"""
Integration tests for all 3 game modes, controller flow, restart, and statistics.
"""

import os
import pytest
from core.state import GameMode, AgentType, GameStatus
from core.controller import GameController
from data.stats_manager import StatsManager


def test_mode_1_human_vs_ai_flow():
    """Mode 1: Human vs AI initializes, human moves, AI responds."""
    ctrl = GameController(
        mode=GameMode.HUMAN_VS_AI,
        agents=(AgentType.HUMAN, AgentType.EASY),
        seed=10,
    )
    assert ctrl.state.mode == GameMode.HUMAN_VS_AI
    assert ctrl.state.current_player == 0

    # Human calls a legal number
    first_legal = ctrl.state.board_a[0]
    accepted = ctrl.trigger_human_move(first_legal)
    assert accepted is True
    assert ctrl.state.is_called(first_legal)
    assert ctrl.state.current_player == 1  # Now AI's turn


def test_mode_2_human_vs_human_flow():
    """Mode 2: Local Human vs Human turn alternation."""
    ctrl = GameController(
        mode=GameMode.HUMAN_VS_HUMAN,
        agents=(AgentType.HUMAN, AgentType.HUMAN),
        seed=20,
    )
    assert ctrl.state.mode == GameMode.HUMAN_VS_HUMAN
    assert ctrl.state.current_player == 0

    p1_move = ctrl.state.board_a[0]
    assert ctrl.trigger_human_move(p1_move) is True
    assert ctrl.state.current_player == 1

    p2_move = ctrl.state.board_b[0]
    if p2_move == p1_move:
        p2_move = ctrl.state.board_b[1]

    assert ctrl.trigger_human_move(p2_move) is True
    assert ctrl.state.current_player == 0


def test_controller_restart():
    """Restart resets board, history, and version."""
    ctrl = GameController(seed=30)
    m = ctrl.state.board_a[0]
    ctrl.trigger_human_move(m)
    assert len(ctrl.state.move_history) == 1

    ctrl.restart(seed=31)
    assert len(ctrl.state.move_history) == 0
    assert ctrl.state.called_mask == 0
    assert ctrl.state.version == 0


def test_statistics_persistence(tmp_path):
    """Verify statistics recording and atomic persistence."""
    stats_file = str(tmp_path / "test_stats.json")
    mgr = StatsManager(filepath=stats_file)
    assert mgr.stats["total_matches"] == 0

    # Create a finished mock state
    ctrl = GameController(mode=GameMode.HUMAN_VS_AI, agents=(AgentType.HUMAN, AgentType.EASY))
    # Artificially set state to finished
    finished_state = ctrl.state.__class__(
        board_a=ctrl.state.board_a,
        board_b=ctrl.state.board_b,
        called_mask=ctrl.state.called_mask,
        current_player=0,
        mode=GameMode.HUMAN_VS_AI,
        agents=(AgentType.HUMAN, AgentType.EASY),
        status=GameStatus.FINISHED,
        winner=0,
        move_history=(1, 2, 3),
    )
    mgr.record_match(finished_state)
    assert mgr.stats["total_matches"] == 1
    assert mgr.stats["human_wins"] == 1

    # Reload from disk
    mgr2 = StatsManager(filepath=stats_file)
    assert mgr2.stats["total_matches"] == 1
    assert mgr2.stats["human_wins"] == 1

    mgr2.clear()
    assert mgr2.stats["total_matches"] == 0
