"""
rag_service.py — Local Retrieval-Augmented Generation (RAG) for Chess Coaching.

Provides fast, zero-budget, local retrieval of:
  1. Opening Theory (ECO codes, strategic plans, common mistakes)
  2. Tactical Motifs (pins, forks, skewers, deflections, back-rank)
  3. Endgame Principles (king activity, opposition, Lucena, Philidor, passed pawns)

Operates with local CPU embeddings or fast cosine/keyword search. Zero external API cost.
"""

from __future__ import annotations

import json
import logging
import math
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

import chess

logger = logging.getLogger("rag_service")

DATA_DIR = Path(__file__).parent / "data" / "rag"
OPENINGS_FILE = DATA_DIR / "openings.json"
TACTICS_FILE = DATA_DIR / "tactics.json"
ENDGAMES_FILE = DATA_DIR / "endgames.json"


class LocalRAGKnowledgeBase:
    """Manages the local chess knowledge base and semantic/keyword retrieval."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.openings: List[Dict[str, Any]] = []
        self.tactics: List[Dict[str, Any]] = []
        self.endgames: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self) -> None:
        try:
            if OPENINGS_FILE.exists():
                self.openings = json.loads(OPENINGS_FILE.read_text(encoding="utf-8"))
            if TACTICS_FILE.exists():
                self.tactics = json.loads(TACTICS_FILE.read_text(encoding="utf-8"))
            if ENDGAMES_FILE.exists():
                self.endgames = json.loads(ENDGAMES_FILE.read_text(encoding="utf-8"))
            logger.info(
                "Loaded RAG knowledge: %d openings, %d tactics, %d endgame principles",
                len(self.openings),
                len(self.tactics),
                len(self.endgames),
            )
        except Exception:
            logger.exception("Failed to load RAG knowledge base files.")

    def _tokenize(self, text: str) -> set[str]:
        """Simple alphanumeric tokenizer for keyword similarity."""
        return set(re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower()))

    def _keyword_similarity(self, query: str, document: str) -> float:
        """Compute Jaccard token similarity with length normalization."""
        q_tokens = self._tokenize(query)
        d_tokens = self._tokenize(document)
        if not q_tokens or not d_tokens:
            return 0.0
        intersection = len(q_tokens & d_tokens)
        union = len(q_tokens | d_tokens)
        return intersection / union if union > 0 else 0.0

    def match_opening(self, move_san: str, ply: int = 1) -> Optional[Dict[str, Any]]:
        """Look up relevant opening by move keywords or ECO code."""
        if ply > 16:
            return None  # Out of opening book phase
        for op in self.openings:
            if move_san in op.get("moves", "").split():
                return op
        return None

    def match_tactic(self, query: str) -> Optional[Dict[str, Any]]:
        """Find the most relevant tactical motif matching query tokens."""
        best_match = None
        best_score = 0.0
        for item in self.tactics:
            doc = f"{item['name']} {item['definition']} {item['tactical_cue']}"
            score = self._keyword_similarity(query, doc)
            if score > best_score:
                best_score = score
                best_match = item
        return best_match if best_score > 0.08 else None

    def match_endgame(self, query: str) -> Optional[Dict[str, Any]]:
        """Find the most relevant endgame principle."""
        best_match = None
        best_score = 0.0
        for item in self.endgames:
            doc = f"{item['name']} {item['rule_summary']} {item['practical_tip']}"
            score = self._keyword_similarity(query, doc)
            if score > best_score:
                best_score = score
                best_match = item
        return best_match if best_score > 0.08 else None

    def retrieve_context(self, analysis: dict) -> str:
        """
        Extract relevant chess knowledge context based on the position facts
        and classification. Returns a concise 1-2 sentence context snippet.
        """
        fen = analysis.get("fen", "")
        move_san = analysis.get("move_san", "")
        quality_label = analysis.get("quality_label", "")
        is_capture = analysis.get("is_capture", False)
        gives_check = analysis.get("gives_check", False)
        allows_mate = analysis.get("allows_forced_mate", False)

        context_parts = []

        try:
            board = chess.Board(fen) if fen else None
        except Exception:
            board = None

        piece_count = len(board.piece_map()) if board else 32
        has_no_queens = bool(board and not board.pieces(chess.QUEEN, chess.WHITE) and not board.pieces(chess.QUEEN, chess.BLACK))
        is_endgame = piece_count <= 14 or has_no_queens
        fullmove_number = board.fullmove_number if board else 1

        # 1. Opening context (early game)
        if fullmove_number <= 8 and not is_endgame:
            opening = self.match_opening(move_san, fullmove_number * 2)
            if opening:
                context_parts.append(
                    f"Opening Note ({opening['name']}): {opening['thematic_ideas']} "
                    f"Typical plan: {opening['key_plans_white'] if board and board.turn == chess.WHITE else opening['key_plans_black']}"
                )

        # 2. Endgame context
        if is_endgame:
            eg_query = f"{move_san} king passed pawn rook opposition endgame"
            endgame = self.match_endgame(eg_query)
            if endgame:
                context_parts.append(
                    f"Endgame Principle ({endgame['name']}): {endgame['rule_summary']} "
                    f"Tip: {endgame['practical_tip']}"
                )

        # 3. Tactical context (for inaccuracies, mistakes, blunders, captures, checks)
        if quality_label in ("inaccuracy", "mistake", "blunder") or gives_check or allows_mate:
            tactical_terms = []
            if allows_mate:
                tactical_terms.append("back-rank checkmate mating net")
            if is_capture:
                tactical_terms.append("deflection capture sacrifice")
            if gives_check:
                tactical_terms.append("discovered attack check pin fork")
            if "N" in move_san:
                tactical_terms.append("knight fork outpost")
            if quality_label == "blunder":
                tactical_terms.append("overloaded defender pin skewer trapped piece")

            query = " ".join(tactical_terms) or "pin fork skewer discovered attack deflection"
            tactic = self.match_tactic(query)
            if tactic:
                context_parts.append(
                    f"Tactical Motif ({tactic['name']}): {tactic['tactical_cue']} "
                    f"Advice: {tactic['remedy_advice']}"
                )

        if not context_parts:
            # Fallback general strategic advice
            return "Principle: Prioritize piece activity, king safety, and control over central squares."

        return " ".join(context_parts)


# Global singleton instance
_rag_kb: Optional[LocalRAGKnowledgeBase] = None


def get_rag_knowledge_base() -> LocalRAGKnowledgeBase:
    global _rag_kb
    if _rag_kb is None:
        _rag_kb = LocalRAGKnowledgeBase()
    return _rag_kb
