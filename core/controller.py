"""
BINGO-BD Game Controller
Coordinates game progression, non-blocking AI background threading,
state-version guards, and turn sequencing across all three game modes.
Pure Python - NO Pygame imports.
"""

from __future__ import annotations
import threading
import time
from typing import Optional, Callable, Dict, Any
from core.state import GameState, GameMode, AgentType, GameStatus
from core.rules import create_game, apply_move, is_legal_move, legal_moves
from ai import choose_move


class GameController:
    """
    Manages active match lifecycle, threading, and mode transitions.

    Thread-safety model
    -------------------
    * The AI runs on a daemon worker thread and only ever sees an immutable
      GameState snapshot.  It never touches live controller state except to
      deposit its result under ``_ai_lock``.
    * Every result is tagged with ``(generation, state.version)``.  The
      generation counter is bumped on restart/cancel, so a worker that was
      started for a previous match can never have its move applied to a new
      match - even when both matches happen to be at version 0 (PRD AC-07).
    """

    def __init__(
        self,
        mode: GameMode = GameMode.HUMAN_VS_AI,
        agents: tuple[AgentType, AgentType] = (AgentType.HUMAN, AgentType.EASY),
        seed: Optional[int] = None,
        on_state_changed: Optional[Callable[[GameState], None]] = None,
        on_move_called: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
        on_game_finished: Optional[Callable[[GameState], None]] = None,
        ai_config: Optional[Dict[str, Any]] = None,
    ):
        self.mode = mode
        self.agents = agents
        self.seed = seed
        self.state: GameState = create_game(mode, agents, seed=seed)
        self.ai_config: Dict[str, Any] = dict(ai_config or {})

        self.on_state_changed = on_state_changed
        self.on_move_called = on_move_called
        self.on_game_finished = on_game_finished

        # AI threading state
        self._ai_thread: Optional[threading.Thread] = None
        self._ai_lock = threading.Lock()
        # (generation, version, move, diagnostics)
        self._ai_result: Optional[tuple[int, int, int, Dict[str, Any]]] = None
        self._generation = 0
        self.is_thinking = False
        self.thinking_started_at = 0.0
        self.last_ai_diagnostics: Dict[str, Any] = {}

        # Progression control
        self.is_paused = False          # AI vs AI pause toggle
        self.hold_progression = False   # UI hold (e.g. while call popup is shown)
        self.step_delay_sec = 0.8
        self._last_move_timestamp = time.time()

        # Call feedback overlay state
        self.active_modal: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def _invalidate_workers(self) -> None:
        """Ignore any in-flight AI computation from now on."""
        with self._ai_lock:
            self._generation += 1
            self._ai_result = None
            self.is_thinking = False

    def restart(self, seed: Optional[int] = None) -> None:
        """Completely resets previous game state with new randomized boards."""
        self._invalidate_workers()

        if seed is not None:
            self.seed = seed
        self.state = create_game(self.mode, self.agents, seed=self.seed)
        self.active_modal = None
        self.last_ai_diagnostics = {}
        self.hold_progression = False
        self._last_move_timestamp = time.time()

        if self.on_state_changed:
            self.on_state_changed(self.state)

    def cancel(self) -> None:
        """Abandon the match (e.g. user navigated back to the menu)."""
        self._invalidate_workers()
        self.active_modal = None

    # ------------------------------------------------------------------ #
    # Moves
    # ------------------------------------------------------------------ #
    def is_human_turn(self) -> bool:
        return (
            self.state.status == GameStatus.PLAYING
            and not self.is_thinking
            and self.state.agents[self.state.current_player] == AgentType.HUMAN
        )

    def trigger_human_move(self, number: int) -> bool:
        """
        Processes human player move request if legal and valid for current turn.
        Returns True if accepted, False otherwise.
        """
        if not self.is_human_turn():
            return False
        if not is_legal_move(self.state, number):
            return False
        player = self.state.current_player
        self._apply_player_move(player, int(number), {"algorithm": "Human"})
        return True

    def _apply_player_move(self, player: int, number: int, diag: Dict[str, Any]) -> None:
        """Applies move and updates callbacks and feedback modal."""
        if self.state.agents[player] != AgentType.HUMAN:
            self.last_ai_diagnostics = diag
        self.state = apply_move(self.state, number)
        self._last_move_timestamp = time.time()

        # Feedback popup details (UI decides how long to show it)
        self.active_modal = {
            "player": player,
            "number": number,
            "timestamp": time.time(),
            "diagnostics": diag,
        }

        if self.on_move_called:
            self.on_move_called(player, number, diag)

        if self.on_state_changed:
            self.on_state_changed(self.state)

        if self.state.status == GameStatus.FINISHED and self.on_game_finished:
            self.on_game_finished(self.state)

    # ------------------------------------------------------------------ #
    # Frame update
    # ------------------------------------------------------------------ #
    def update(self) -> None:
        """
        Called once per frame in the main loop to process background AI results,
        advance AI vs AI matches, and monitor turn scheduling.
        """
        # 1. Collect a finished AI result (if any)
        result = None
        with self._ai_lock:
            if self._ai_result is not None:
                result = self._ai_result
                self._ai_result = None
                self.is_thinking = False

        if result is not None:
            gen, ver, move, diag = result
            # Generation + version guard: discard anything stale
            if (
                gen == self._generation
                and ver == self.state.version
                and self.state.status == GameStatus.PLAYING
                and is_legal_move(self.state, move)
            ):
                self._apply_player_move(self.state.current_player, move, diag)
                return

        # 2. Dispatch AI if it's an AI's turn
        if self.state.status != GameStatus.PLAYING or self.is_thinking:
            return
        current_agent = self.state.agents[self.state.current_player]
        if current_agent == AgentType.HUMAN:
            return
        if self.hold_progression:
            return
        if self.mode == GameMode.AI_VS_AI:
            if self.is_paused:
                return
            if time.time() - self._last_move_timestamp < self.step_delay_sec:
                return
        self._dispatch_ai_worker(self.state.current_player)

    def _dispatch_ai_worker(self, player: int) -> None:
        """Launches AI decision computation on a background worker thread."""
        with self._ai_lock:
            self.is_thinking = True
            generation = self._generation
        self.thinking_started_at = time.time()
        state_snapshot = self.state
        config = dict(self.ai_config)

        def worker() -> None:
            try:
                move, diag = choose_move(state_snapshot, player, config)
            except Exception as ex:  # pragma: no cover - defensive
                valid = legal_moves(state_snapshot)
                move = valid[0] if valid else 1
                diag = {"algorithm": "WorkerFallback", "error": str(ex)}

            with self._ai_lock:
                if generation == self._generation:
                    self._ai_result = (generation, state_snapshot.version, move, diag)

        self._ai_thread = threading.Thread(target=worker, daemon=True)
        self._ai_thread.start()

    def wait_for_ai(self, timeout: float = 5.0) -> None:
        """Test helper: block until the current worker has finished."""
        t = self._ai_thread
        if t is not None:
            t.join(timeout)

    def dismiss_modal(self) -> None:
        """Dismisses the number-called modal overlay."""
        self.active_modal = None
