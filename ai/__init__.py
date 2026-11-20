"""
BINGO-BD AI Package
Exposes unified choose_move interface with difficulty dispatching and robust fallback.
"""

from __future__ import annotations
import logging
from typing import Tuple, Dict, Any, Optional
from core.state import GameState, AgentType
from core.rules import legal_moves
from ai.heuristic import choose_heuristic_move
from ai.minimax import choose_minimax_move
from ai.mcts import choose_mcts_move

logger = logging.getLogger(__name__)


def choose_move(
    state: GameState,
    player: int,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Selects a legal move for `player` using the agent type configured in the state
    or specified in `config`. If search encounters an error, logs and falls back to
    the heuristic greedy selector.
    """
    config = config or {}
    agent_type = state.agents[player] if player < len(state.agents) else AgentType.EASY

    # Allow overriding difficulty via config
    if "difficulty" in config:
        diff_str = str(config["difficulty"]).upper()
        if hasattr(AgentType, diff_str):
            agent_type = AgentType[diff_str]

    seed = config.get("seed")

    try:
        if agent_type == AgentType.EASY:
            return choose_heuristic_move(state, player, seed=seed)
        elif agent_type == AgentType.MEDIUM:
            depth = config.get("depth", 2)
            time_limit = config.get("time_limit_sec", 1.0)
            return choose_minimax_move(
                state, player, depth=depth, time_limit_sec=time_limit, seed=seed
            )
        elif agent_type == AgentType.HARD:
            rollouts = config.get("rollouts", 2000)
            time_limit = config.get("time_limit_sec", 1.5)
            return choose_mcts_move(
                state, player, rollouts=rollouts, time_limit_sec=time_limit, seed=seed
            )
        else:
            # Default fallback for unknown or human in AI dispatch
            return choose_heuristic_move(state, player, seed=seed)

    except Exception as e:
        logger.error(f"Error in {agent_type} AI search: {e}. Falling back to heuristic.", exc_info=True)
        try:
            return choose_heuristic_move(state, player, seed=seed)
        except Exception:
            # Ultimate emergency fallback: first legal move
            valid = legal_moves(state)
            if valid:
                return valid[0], {"algorithm": "EmergencyFallback", "selected_move": valid[0]}
            raise RuntimeError("No legal moves available to select.")


__all__ = [
    "choose_move",
    "choose_heuristic_move",
    "choose_minimax_move",
    "choose_mcts_move",
]
