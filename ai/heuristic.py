from __future__ import annotations
import random
import time
from typing import Tuple, Dict, Any, Optional, List
from core.state import GameState
from core.rules import legal_moves, apply_move
from ai.evaluator import evaluate_state


def choose_heuristic_move(
    state: GameState,
    player: int,
    seed: Optional[int] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Evaluates at most 25 successor states using one-step lookahead.
    Selects the highest scoring move.
    Uses seeded RNG for deterministic tie-breaking.
    """
    start_time = time.perf_counter()
    moves = legal_moves(state)
    if not moves:
        raise ValueError("Cannot choose move from terminal or empty state.")

    if len(moves) == 1:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        return moves[0], {
            "algorithm": "Heuristic (Easy)",
            "selected_move": moves[0],
            "score": 0.0,
            "evaluations": 1,
            "latency_ms": elapsed,
        }

    rng = random.Random(seed if seed is not None else 42 + state.version)

    best_score = -float("inf")
    best_candidates: List[int] = []

    for move in moves:
        successor = apply_move(state, move)
        score = evaluate_state(successor, player)

        if score > best_score + 1e-7:
            best_score = score
            best_candidates = [move]
        elif abs(score - best_score) <= 1e-7:
            best_candidates.append(move)

    # Seeded deterministic tie breaking
    chosen_move = rng.choice(best_candidates)
    elapsed = (time.perf_counter() - start_time) * 1000.0

    diagnostics = {
        "algorithm": "Heuristic (Easy)",
        "selected_move": chosen_move,
        "score": round(best_score, 2),
        "evaluations": len(moves),
        "tied_moves": len(best_candidates),
        "latency_ms": round(elapsed, 2),
    }

    return chosen_move, diagnostics
