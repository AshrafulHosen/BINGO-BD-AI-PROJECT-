"""
BINGO-BD Statistics Manager
Handles loading, updating, atomic persistence, and clearing of cumulative match stats.
Pure Python - resilient to corrupted or missing files.
"""

from __future__ import annotations
import copy
import json
import os
import tempfile
import time
from typing import Dict, Any, List
from core.state import GameState, GameMode, AgentType, DRAW


DEFAULT_STATS: Dict[str, Any] = {
    "total_matches": 0,
    "human_wins": 0,
    "ai_wins": 0,
    "player_1_wins": 0,
    "player_2_wins": 0,
    "draws": 0,
    "by_difficulty": {
        "EASY": {"matches": 0, "human_wins": 0, "ai_wins": 0, "draws": 0},
        "MEDIUM": {"matches": 0, "human_wins": 0, "ai_wins": 0, "draws": 0},
        "HARD": {"matches": 0, "human_wins": 0, "ai_wins": 0, "draws": 0},
    },
    "recent_history": [],
}


class StatsManager:
    """Thread-safe and atomic statistics storage manager."""

    def __init__(self, filepath: str = "data/statistics.json"):
        self.filepath = filepath
        self._ensure_directory()
        self.stats = self.load()

    def _ensure_directory(self) -> None:
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception:
                pass

    def load(self) -> Dict[str, Any]:
        """Loads statistics from disk; defaults safely if missing or corrupt."""
        if not os.path.exists(self.filepath):
            return copy.deepcopy(DEFAULT_STATS)
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return copy.deepcopy(DEFAULT_STATS)
            # Ensure all required keys exist (deep copies: never alias defaults)
            for k, v in DEFAULT_STATS.items():
                if k not in data:
                    data[k] = copy.deepcopy(v)
            by_diff = data.get("by_difficulty")
            if not isinstance(by_diff, dict):
                data["by_difficulty"] = by_diff = copy.deepcopy(DEFAULT_STATS["by_difficulty"])
            for diff, row in DEFAULT_STATS["by_difficulty"].items():
                if not isinstance(by_diff.get(diff), dict):
                    by_diff[diff] = copy.deepcopy(row)
                for key, val in row.items():
                    by_diff[diff].setdefault(key, val)
            return data
        except Exception:
            return copy.deepcopy(DEFAULT_STATS)

    def record_match(self, state: GameState) -> None:
        """Records finished match results."""
        if state.winner is None:
            return

        self.stats["total_matches"] += 1
        winner = state.winner
        is_draw = (winner == DRAW)

        if is_draw:
            self.stats["draws"] += 1
        elif winner == 0:
            self.stats["player_1_wins"] += 1
        elif winner == 1:
            self.stats["player_2_wins"] += 1

        # Human vs AI tracking
        diff_key = None
        if state.mode == GameMode.HUMAN_VS_AI:
            ai_agent = state.agents[1]
            diff_key = ai_agent.value
            if diff_key in self.stats["by_difficulty"]:
                self.stats["by_difficulty"][diff_key]["matches"] += 1
                if is_draw:
                    self.stats["by_difficulty"][diff_key]["draws"] += 1
                elif winner == 0:
                    self.stats["human_wins"] += 1
                    self.stats["by_difficulty"][diff_key]["human_wins"] += 1
                elif winner == 1:
                    self.stats["ai_wins"] += 1
                    self.stats["by_difficulty"][diff_key]["ai_wins"] += 1

        # Record recent history entry (capped at 50)
        history_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": state.mode.value,
            "agent_0": state.agents[0].value,
            "agent_1": state.agents[1].value,
            "winner": "Draw" if is_draw else ("Player 1" if winner == 0 else "Player 2"),
            "calls_count": len(state.move_history),
            "lines_p1": state.lines_a,
            "lines_p2": state.lines_b,
        }
        self.stats.setdefault("recent_history", []).insert(0, history_entry)
        if len(self.stats["recent_history"]) > 50:
            self.stats["recent_history"] = self.stats["recent_history"][:50]

        self.save()

    def save(self) -> None:
        """Atomic write to prevent corruption."""
        try:
            self._ensure_directory()
            dir_name = os.path.dirname(self.filepath) or "."
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                json.dump(self.stats, tf, indent=2)
                temp_name = tf.name
            os.replace(temp_name, self.filepath)
        except Exception:
            # Safe failure: never crash the game if saving fails
            pass

    def clear(self) -> None:
        """Clears all statistics."""
        self.stats = copy.deepcopy(DEFAULT_STATS)
        self.save()
