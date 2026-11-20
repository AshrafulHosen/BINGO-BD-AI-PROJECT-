"""
Unit tests for Easy AI (One-Step Heuristic Search).
"""

import pytest
from core.state import GameMode, AgentType
from core.rules import create_game, apply_move, legal_moves
from ai.heuristic import choose_heuristic_move


def test_heuristic_returns_legal_move():
    """Heuristic AI must always return a legal, uncalled number."""
    state = create_game(GameMode.HUMAN_VS_AI, (AgentType.HUMAN, AgentType.EASY), seed=1)
    # Simulate a few turns
    for _ in range(5):
        valid = legal_moves(state)
        move, diag = choose_heuristic_move(state, state.current_player, seed=42)
        assert move in valid
        assert not state.is_called(move)
        state = apply_move(state, move)


def test_heuristic_deterministic_tie_breaking():
    """Identical seeds must produce identical tie-breaking moves."""
    state = create_game(seed=10)
    m1, _ = choose_heuristic_move(state, 1, seed=777)
    m2, _ = choose_heuristic_move(state, 1, seed=777)
    assert m1 == m2
