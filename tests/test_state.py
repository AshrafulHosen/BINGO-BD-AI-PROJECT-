"""
Unit tests for BINGO-BD GameState immutability, versioning, and properties.
"""

import pytest
from core.state import GameState, GameMode, AgentType, GameStatus
from core.rules import create_game, apply_move


def test_state_immutability():
    """Applying a move must return a NEW state without mutating the original state."""
    state = create_game(seed=42)
    original_mask = state.called_mask
    original_history = state.move_history
    original_version = state.version

    new_state = apply_move(state, 5)

    assert state.called_mask == original_mask
    assert state.move_history == original_history
    assert state.version == original_version

    assert new_state.called_mask != original_mask
    assert new_state.move_history == (5,)
    assert new_state.version == original_version + 1


def test_state_properties():
    """Verify state convenience properties."""
    state = create_game(seed=99)
    assert state.is_called(10) is False
    assert len(state.called_numbers) == 0

    s2 = apply_move(state, 10)
    assert s2.is_called(10) is True
    assert s2.called_numbers == [10]
