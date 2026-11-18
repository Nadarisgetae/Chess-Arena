"""
test_rag_service.py — Unit tests for the local RAG knowledge base.
"""

import pytest
from backend.rag_service import get_rag_knowledge_base, LocalRAGKnowledgeBase


def test_rag_knowledge_base_loads():
    kb = get_rag_knowledge_base()
    assert len(kb.openings) >= 5, "Should have loaded openings"
    assert len(kb.tactics) >= 5, "Should have loaded tactics"
    assert len(kb.endgames) >= 5, "Should have loaded endgames"


def test_match_opening_sicilian():
    kb = get_rag_knowledge_base()
    opening = kb.match_opening("c5", ply=2)
    assert opening is not None
    assert "Sicilian" in opening["name"]


def test_match_tactic_fork():
    kb = get_rag_knowledge_base()
    tactic = kb.match_tactic("knight fork king queen simultaneous attack")
    assert tactic is not None
    assert "Fork" in tactic["name"]


def test_retrieve_context_blunder():
    kb = get_rag_knowledge_base()
    analysis = {
        "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
        "move_san": "Nf6",
        "quality_label": "blunder",
        "is_capture": False,
        "gives_check": False,
        "allows_forced_mate": True,
    }
    context = kb.retrieve_context(analysis)
    assert isinstance(context, str)
    assert len(context) > 20
    assert ("Tactical" in context or "Opening" in context)
