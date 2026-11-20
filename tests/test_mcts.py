"""
Unit tests for Hard AI (Monte Carlo Tree Search with UCT).
"""

import pytest
from core.state import GameMode, AgentType
from core.rules import create_game, legal_moves
from ai.mcts import choose_mcts_move, MCTSNode
from ai import choose_move


def test_mcts_returns_legal_move():
    """MCTS must return a legal move after performing simulations."""
    state = create_game(GameMode.HUMAN_VS_AI, (AgentType.HUMAN, AgentType.HARD), seed=4)
    valid = legal_moves(state)
    move, diag = choose_mcts_move(state, player=1, rollouts=50, time_limit_sec=1.0, seed=42)
    assert move in valid
    assert not state.is_called(move)
    assert diag["simulations"] > 0
    assert diag["visits"] > 0


def test_ai_fallback_on_error():
    """If an AI encounters an error, choose_move falls back gracefully to heuristic."""
    state = create_game(seed=5)
    # Pass an invalid difficulty to test robust fallback
    move, diag = choose_move(state, 1, {"difficulty": "INVALID_DIFF"})
    assert move in legal_moves(state)
