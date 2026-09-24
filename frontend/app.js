/**
 * Chess Arena — app.js
 * ──────────────────────────────────────────────────────────────────
 * Pure vanilla JS chess UI.
 *  • Manages board rendering from FEN
 *  • Click-to-select + legal move highlighting (via backend)
 *  • Communicates with FastAPI backend for all game logic
 *  • Handles pawn promotion dialog
 *  • Animates evaluation bar and win probability
 * ──────────────────────────────────────────────────────────────────
 */

const API = 'http://localhost:8000/api';

// ── Skill → Elo mapping (approximate) ──────────────────────────────
const SKILL_ELO = {
  0: '~800', 1: '~900', 2: '~1000', 3: '~1050', 4: '~1100',
  5: '~1150', 6: '~1200', 7: '~1300', 8: '~1350', 9: '~1400',
  10: '~1500', 11: '~1600', 12: '~1700', 13: '~1800', 14: '~1900',
  15: '~2000', 16: '~2200', 17: '~2400', 18: '~2500', 19: '~2600',
  20: '~2800',
};

// ── FEN Piece mapping ───────────────────────────────────────────────
const PIECE_CLASS = {
  K: 'wK', Q: 'wQ', R: 'wR', B: 'wB', N: 'wN', P: 'wP',
  k: 'bK', q: 'bQ', r: 'bR', b: 'bB', n: 'bN', p: 'bP',
};

// ── State ──────────────────────────────────────────────────────────
let state = {
  gameId:        null,
  fen:           null,
  playerColor:   'white',
  skillLevel:    10,
  flipped:       false,
  selectedSquare: null,
  legalMoves:    [],      // array of {from, to, promo?} in UCI
  lastMoveFrom:  null,
  lastMoveTo:    null,
  inCheck:       false,
  checkSquare:   null,
  gameOver:      false,
  moveSans:      [],      // [ {white: 'e4', black: 'e5'}, … ]
  pendingPromo:  null,    // {from, to} waiting for piece choice
  thinking:      false,
};


// ── DOM References ─────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const DOM = {
  board:           $('chessboard'),
  statusText:      $('game-status-text'),
  statusIcon:      $('status-icon'),
  statusDot:       $('status-dot'),
  statusLabel:     $('status-text'),
  evalFill:        $('eval-bar-fill'),
  evalScore:       $('eval-score'),
  winProbFill:     $('win-prob-fill'),
  winProbWhite:    $('win-prob-white'),
  winProbBlack:    $('win-prob-black'),
  moveTableBody:   $('move-table-body'),
  lastMoveSan:     $('last-move-san'),
  engineElo:       $('engine-elo-display'),
  resultBanner:    $('result-banner'),
  resultIcon:      $('result-icon'),
  resultText:      $('result-text'),
  resultSub:       $('result-sub'),
  difficultySlider: $('difficulty-slider'),
  difficultyLabel:  $('difficulty-label'),
  btnNewGame:       $('btn-new-game'),
  btnResign:        $('btn-resign'),
  btnFlip:          $('btn-flip'),
  btnPlayWhite:     $('btn-play-white'),
  btnPlayBlack:     $('btn-play-black'),
  promoOverlay:     $('promo-overlay'),
  rankLabelsLeft:   $('rank-labels-left'),
  rankLabelsRight:  $('rank-labels-right'),
  fileLabels:       $('file-labels'),
  coachCard:        $('coach-card'),
  coachBadge:       $('coach-quality-badge'),
  coachLoss:        $('coach-loss'),
  coachBestMove:    $('coach-best-move'),
  coachSummary:     $('coach-summary'),
};


// ── Utility: FEN parser ────────────────────────────────────────────

/**
 * Parse a FEN string into an 8×8 array (rank 0 = rank 8, file 0 = file a).
 * Returns piece chars like 'K', 'q', or '' for empty squares.
 */
function parseFen(fen) {
  const board = Array.from({ length: 8 }, () => Array(8).fill(''));
  const rows = fen.split(' ')[0].split('/');
  for (let r = 0; r < 8; r++) {
    let c = 0;
    for (const ch of rows[r]) {
      if (/\d/.test(ch)) {
        c += parseInt(ch, 10);
      } else {
        board[r][c] = ch;
        c++;
      }
    }
  }
  return board;
}

function fenSideToMove(fen) {
  return fen.split(' ')[1] === 'w' ? 'white' : 'black';
}

/** Convert square name (e.g. 'e4') to [rank-index 0-7, file-index 0-7] */
function squareToIndex(sq) {
  const file = sq.charCodeAt(0) - 97; // 'a'=0
  const rank = 8 - parseInt(sq[1], 10); // '8'=0
  return [rank, file];
}

function indexToSquare(r, f) {
  return String.fromCharCode(97 + f) + (8 - r);
}

// ── Utility: network helpers ───────────────────────────────────────

async function apiFetch(path, opts = {}) {
  const url = `${API}${path}`;
  const res  = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}


// ── Board rendering ────────────────────────────────────────────────

function renderBoard(fen) {
  const board2D = parseFen(fen);
  DOM.board.innerHTML = '';

  const legal = state.legalMoves;
  const legalTargets = new Set(legal.filter(m => m.startsWith(state.selectedSquare || '')).map(m => m.slice(2, 4)));

  for (let visualRank = 0; visualRank < 8; visualRank++) {
    for (let visualFile = 0; visualFile < 8; visualFile++) {

      // Account for board flip
      const dataRank = state.flipped ? 7 - visualRank : visualRank;
      const dataFile = state.flipped ? 7 - visualFile : visualFile;
      const squareName = indexToSquare(dataRank, dataFile);

      const sq = document.createElement('div');
      sq.className = 'square ' + ((dataRank + dataFile) % 2 === 0 ? 'light' : 'dark');
      sq.dataset.square = squareName;

      // Highlights
      if (squareName === state.lastMoveFrom || squareName === state.lastMoveTo) {
        sq.classList.add(squareName === state.lastMoveFrom ? 'last-move-from' : 'last-move-to');
      }
      if (squareName === state.selectedSquare) {
        sq.classList.add('selected');
      }
      if (state.checkSquare && squareName === state.checkSquare) {
        sq.classList.add('in-check');
      }

      // Legal move targets
      if (state.selectedSquare && legalTargets.has(squareName)) {
        const piece = board2D[dataRank][dataFile];
        sq.classList.add(piece ? 'legal-capture' : 'legal-target');
      }

      // Piece
      const pieceChar = board2D[dataRank][dataFile];
      if (pieceChar) {
        const pieceEl = document.createElement('div');
        pieceEl.className = 'piece ' + PIECE_CLASS[pieceChar];
        sq.appendChild(pieceEl);
      }

      sq.addEventListener('click', onSquareClick);
      DOM.board.appendChild(sq);
    }
  }

  updateLabels();
}

function updateLabels() {
  // Rank labels
  const ranks = state.flipped ? ['1','2','3','4','5','6','7','8'] : ['8','7','6','5','4','3','2','1'];
  DOM.rankLabelsLeft.querySelectorAll('span').forEach((el, i) => el.textContent = ranks[i]);
  DOM.rankLabelsRight.querySelectorAll('span').forEach((el, i) => el.textContent = ranks[i]);

  // File labels
  const files = state.flipped ? ['h','g','f','e','d','c','b','a'] : ['a','b','c','d','e','f','g','h'];
  DOM.fileLabels.querySelectorAll('span').forEach((el, i) => el.textContent = files[i]);
}

function animatePieceOnSquare(squareName) {
  const sq = DOM.board.querySelector(`[data-square="${squareName}"]`);
  if (!sq) return;
  const piece = sq.querySelector('.piece');
  if (!piece) return;
  piece.classList.remove('animate-move');
  void piece.offsetWidth; // reflow
  piece.classList.add('animate-move');
}


// ── Square click handler ───────────────────────────────────────────

async function onSquareClick(e) {
  if (state.gameOver || state.thinking || !state.gameId) return;

  const sq = e.currentTarget;
  const squareName = sq.dataset.square;
  const board2D = parseFen(state.fen);
  const [r, f] = squareToIndex(squareName);
  const piece = board2D[r][f];
  const sideToMove = fenSideToMove(state.fen);

  // Not the player's turn
  if (sideToMove !== state.playerColor) return;

  // Case 1: no selection — try to select this square
  if (!state.selectedSquare) {
    if (!piece) return;
    const isPlayerPiece = (state.playerColor === 'white')
      ? piece === piece.toUpperCase()
      : piece === piece.toLowerCase();
    if (!isPlayerPiece) return;

    // Fetch legal moves from backend
    const lm = await getLegalMoves(state.fen);
    const movesFrom = lm.filter(m => m.startsWith(squareName));
    if (movesFrom.length === 0) return;

    state.selectedSquare = squareName;
    state.legalMoves = movesFrom;
    renderBoard(state.fen);
    return;
  }

  // Case 2: same square clicked — deselect
  if (state.selectedSquare === squareName) {
    clearSelection();
    renderBoard(state.fen);
    return;
  }

  // Case 3: another own piece clicked — switch selection
  if (piece) {
    const isPlayerPiece = (state.playerColor === 'white')
      ? piece === piece.toUpperCase()
      : piece === piece.toLowerCase();
    if (isPlayerPiece) {
      const lm = await getLegalMoves(state.fen);
      const movesFrom = lm.filter(m => m.startsWith(squareName));
      state.selectedSquare = squareName;
      state.legalMoves = movesFrom;
      renderBoard(state.fen);
      return;
    }
  }

  // Case 4: attempt a move
  const candidateMoves = state.legalMoves.filter(m =>
    m.startsWith(state.selectedSquare) && m.slice(2, 4) === squareName
  );
  if (candidateMoves.length === 0) {
    clearSelection();
    renderBoard(state.fen);
    return;
  }

  // Check if promotion is needed
  const needsPromo = candidateMoves.some(m => m.length === 5);
  if (needsPromo) {
    state.pendingPromo = { from: state.selectedSquare, to: squareName };
    DOM.promoOverlay.classList.remove('hidden');
    // Tint promotion buttons for correct color
    const isWhite = state.playerColor === 'white';
    document.querySelectorAll('.promo-btn').forEach(btn => {
      const p = btn.dataset.piece;
      btn.querySelector('span, :first-child').textContent =
        ({ q: isWhite ? '♛' : '♛', r: isWhite ? '♜' : '♜', b: isWhite ? '♝' : '♝', n: isWhite ? '♞' : '♞' }[p] || '');
    });
    return;
  }

  const moveUci = candidateMoves[0];
  clearSelection();
  await submitMove(moveUci);
}


// ── Promotion dialog ───────────────────────────────────────────────

document.querySelectorAll('.promo-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    if (!state.pendingPromo) return;
    DOM.promoOverlay.classList.add('hidden');
    const { from, to } = state.pendingPromo;
    const piece = btn.dataset.piece;
    state.pendingPromo = null;
    clearSelection();
    await submitMove(`${from}${to}${piece}`);
  });
});


// ── Submit move to backend ─────────────────────────────────────────

async function submitMove(moveUci) {
  if (!state.gameId || state.thinking) return;

  state.thinking = true;
  setStatus('thinking', `
    <span class="thinking-indicator">Engine thinking
      <span class="thinking-dots"><span></span><span></span><span></span></span>
    </span>
  `);

  try {
    const result = await apiFetch(`/game/${state.gameId}/move`, {
      method: 'POST',
      body: JSON.stringify({ move_uci: moveUci, time_limit: 0.1 }),
    });

    // Update state after player move
    state.lastMoveFrom = moveUci.slice(0, 2);
    state.lastMoveTo   = moveUci.slice(2, 4);

    if (result.game_over && !result.engine_move_uci) {
      // Player's move ended the game (checkmate/stalemate by player)
      state.fen = result.fen_after_player;
      state.gameOver = true;
      updateCoachCard(result);
      handleGameOver(result);
    } else if (result.engine_move_uci) {
      // Engine responded
      state.fen = result.fen_after_engine;
      state.lastMoveFrom = result.engine_move_uci.slice(0, 2);
      state.lastMoveTo   = result.engine_move_uci.slice(2, 4);

      // Detect check on king
      state.checkSquare = null;
      state.inCheck     = result.is_check;
      if (result.is_check) {
        state.checkSquare = findKing(state.fen, state.playerColor);
      }

      addMovePair(result.player_move_san, result.engine_move_san);
      DOM.lastMoveSan.textContent = result.engine_move_san || '—';

      updateEvalBar(result.eval_centipawns, result.eval_mate_in, result.win_pct);
      updateCoachCard(result);

      if (result.game_over) {
        state.gameOver = true;
        handleGameOver(result);
      } else {
        setStatus('default', `Your turn (${state.playerColor === 'white' ? 'White' : 'Black'})`);
      }
    } else {
      // Edge case: no engine move, game not over yet (shouldn't happen normally)
      state.fen = result.fen_after_player;
    }

    renderBoard(state.fen);
    if (result.engine_move_uci) animatePieceOnSquare(result.engine_move_uci.slice(2, 4));

  } catch (err) {
    setStatus('error', `Error: ${err.message}`);
  } finally {
    state.thinking = false;
  }
}


// ── Coach card ────────────────────────────────────────────────────

const COACH_COLORS = {
  best:        '#10b981',  // emerald
  good:        '#06b6d4',  // cyan
  inaccuracy:  '#f59e0b',  // gold
  mistake:     '#f97316',  // orange
  blunder:     '#f43f5e',  // rose
};

const COACH_EMOJIS = {
  best: '✅', good: '👍', inaccuracy: '⚠️', mistake: '❌', blunder: '💀',
};

function updateCoachCard(result) {
  const label = result.coach_quality_label;
  if (!label) {
    DOM.coachCard.classList.add('hidden');
    return;
  }

  DOM.coachCard.classList.remove('hidden');

  const color = COACH_COLORS[label] || '#94a3b8';
  const emoji = COACH_EMOJIS[label] || '';

  DOM.coachBadge.textContent = `${emoji} ${label.charAt(0).toUpperCase() + label.slice(1)}`;
  DOM.coachBadge.style.setProperty('--coach-color', color);
  DOM.coachBadge.style.background = color + '22';
  DOM.coachBadge.style.color = color;
  DOM.coachBadge.style.borderColor = color + '66';

  const before = result.coach_win_pct_before?.toFixed(1) ?? '?';
  const after  = result.coach_win_pct_after?.toFixed(1)  ?? '?';
  const loss   = result.coach_win_pct_loss?.toFixed(1)   ?? '0.0';
  const sign   = parseFloat(loss) > 0 ? '-' : '';
  DOM.coachLoss.textContent = `${before}% → ${after}% (${sign}${loss}pp)`;
  DOM.coachLoss.style.color = parseFloat(loss) >= 10 ? color : 'var(--clr-text)';

  DOM.coachBestMove.textContent = result.coach_best_move_san || '—';
  DOM.coachSummary.textContent  = result.coach_summary || '—';
}


// ── Legal moves ────────────────────────────────────────────────────

async function getLegalMoves(fen) {
  try {
    const data = await apiFetch(`/engine/legalmoves?fen=${encodeURIComponent(fen)}`);
    return data.legal_moves || [];
  } catch {
    return [];
  }
}


// ── New Game ───────────────────────────────────────────────────────

async function startNewGame() {
  DOM.btnResign.disabled = false;
  DOM.resultBanner.classList.add('hidden');
  DOM.coachCard.classList.add('hidden');
  clearMoveTable();
  clearSelection();

  state.gameOver       = false;
  state.thinking       = false;
  state.lastMoveFrom   = null;
  state.lastMoveTo     = null;
  state.checkSquare    = null;
  state.inCheck        = false;
  state.moveSans       = [];
  state.pendingPromo   = null;
  DOM.lastMoveSan.textContent = '—';
  updateEvalBar(0, null, 50);

  setStatus('default', 'Starting game…');

  try {
    const res = await apiFetch('/game/new', {
      method: 'POST',
      body: JSON.stringify({
        player_id:    'guest',
        skill_level:  state.skillLevel,
        player_color: state.playerColor,
      }),
    });

    state.gameId = res.game_id;
    state.fen    = res.fen_after_engine || res.fen;

    if (state.skillLevel === 'auto') {
      DOM.difficultyLabel.textContent = `Auto assigned: Skill ${res.skill_level} (${SKILL_ELO[res.skill_level]} Elo)`;
      DOM.engineElo.textContent = `${SKILL_ELO[res.skill_level]} Elo`;
    }

    if (res.engine_move && res.engine_move_san) {
      state.lastMoveFrom = res.engine_move.slice(0, 2);
      state.lastMoveTo   = res.engine_move.slice(2, 4);
      addMovePair(null, res.engine_move_san);  // engine moved first (player is black)
      DOM.lastMoveSan.textContent = res.engine_move_san;
    }

    renderBoard(state.fen);
    setStatus('default', `Your turn (${state.playerColor === 'white' ? 'White ♙' : 'Black ♟'})`);
  } catch (err) {
    setStatus('error', `Failed to start game: ${err.message}`);
  }
}


// ── Game Over ──────────────────────────────────────────────────────

function handleGameOver(result) {
  DOM.btnResign.disabled = true;
  DOM.resultBanner.classList.remove('hidden');

  const r = result.game_result;
  let icon  = '🤝';
  let text  = 'Game Over';
  let sub   = result.termination || '';

  if (r === '1-0') {
    icon = state.playerColor === 'white' ? '🏆' : '💀';
    text = state.playerColor === 'white' ? 'You Win!' : 'Engine Wins';
  } else if (r === '0-1') {
    icon = state.playerColor === 'black' ? '🏆' : '💀';
    text = state.playerColor === 'black' ? 'You Win!' : 'Engine Wins';
  } else {
    icon = '🤝';
    text = 'Draw';
  }

  DOM.resultIcon.textContent = icon;
  DOM.resultText.textContent = text;
  DOM.resultSub.textContent  = sub.replace(/_/g, ' ');
  setStatus('default', `${text} — ${sub.replace(/_/g, ' ')}`);
}


// ── Resign ─────────────────────────────────────────────────────────

async function resignGame() {
  if (!state.gameId || state.gameOver) return;
  try {
    await apiFetch(`/game/${state.gameId}/resign`, {
      method: 'POST',
      body: JSON.stringify({ player_id: 'guest' }),
    });
    state.gameOver = true;
    DOM.btnResign.disabled = true;
    DOM.resultBanner.classList.remove('hidden');
    DOM.resultIcon.textContent = '🏳️';
    DOM.resultText.textContent = 'You Resigned';
    DOM.resultSub.textContent  = 'Better luck next time!';
    setStatus('default', 'You resigned.');
  } catch (err) {
    setStatus('error', `Failed to resign: ${err.message}`);
  }
}


// ── UI Helpers ─────────────────────────────────────────────────────

function clearSelection() {
  state.selectedSquare = null;
  state.legalMoves = [];
}

function setStatus(type, html) {
  DOM.statusText.innerHTML = html;
  DOM.statusIcon.textContent = { default: '♟', error: '⚠', thinking: '🤔' }[type] || '♟';
}

function updateEvalBar(cp, mateIn, winPct) {
  if (winPct == null) return;
  const pct = Math.max(5, Math.min(95, winPct));
  DOM.evalFill.style.width = pct + '%';

  let label;
  if (mateIn != null) {
    label = `M${Math.abs(mateIn)}`;
    DOM.evalScore.style.color = mateIn > 0 ? '#10b981' : '#f43f5e';
  } else if (cp != null) {
    const abs = Math.abs(cp / 100).toFixed(1);
    label = (cp >= 0 ? '+' : '-') + abs;
    DOM.evalScore.style.color = 'var(--clr-text)';
  } else {
    label = '0.0';
  }
  DOM.evalScore.textContent = label;

  // Win prob bar
  DOM.winProbFill.style.width = pct + '%';
  DOM.winProbWhite.textContent = pct.toFixed(0) + '%';
  DOM.winProbBlack.textContent = (100 - pct).toFixed(0) + '%';
}

function addMovePair(whiteSan, blackSan) {
  const tbody = DOM.moveTableBody;

  // Remove "no moves" placeholder
  const empty = tbody.querySelector('.empty-row');
  if (empty) tbody.removeChild(empty);

  const prev = tbody.querySelectorAll('tr.latest');
  prev.forEach(r => r.classList.remove('latest'));

  if (whiteSan) {
    // New pair row
    const moveNum = state.moveSans.length + 1;
    state.moveSans.push({ white: whiteSan, black: '' });
    const tr = document.createElement('tr');
    tr.classList.add('latest');
    tr.innerHTML = `
      <td class="move-num">${moveNum}</td>
      <td class="move-san">${whiteSan}</td>
      <td class="move-san"></td>
    `;
    tbody.appendChild(tr);
  }

  if (blackSan && state.moveSans.length > 0) {
    const last = state.moveSans[state.moveSans.length - 1];
    last.black = blackSan;
    const rows = tbody.querySelectorAll('tr:not(.empty-row)');
    const lastRow = rows[rows.length - 1];
    if (lastRow) {
      const tds = lastRow.querySelectorAll('td');
      if (tds[2]) tds[2].textContent = blackSan;
      lastRow.classList.add('latest');
    }
  }

  // Scroll to bottom
  const wrapper = DOM.moveTableBody.closest('.move-list-wrapper');
  if (wrapper) wrapper.scrollTop = wrapper.scrollHeight;
}

function clearMoveTable() {
  state.moveSans = [];
  DOM.moveTableBody.innerHTML = '<tr class="empty-row"><td colspan="3">No moves yet</td></tr>';
}

function findKing(fen, color) {
  const board2D = parseFen(fen);
  const kingChar = color === 'white' ? 'K' : 'k';
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      if (board2D[r][f] === kingChar) return indexToSquare(r, f);
    }
  }
  return null;
}


// ── Health check & connection status ──────────────────────────────

async function checkHealth() {
  try {
    const res = await fetch('http://localhost:8000/health');
    if (res.ok) {
      DOM.statusDot.className  = 'status-dot online';
      DOM.statusLabel.textContent = 'Engine Ready';
      return true;
    }
  } catch {}
  DOM.statusDot.className  = 'status-dot offline';
  DOM.statusLabel.textContent = 'Backend Offline';
  return false;
}


// ── Difficulty slider ──────────────────────────────────────────────

const autoDiffCheckbox = $('auto-difficulty');
autoDiffCheckbox.addEventListener('change', () => {
  if (autoDiffCheckbox.checked) {
    DOM.difficultySlider.disabled = true;
    state.skillLevel = 'auto';
    DOM.difficultyLabel.textContent = `Auto: Optimal match`;
    DOM.difficultyLabel.style.opacity = 0.5;
  } else {
    DOM.difficultySlider.disabled = false;
    const v = parseInt(DOM.difficultySlider.value, 10);
    state.skillLevel = v;
    DOM.difficultyLabel.textContent = `Skill ${v} (${SKILL_ELO[v]} Elo)`;
    DOM.difficultyLabel.style.opacity = 1.0;
  }
});

DOM.difficultySlider.addEventListener('input', () => {
  if (autoDiffCheckbox.checked) return;
  const v = parseInt(DOM.difficultySlider.value, 10);
  state.skillLevel = v;
  DOM.difficultyLabel.textContent = `Skill ${v} (${SKILL_ELO[v]} Elo)`;
  DOM.engineElo.textContent       = `${SKILL_ELO[v]} Elo`;
});


// ── Color picker ───────────────────────────────────────────────────

DOM.btnPlayWhite.addEventListener('click', () => {
  state.playerColor = 'white';
  DOM.btnPlayWhite.classList.add('active');
  DOM.btnPlayBlack.classList.remove('active');
});

DOM.btnPlayBlack.addEventListener('click', () => {
  state.playerColor = 'black';
  DOM.btnPlayBlack.classList.add('active');
  DOM.btnPlayWhite.classList.remove('active');
});


// ── Flip board ────────────────────────────────────────────────────

DOM.btnFlip.addEventListener('click', () => {
  state.flipped = !state.flipped;
  if (state.fen) renderBoard(state.fen);
});


// ── New Game ───────────────────────────────────────────────────────

DOM.btnNewGame.addEventListener('click', startNewGame);
$('btn-result-new-game').addEventListener('click', startNewGame);


// ── Resign ────────────────────────────────────────────────────────

DOM.btnResign.addEventListener('click', resignGame);


// ── Difficulty init ────────────────────────────────────────────────

state.skillLevel = 'auto';
DOM.difficultySlider.value = 10;
DOM.difficultyLabel.textContent = `Auto: Optimal match`;


// ── Render start position immediately ─────────────────────────────

state.fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
renderBoard(state.fen);


// ── Boot ───────────────────────────────────────────────────────────

(async function boot() {
  const online = await checkHealth();
  if (!online) {
    setStatus('error', 'Backend offline — start the server first.');
  } else {
    setStatus('default', 'Click "New Game" to play!');
  }
  // Re-check every 10 seconds
  setInterval(checkHealth, 10000);
})();
