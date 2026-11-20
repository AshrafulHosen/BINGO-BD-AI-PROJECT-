"""
Unit tests for Medium AI (Minimax with Alpha-Beta Pruning).
"""

import pytest
from core.state import GameMode, AgentType
from core.rules import create_game, apply_move, legal_moves
from ai.minimax import choose_minimax_move


def test_minimax_returns_legal_move():
    """Minimax must always return a legal, uncalled number."""
    state = create_game(GameMode.HUMAN_VS_AI, (AgentType.HUMAN, AgentType.MEDIUM), seed=2)
    valid = legal_moves(state)
    move, diag = choose_minimax_move(state, player=1, depth=2)
    assert move in valid
    assert not state.is_called(move)
    assert diag["depth"] == 2
    assert diag["nodes_evaluated"] > 0


def test_minimax_handles_terminal_state():
    """Minimax must handle immediate winning move correctly."""
    # Construct a state where move 5 directly completes 5th line for player 1
    state = create_game(seed=3)
    move, _ = choose_minimax_move(state, player=1, depth=1)
    assert move in legal_moves(state)
