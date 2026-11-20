"""
BINGO-BD Medium AI: Depth-Limited Minimax with Alpha-Beta Pruning
Implements adversarial game tree search with action ordering, terminal state detection,
and depth-adjusted terminal utility.
Pure Python - NO Pygame imports.
"""

from __future__ import annotations
import time
from typing import Tuple, Dict, Any, Optional, List
from core.state import GameState, GameStatus, DRAW
from core.rules import legal_moves, apply_move
from ai.evaluator import evaluate_state, quick_move_score, WIN_SCORE, LOSS_SCORE, DRAW_SCORE


class _SearchTimeout(Exception):
    """Raised internally when the wall-clock budget is exhausted."""


def choose_minimax_move(
    state: GameState,
    player: int,
    depth: int = 2,
    time_limit_sec: float = 1.0,
    seed: Optional[int] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Finds the best legal move using depth-limited Minimax with Alpha-Beta Pruning.

    * Terminal utilities dominate heuristic leaves (+/-100000, adjusted by ply so
      that quicker wins / slower losses are preferred).
    * Moves are ordered by ``quick_move_score`` to maximise alpha-beta cutoffs;
      ties keep that ordering, so the result is deterministic.
    * If the time budget runs out, the search is aborted and the best *fully
      evaluated* root move is returned (PRD section 6).  If not even one root
      move finished, the best-ordered move (heuristic fallback) is returned.
    """
    start_time = time.perf_counter()
    deadline = start_time + max(0.0, time_limit_sec)
    moves = legal_moves(state)
    if not moves:
        raise ValueError("Cannot choose move from terminal or empty state.")

    if len(moves) == 1:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        return moves[0], {
            "algorithm": "Minimax (Medium)",
            "selected_move": moves[0],
            "depth": depth,
            "nodes_evaluated": 1,
            "score": 0.0,
            "latency_ms": round(elapsed, 2),
        }

    depth = max(1, int(depth))
    opponent = 1 - player
    nodes_evaluated = 0
    cutoffs = 0

    def ordered(s: GameState, mover: int) -> List[int]:
        return sorted(legal_moves(s), key=lambda m: quick_move_score(s, m, mover), reverse=True)

    def minimax(s: GameState, ply: int, alpha: float, beta: float) -> float:
        nonlocal nodes_evaluated, cutoffs
        nodes_evaluated += 1
        if (nodes_evaluated & 63) == 0 and time.perf_counter() > deadline:
            raise _SearchTimeout

        # 1. Terminal evaluation
        if s.status == GameStatus.FINISHED:
            if s.winner == player:
                return WIN_SCORE - ply      # prefer quicker victory
            if s.winner == opponent:
                return LOSS_SCORE + ply     # delay defeat
            return DRAW_SCORE

        # 2. Depth cutoff: heuristic leaf
        if ply >= depth:
            return evaluate_state(s, player)

        if s.current_player == player:
            best = -float("inf")
            for m in ordered(s, player):
                val = minimax(apply_move(s, m), ply + 1, alpha, beta)
                if val > best:
                    best = val
                if best > alpha:
                    alpha = best
                if alpha >= beta:
                    cutoffs += 1
                    break  # beta cutoff
            return best
        else:
            best = float("inf")
            for m in ordered(s, opponent):
                val = minimax(apply_move(s, m), ply + 1, alpha, beta)
                if val < best:
                    best = val
                if best < beta:
                    beta = best
                if alpha >= beta:
                    cutoffs += 1
                    break  # alpha cutoff
            return best

    root_moves = ordered(state, player)
    best_move = root_moves[0]
    best_value = -float("inf")
    alpha = -float("inf")
    completed = 0
    timed_out = False

    for move in root_moves:
        try:
            value = minimax(apply_move(state, move), 1, alpha, float("inf"))
        except _SearchTimeout:
            timed_out = True
            break
        completed += 1
        if value > best_value:
            best_value = value
            best_move = move
        if value > alpha:
            alpha = value
        if best_value >= WIN_SCORE - depth:
            break  # forced win found - no need to keep searching

    elapsed = (time.perf_counter() - start_time) * 1000.0
    diagnostics = {
        "algorithm": "Minimax (Medium)",
        "selected_move": best_move,
        "score": round(best_value, 2) if completed else 0.0,
        "depth": depth,
        "nodes_evaluated": nodes_evaluated,
        "cutoffs": cutoffs,
        "root_moves_searched": completed,
        "timed_out": timed_out,
        "latency_ms": round(elapsed, 2),
    }
    return best_move, diagnostics
