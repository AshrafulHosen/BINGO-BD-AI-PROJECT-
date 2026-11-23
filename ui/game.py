from __future__ import annotations

import math
import time
from typing import Tuple, Callable, Optional, Dict, Any, List

import pygame

from core.board import ALL_LINES
from core.state import GameState, GameMode, AgentType, GameStatus, DRAW
from core.controller import GameController
from ui.theme import (
    COLORS,
    VIRTUAL_WIDTH,
    VIRTUAL_HEIGHT,
    S,
    SR,
    draw_text,
    draw_rounded_rect,
    draw_shadow,
    draw_circle,
    draw_icon,
    draw_thick_line,
    draw_app_background,
    get_overlay,
    cached_layer,
    static_layer,
    ease_out_cubic,
    play_sound,
    virtual_mouse,
)
from ui.widgets import Button, IconButton, LetterBadge, draw_panel, draw_avatar, draw_board_tile
from data.settings_manager import SettingsManager

# --------------------------------------------------------------------------- #
# Layout constants
# --------------------------------------------------------------------------- #
CARD_Y, CARD_H = 62, 86
BOARD_Y, BOARD_H = 160, 544
LEFT_X, SIDE_W = 24, 440
CENTER_X, CENTER_W = 480, 320
RIGHT_X = 816
CELL = 83
GRID = CELL * 5

DIFF_LABEL = {
    AgentType.EASY: "Easy",
    AgentType.MEDIUM: "Medium",
    AgentType.HARD: "Hard",
    AgentType.HUMAN: "Human",
}
ALGO_LABEL = {
    AgentType.EASY: "Heuristic",
    AgentType.MEDIUM: "Minimax",
    AgentType.HARD: "MCTS",
}

P_COLORS = {
    0: {"main": COLORS["human_blue"], "light": COLORS["human_blue_light"],
        "header": (COLORS["human_header_top"], COLORS["human_header_bottom"]),
        "band": COLORS["human_band"], "tint": ((22, 58, 112), (14, 38, 78))},
    1: {"main": COLORS["ai_red"], "light": COLORS["ai_red_light"],
        "header": (COLORS["ai_header_top"], COLORS["ai_header_bottom"]),
        "band": COLORS["ai_band"], "tint": ((88, 22, 44), (52, 16, 34))},
}


def board_geometry(board_rect: pygame.Rect) -> Dict[str, Any]:
    gx = board_rect.x + (board_rect.w - GRID) / 2
    gy = board_rect.y + 106
    return {
        "header": pygame.Rect(board_rect.x, board_rect.y, board_rect.w, 48),
        "band": pygame.Rect(int(gx), board_rect.y + 58, GRID, 34),
        "gx": gx,
        "gy": gy,
    }


class GameplayScreen:
    """In-game dual-board interface."""

    def __init__(
        self,
        controller: GameController,
        on_menu: Callable[[], None],
        on_game_over: Callable[[GameState], None],
        settings: SettingsManager,
    ):
        self.controller = controller
        self.on_menu = on_menu
        self.on_game_over = on_game_over
        self.settings = settings

        self.selected_number: Optional[int] = None
        self.show_progress_modal = False
        self.board_a_rect = pygame.Rect(LEFT_X, BOARD_Y, SIDE_W, BOARD_H)
        self.board_b_rect = pygame.Rect(RIGHT_X, BOARD_Y, SIDE_W, BOARD_H)
        self.center_rect = pygame.Rect(CENTER_X, BOARD_Y, CENTER_W, BOARD_H)
        self.call_card = pygame.Rect(CENTER_X, BOARD_Y, CENTER_W, 262)
        self.sheet_card = pygame.Rect(CENTER_X, BOARD_Y + 274, CENTER_W, BOARD_H - 274)

        # Toolbar
        self.btn_menu = Button((24, 12, 112, 40), text="Menu", icon="back", variant="navy",
                               font_size=15, radius=12, on_click=self.on_menu, lip=3)
        self.btn_restart = Button((146, 12, 124, 40), text="Restart", icon="restart", variant="navy",
                                  font_size=15, radius=12, on_click=self._handle_restart, lip=3)
        self.btn_progress = Button((1080, 12, 128, 40), text="Progress", icon="statistics",
                                   variant="navy", font_size=15, radius=12,
                                   on_click=self._toggle_progress_modal, lip=3)
        self.btn_sound = IconButton((1236, 32), radius=20, icon=self._sound_icon(),
                                    on_click=self._toggle_sound, icon_size=20)

        # Centre console
        cx = self.call_card.centerx
        self.btn_call_number = Button((cx - 120, self.call_card.y + 196, 240, 50), text="Call Number",
                                      icon="play", variant="green", font_size=18, radius=14,
                                      on_click=self._confirm_call_number, sound_name="")
        self.btn_ai_pause = Button((cx - 120, self.call_card.y + 196, 240, 50),
                                   text="Pause", icon="pause", variant="navy", font_size=18,
                                   radius=14, on_click=self._toggle_ai_pause)

        # Modals
        self.btn_modal_continue = Button((640 - 110, 0, 220, 50), text="Continue", variant="green",
                                         font_size=19, radius=14, on_click=self._dismiss_call_modal)
        self.btn_modal_close = IconButton((0, 0), radius=18, icon="close", variant="plain",
                                          on_click=self._dismiss_call_modal, icon_size=20)
        self.btn_progress_close = IconButton((0, 0), radius=18, icon="close", variant="plain",
                                             on_click=self._toggle_progress_modal, icon_size=20)

        # Tracking for sounds / animations
        self._seen_moves = 0
        self._prev_lines = [0, 0]
        self._modal_meta: Dict[str, Any] = {}
        self._letter_flash: Dict[int, Tuple[int, float]] = {}
        self._finished_at: Optional[float] = None
        self._game_over_sent = False
        self._digit_buffer = ""
        self._digit_time = 0.0

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _sound_icon(self) -> str:
        return "sound_on" if self.settings.sound_enabled else "sound_off"

    def _modal_duration(self) -> float:
        return 0.55 if self.settings.ai_speed == "Fast" else 1.15

    def _uses_call_modal(self) -> bool:
        return self.controller.mode != GameMode.AI_VS_AI

    def _player_name(self, p: int, short: bool = False) -> str:
        st = self.controller.state
        if st.mode == GameMode.HUMAN_VS_AI:
            return "You" if p == 0 else "AI"
        if st.mode == GameMode.HUMAN_VS_HUMAN:
            return f"Player {p + 1}"
        return f"AI {p + 1}"

    def _player_subtitle(self, p: int) -> str:
        agent = self.controller.state.agents[p]
        if agent == AgentType.HUMAN:
            return "Human"
        return f"{DIFF_LABEL[agent]} · {ALGO_LABEL[agent]}"

    def _human_can_act(self) -> bool:
        return (
            self.controller.is_human_turn()
            and self.controller.active_modal is None
            and not self.show_progress_modal
        )

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _toggle_sound(self) -> None:
        self.settings.sound_enabled = not self.settings.sound_enabled
        self.btn_sound.icon = self._sound_icon()
        if self.settings.sound_enabled:
            play_sound("click", self.settings)

    def _handle_restart(self) -> None:
        self.selected_number = None
        self.show_progress_modal = False
        self._seen_moves = 0
        self._prev_lines = [0, 0]
        self._letter_flash.clear()
        self._modal_meta = {}
        self._finished_at = None
        self._game_over_sent = False
        self.controller.restart()

    def _toggle_progress_modal(self) -> None:
        self.show_progress_modal = not self.show_progress_modal

    def _toggle_ai_pause(self) -> None:
        self.controller.is_paused = not self.controller.is_paused
        self.btn_ai_pause.text = "Resume" if self.controller.is_paused else "Pause"
        self.btn_ai_pause.icon = "play" if self.controller.is_paused else "pause"

    def _select_or_call(self, number: int) -> None:
        if not self._human_can_act() or self.controller.state.is_called(number):
            return
        if self.selected_number == number:
            self._confirm_call_number()
        else:
            self.selected_number = number
            play_sound("click", self.settings)

    def _confirm_call_number(self) -> None:
        if self.selected_number is None or not self._human_can_act():
            return
        num = self.selected_number
        if self.controller.trigger_human_move(num):
            self.selected_number = None

    def _dismiss_call_modal(self) -> None:
        self.controller.dismiss_modal()

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #
    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        # 1. Progress modal
        if self.show_progress_modal:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.show_progress_modal = False
                return
            self.btn_progress_close.handle_event(event, mouse_pos, self.settings)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not self._progress_modal_rect().collidepoint(mouse_pos):
                    self.show_progress_modal = False
            return

        # 2. Call popup: any click / key dismisses
        if self.controller.active_modal is not None and self._uses_call_modal():
            if event.type == pygame.KEYDOWN:
                self._dismiss_call_modal()
                return
            self.btn_modal_continue.handle_event(event, mouse_pos, self.settings)
            self.btn_modal_close.handle_event(event, mouse_pos, self.settings)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dismiss_call_modal()
            return

        # 3. Keyboard
        if event.type == pygame.KEYDOWN:
            self._handle_key(event)
            return

        # 4. Toolbar
        self.btn_menu.handle_event(event, mouse_pos, self.settings)
        self.btn_restart.handle_event(event, mouse_pos, self.settings)
        self.btn_progress.handle_event(event, mouse_pos, self.settings)
        self.btn_sound.handle_event(event, mouse_pos, self.settings)

        state = self.controller.state
        if state.mode == GameMode.AI_VS_AI:
            self.btn_ai_pause.handle_event(event, mouse_pos, self.settings)
            return

        # 5. Human selection / calling
        if self._human_can_act():
            if self.selected_number is not None:
                self.btn_call_number.handle_event(event, mouse_pos, self.settings)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                num = (self._number_at(self.board_a_rect, state.board_a, mouse_pos)
                       or self._number_at(self.board_b_rect, state.board_b, mouse_pos)
                       or self._sheet_number_at(mouse_pos))
                if num is not None and not state.is_called(num):
                    self._select_or_call(num)

    def _handle_key(self, event: pygame.event.Event) -> None:
        k = event.key
        if k == pygame.K_ESCAPE:
            self.selected_number = None
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if self.controller.mode == GameMode.AI_VS_AI:
                self._toggle_ai_pause()
            else:
                self._confirm_call_number()
        elif k == pygame.K_p:
            self._toggle_progress_modal()
        elif k == pygame.K_r and (event.mod & pygame.KMOD_CTRL):
            self._handle_restart()
        elif k == pygame.K_m:
            self._toggle_sound()
        elif event.unicode and event.unicode.isdigit() and self._human_can_act():
            # type a number (1-25) to select it
            now = time.time()
            if now - self._digit_time > 0.9:
                self._digit_buffer = ""
            self._digit_time = now
            self._digit_buffer = (self._digit_buffer + event.unicode)[-2:]
            for cand in (self._digit_buffer, self._digit_buffer[-1:]):
                if cand.isdigit() and 1 <= int(cand) <= 25 and not self.controller.state.is_called(int(cand)):
                    self.selected_number = int(cand)
                    break

    def _number_at(self, board_rect: pygame.Rect, board: Tuple[int, ...],
                   pos: Tuple[int, int]) -> Optional[int]:
        g = board_geometry(board_rect)
        mx, my = pos[0] - g["gx"], pos[1] - g["gy"]
        if 0 <= mx < GRID and 0 <= my < GRID:
            col, row = int(mx // CELL), int(my // CELL)
            return board[row * 5 + col]
        return None

    def _sheet_chip_center(self, n: int) -> Tuple[float, float]:
        idx = n - 1
        return (self.sheet_card.centerx - 108 + (idx % 5) * 54,
                self.sheet_card.y + 62 + (idx // 5) * 40)

    def _sheet_number_at(self, pos: Tuple[int, int]) -> Optional[int]:
        for n in range(1, 26):
            cx, cy = self._sheet_chip_center(n)
            if (pos[0] - cx) ** 2 + (pos[1] - cy) ** 2 <= 19 ** 2:
                return n
        return None

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #
    def update(self) -> None:
        ctrl = self.controller
        modal_open = ctrl.active_modal is not None and self._uses_call_modal()
        ctrl.hold_progression = modal_open or self.show_progress_modal
        ctrl.update()
        state = ctrl.state

        # New call -> sounds, line flashes, popup meta
        if len(state.move_history) > self._seen_moves:
            self._seen_moves = len(state.move_history)
            lines = [state.lines_a, state.lines_b]
            gained = [lines[0] - self._prev_lines[0], lines[1] - self._prev_lines[1]]
            for p in (0, 1):
                if gained[p] > 0 and lines[p] <= 5:
                    self._letter_flash[p] = (min(5, lines[p]) - 1, time.time())
            self._modal_meta = {"gained": gained}
            self._prev_lines = lines
            if self.selected_number is not None and state.is_called(self.selected_number):
                self.selected_number = None
            if state.status == GameStatus.PLAYING:
                play_sound("line" if any(g > 0 for g in gained) else "call", self.settings)
            if not self._uses_call_modal():
                ctrl.dismiss_modal()

        # Auto-dismiss call popup
        if ctrl.active_modal is not None:
            if time.time() - ctrl.active_modal.get("timestamp", 0) > self._modal_duration():
                ctrl.dismiss_modal()

        # Clear selection when it's no longer a human's turn
        if not ctrl.is_human_turn():
            self.selected_number = None

        # Game over: show the final board briefly, then transition
        if state.status == GameStatus.FINISHED and not self._game_over_sent:
            if ctrl.active_modal is None:
                if self._finished_at is None:
                    self._finished_at = time.time()
                elif time.time() - self._finished_at > 0.9:
                    self._game_over_sent = True
                    self.on_game_over(state)

    # ------------------------------------------------------------------ #
    # Draw
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        state = self.controller.state
        surface.blit(static_layer(self._static_key(state), lambda s: self._paint_static(s, state)), (0, 0))

        self._draw_toolbar(surface, state)
        self._draw_player_card(surface, state, 0)
        self._draw_turn_card(surface, state)
        self._draw_player_card(surface, state, 1)

        hover_num = None
        if self._human_can_act():
            m = virtual_mouse()
            hover_num = (self._number_at(self.board_a_rect, state.board_a, m)
                         or self._number_at(self.board_b_rect, state.board_b, m)
                         or self._sheet_number_at(m))
            if hover_num is not None and state.is_called(hover_num):
                hover_num = None

        self._draw_board(surface, state, 0, hover_num)
        self._draw_board(surface, state, 1, hover_num)
        self._draw_call_card(surface, state)
        self._draw_call_sheet(surface, state, hover_num)

        if self.controller.active_modal is not None and self._uses_call_modal():
            self._draw_call_modal(surface)
        if self.show_progress_modal:
            self._draw_progress_modal(surface, state)

    # ------------------------------------------------------------------ #
    # Static chrome (pre-composed, see ui.theme.static_layer)
    # ------------------------------------------------------------------ #
    def _static_key(self, state: GameState) -> Tuple[Any, ...]:
        turn = state.current_player if state.status == GameStatus.PLAYING else -1
        return ("game", state.mode, state.agents, turn)

    def _paint_static(self, surface: pygame.Surface, state: GameState) -> None:
        draw_app_background(surface)
        self._paint_toolbar_label(surface, state)
        playing = state.status == GameStatus.PLAYING
        for p in (0, 1):
            pc = P_COLORS[p]
            r = pygame.Rect(LEFT_X if p == 0 else RIGHT_X, CARD_Y, SIDE_W, CARD_H)
            active = playing and state.current_player == p
            if active:
                draw_shadow(surface, r, radius=18, offset=(0, 0), blur=14, alpha=150, color=pc["main"])
            draw_rounded_rect(surface, r, None, 18, pc["light"] if active else COLORS["border_light"],
                              2 if active else 1.2, gradient=pc["tint"] if active else
                              ((20, 46, 88), (13, 32, 64)))
        draw_rounded_rect(surface, (CENTER_X, CARD_Y, CENTER_W, CARD_H), None, 18, COLORS["border_light"],
                          1.2, gradient=((20, 46, 88), (13, 32, 64)))
        for p in (0, 1):
            pc = P_COLORS[p]
            br = self.board_a_rect if p == 0 else self.board_b_rect
            g = board_geometry(br)
            active = playing and state.current_player == p and state.agents[p] == AgentType.HUMAN
            if active:
                draw_shadow(surface, br, radius=22, offset=(0, 0), blur=18, alpha=150, color=pc["main"])
            else:
                draw_shadow(surface, br, radius=22, offset=(0, 8), blur=16, alpha=130)
            draw_rounded_rect(surface, br, COLORS["bg_card"], 22, pc["light"] if active else pc["main"], 2)

            # header with rounded top corners only (clipped)
            hdr = g["header"]
            surface.set_clip(SR(hdr))
            draw_rounded_rect(surface, (hdr.x, hdr.y, hdr.w, hdr.h + 30), None, 22,
                              gradient=(pc["header"][0], pc["header"][1]))
            surface.set_clip(None)
            if state.mode == GameMode.HUMAN_VS_AI:
                title = "Your Board" if p == 0 else "AI Board"
            else:
                title = f"{self._player_name(p)} Board"
            draw_text(surface, title, 21, COLORS["text_white"], hdr.center, weight="bold",
                      shadow=((0, 0, 0), 1.5))

            # B I N G O column band
            band = g["band"]
            draw_rounded_rect(surface, band, pc["band"], 10)
            for c, ch in enumerate("BINGO"):
                draw_text(surface, ch, 18, COLORS["text_white"], (g["gx"] + c * CELL + CELL / 2, band.centery),
                          weight="black")

            # grid backdrop + tiles
            gx, gy = g["gx"], g["gy"]
            draw_rounded_rect(surface, (gx - 5, gy - 5, GRID + 10, GRID + 10), (214, 224, 238), 14)
        draw_panel(surface, self.call_card, radius=20, gradient=((20, 46, 88), (12, 30, 60)))
        draw_panel(surface, self.sheet_card, radius=20, gradient=((18, 42, 80), (11, 28, 56)))
        draw_text(surface, "Called Numbers", 16, COLORS["text_white"],
                  (self.sheet_card.x + 20, self.sheet_card.y + 24), anchor="midleft")

    # -- toolbar --------------------------------------------------------- #
    def _draw_toolbar(self, surface: pygame.Surface, state: GameState) -> None:
        for b in (self.btn_menu, self.btn_restart, self.btn_progress, self.btn_sound):
            b.draw(surface)

    def _paint_toolbar_label(self, surface: pygame.Surface, state: GameState) -> None:
        if state.mode == GameMode.HUMAN_VS_AI:
            label = f"Human vs AI  •  {DIFF_LABEL[state.agents[1]]} ({ALGO_LABEL[state.agents[1]]})"
        elif state.mode == GameMode.HUMAN_VS_HUMAN:
            label = "Human vs Human  •  Local match"
        else:
            label = (f"AI vs AI  •  {DIFF_LABEL[state.agents[0]]} vs {DIFF_LABEL[state.agents[1]]}")
        draw_text(surface, label, 15, COLORS["text_muted"], (640, 32), weight="semibold")

    # -- top cards ------------------------------------------------------- #
    def _draw_player_card(self, surface: pygame.Surface, state: GameState, p: int) -> None:
        pc = P_COLORS[p]
        x = LEFT_X if p == 0 else RIGHT_X
        r = pygame.Rect(x, CARD_Y, SIDE_W, CARD_H)
        active = state.status == GameStatus.PLAYING and state.current_player == p
        is_ai = state.agents[p] != AgentType.HUMAN
        lines = min(5, state.lines_a if p == 0 else state.lines_b)
        flash = self._letter_flash.get(p)
        pulse = flash[0] if flash and time.time() - flash[1] < 1.6 else None
        name = self._player_name(p)
        sub = self._player_subtitle(p)
        icon = "robot" if is_ai else "user"

        if p == 0:
            draw_avatar(surface, (r.x + 48, r.centery), 30, icon, pc["main"],
                        ring=(255, 255, 255, 60) if active else None)
            nx = r.x + 94
            draw_text(surface, name, 21, COLORS["text_white"], (nx, r.y + 24), anchor="midleft")
            draw_text(surface, sub, 12, COLORS["text_muted"], (nx + _tw(name, 21) + 10, r.y + 25),
                      anchor="midleft", weight="semibold")
            LetterBadge.draw_letter_bar(surface, nx, r.y + 60, lines, pc["main"], radius=13,
                                        spacing=33, anchor="left", pulse_index=pulse)
            draw_text(surface, f"{lines}/5", 28, COLORS["gold_glow"], (r.right - 24, r.centery - 6),
                      anchor="midright", weight="black")
            draw_text(surface, "lines", 12, COLORS["text_muted"], (r.right - 24, r.centery + 20),
                      anchor="midright", weight="semibold")
        else:
            draw_avatar(surface, (r.right - 48, r.centery), 30, icon, pc["main"],
                        ring=(255, 255, 255, 60) if active else None)
            nx = r.right - 94
            draw_text(surface, name, 21, COLORS["text_white"], (nx, r.y + 24), anchor="midright")
            draw_text(surface, sub, 12, COLORS["text_muted"], (nx - _tw(name, 21) - 10, r.y + 25),
                      anchor="midright", weight="semibold")
            bar_w = 4 * 33 + 26
            LetterBadge.draw_letter_bar(surface, nx - bar_w, r.y + 60, lines, pc["main"], radius=13,
                                        spacing=33, anchor="left", pulse_index=pulse)
            draw_text(surface, f"{lines}/5", 28, COLORS["gold_glow"], (r.x + 24, r.centery - 6),
                      anchor="midleft", weight="black")
            draw_text(surface, "lines", 12, COLORS["text_muted"], (r.x + 24, r.centery + 20),
                      anchor="midleft", weight="semibold")

    def _draw_turn_card(self, surface: pygame.Surface, state: GameState) -> None:
        r = pygame.Rect(CENTER_X, CARD_Y, CENTER_W, CARD_H)
        ctrl = self.controller
        p = state.current_player
        if state.status == GameStatus.FINISHED:
            if state.winner == DRAW:
                title, col = "It's a draw!", COLORS["gold_glow"]
            else:
                title, col = f"{self._player_name(state.winner)} got BINGO!", COLORS["gold_glow"]
            sub = "Final board"
        elif ctrl.is_thinking or state.agents[p] != AgentType.HUMAN:
            dots = "." * (1 + int(time.time() * 3) % 3)
            if state.mode == GameMode.AI_VS_AI and ctrl.is_paused:
                title, col, sub = "Paused", COLORS["gold_glow"], "Press Resume to continue"
            else:
                title = f"{self._player_name(p)} is thinking{dots}"
                col = P_COLORS[p]["light"]
                sub = self._player_subtitle(p)
        else:
            if state.mode == GameMode.HUMAN_VS_AI:
                title = "Your turn"
            else:
                title = f"{self._player_name(p)}'s turn"
            col = COLORS["btn_green_hover"]
            sub = "Pick a number, then Call"
        draw_text(surface, "TURN", 11, COLORS["text_dim"], (r.centerx, r.y + 18), weight="black")
        if state.status == GameStatus.PLAYING:
            draw_circle(surface, (r.centerx - _tw(title, 20) / 2 - 14, r.y + 44), 5, col)
        draw_text(surface, title, 20, col, (r.centerx, r.y + 44), weight="bold", max_width=r.w - 40)
        draw_text(surface, sub, 12, COLORS["text_muted"], (r.centerx, r.y + 68), weight="semibold")

    # -- boards ---------------------------------------------------------- #
    def _draw_board(self, surface: pygame.Surface, state: GameState, p: int,
                    hover_num: Optional[int]) -> None:
        pc = P_COLORS[p]
        br = self.board_a_rect if p == 0 else self.board_b_rect
        board = state.board_a if p == 0 else state.board_b
        g = board_geometry(br)
        active = (state.status == GameStatus.PLAYING and state.current_player == p
                  and state.agents[p] == AgentType.HUMAN)

        gx, gy = g["gx"], g["gy"]
        completed = state.completed_line_indices_a() if p == 0 else state.completed_line_indices_b()
        on_line_cells = {c for li in completed for c in ALL_LINES[li]}
        latest = state.move_history[-1] if state.move_history else None
        can_click = self._human_can_act()
        # pass 1: tiles, pass 2: completed-line strokes, pass 3: markers + numbers
        for stage in ("bg", "lines", "fg"):
            if stage == "lines":
                if completed:
                    key = ("lines", tuple(completed))
                    layer = cached_layer(key, lambda: self._build_line_layer(completed))
                    surface.blit(layer, SR((gx, gy, GRID, GRID)).topleft)
                continue
            for idx, num in enumerate(board):
                row, col = divmod(idx, 5)
                tile = pygame.Rect(int(gx + col * CELL + 3), int(gy + row * CELL + 3), CELL - 6, CELL - 6)
                called = state.is_called(num)
                draw_board_tile(
                    surface, tile, num, called,
                    hovered=(hover_num == num and not called),
                    selected=(self.selected_number == num and not called),
                    latest=(num == latest),
                    mark_color=COLORS["mark_blue"],
                    clickable=can_click and not called,
                    on_line=idx in on_line_cells,
                    stage=stage,
                )

    @staticmethod
    def _build_line_layer(completed: List[int]) -> pygame.Surface:
        w = S(GRID)
        layer = pygame.Surface((w, w), pygame.SRCALPHA)
        layer.fill((0, 0, 0, 0))
        for li in completed:
            cells = ALL_LINES[li]
            r0, c0 = divmod(cells[0], 5)
            r1, c1 = divmod(cells[-1], 5)
            p1 = (c0 * CELL + CELL / 2, r0 * CELL + CELL / 2)
            p2 = (c1 * CELL + CELL / 2, r1 * CELL + CELL / 2)
            draw_thick_line(layer, p1, p2, 12, (34, 197, 94, 210))
        return layer

    # -- centre column ---------------------------------------------------- #
    def _draw_call_card(self, surface: pygame.Surface, state: GameState) -> None:
        r = self.call_card
        cx = r.centerx
        ctrl = self.controller

        if self.selected_number is not None:
            label, num = "SELECTED NUMBER", self.selected_number
            caption, cap_col = "Next number to be called", COLORS["btn_green_hover"]
        elif state.move_history:
            label, num = "LAST CALLED", state.move_history[-1]
            caption, cap_col = "Marked on both boards", COLORS["text_muted"]
        else:
            label, num = "NEXT NUMBER", None
            caption, cap_col = "No numbers called yet", COLORS["text_muted"]
        if self._human_can_act() and self.selected_number is None:
            caption, cap_col = "Click a number on any board", COLORS["text_light"]
        elif ctrl.is_thinking:
            caption, cap_col = "AI is choosing a number…", P_COLORS[state.current_player]["light"]

        draw_text(surface, label, 12, COLORS["text_dim"], (cx, r.y + 26), weight="black")
        center = (cx, r.y + 104)
        if self.selected_number is not None:
            pulse = 0.5 + 0.5 * math.sin(time.time() * 5)
            draw_circle(surface, center, 62 + 4 * pulse, (255, 196, 46, 50))
        draw_circle(surface, center, 58, (10, 24, 50))
        draw_circle(surface, center, 54, None, (255, 236, 160), 2,
                    gradient=(COLORS["gold_glow"], COLORS["gold_dark"]))
        draw_text(surface, str(num) if num is not None else "–", 46, COLORS["text_dark"], center,
                  weight="black")
        draw_text(surface, caption, 14, cap_col, (cx, r.y + 178), weight="semibold", max_width=r.w - 24)

        if state.mode == GameMode.AI_VS_AI:
            self.btn_ai_pause.enabled = state.status == GameStatus.PLAYING
            self.btn_ai_pause.draw(surface)
        else:
            human_turn = self._human_can_act()
            self.btn_call_number.enabled = human_turn and self.selected_number is not None
            self.btn_call_number.text = "Call Number" if human_turn or state.status != GameStatus.PLAYING \
                else "Waiting…"
            self.btn_call_number.draw(surface)

    def _draw_call_sheet(self, surface: pygame.Surface, state: GameState,
                         hover_num: Optional[int]) -> None:
        r = self.sheet_card
        draw_text(surface, f"{len(state.move_history)}/25", 15, COLORS["gold_glow"],
                  (r.right - 20, r.y + 24), anchor="midright", weight="black")
        latest = state.move_history[-1] if state.move_history else None
        for n in range(1, 26):
            c = self._sheet_chip_center(n)
            called = state.is_called(n)
            if n == latest:
                draw_circle(surface, c, 18, None, (255, 236, 160), 1.5,
                            gradient=(COLORS["gold_glow"], COLORS["gold_dark"]))
                tcol = COLORS["text_dark"]
            elif called:
                draw_circle(surface, c, 18, None, COLORS["mark_blue_ring"], 1,
                            gradient=((60, 146, 250), COLORS["mark_blue"]))
                tcol = COLORS["text_white"]
            elif n == self.selected_number:
                draw_circle(surface, c, 18, (60, 52, 20), COLORS["gold"], 2)
                tcol = COLORS["gold_glow"]
            elif n == hover_num:
                draw_circle(surface, c, 18, (34, 70, 126), COLORS["border_focus"], 1.5)
                tcol = COLORS["text_white"]
            else:
                draw_circle(surface, c, 18, (16, 38, 72), COLORS["border_light"], 1)
                tcol = COLORS["text_dim"]
            draw_text(surface, str(n), 14, tcol, c, weight="bold")

        diag = self.controller.last_ai_diagnostics
        if diag and diag.get("algorithm") not in (None, "Human"):
            draw_text(surface, _diag_text(diag), 12, COLORS["text_muted"], (r.centerx, r.bottom - 18),
                      weight="semibold", max_width=r.w - 24)

    # -- modals ---------------------------------------------------------- #
    def _draw_call_modal(self, surface: pygame.Surface) -> None:
        info = self.controller.active_modal
        if not info:
            return
        age = time.time() - info.get("timestamp", 0)
        t = ease_out_cubic(age / 0.18)
        surface.blit(get_overlay((4, 10, 24, int(150 * t))), (0, 0))

        mw, mh = 440, 340
        mx = (VIRTUAL_WIDTH - mw) // 2
        my = int((VIRTUAL_HEIGHT - mh) // 2 + 16 * (1 - t))
        rect = pygame.Rect(mx, my, mw, mh)
        draw_panel(surface, rect, radius=24, border=COLORS["border_focus"], border_width=2,
                   gradient=((22, 50, 96), (12, 30, 62)))

        p = info["player"]
        state = self.controller.state
        if state.mode == GameMode.HUMAN_VS_AI:
            title = "You called" if p == 0 else "AI called"
        else:
            title = f"{self._player_name(p)} called"
        draw_text(surface, title, 26, COLORS["text_white"], (rect.centerx, my + 44))
        self.btn_modal_close.rect.center = (rect.right - 32, my + 32)
        self.btn_modal_close.draw(surface)

        c = (rect.centerx, my + 140)
        for a_deg in (-35, 0, 35, 145, 180, 215):   # radiating ticks left/right (concept sheet)
            a = math.radians(a_deg)
            r1, r2 = 72, 92
            draw_thick_line(surface, (c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a)),
                            (c[0] + r2 * math.cos(a), c[1] + r2 * math.sin(a)), 4, COLORS["human_blue_light"])
        draw_circle(surface, c, 62, (12, 30, 64))
        draw_circle(surface, c, 58, None, (170, 210, 255), 3, gradient=((70, 156, 255), (20, 100, 220)))
        draw_text(surface, str(info["number"]), 56, COLORS["text_white"], c, weight="black")

        gained = self._modal_meta.get("gained", [0, 0])
        if any(gained):
            parts = [f"+{g} line{'s' if g > 1 else ''} for {self._player_name(i)}"
                     for i, g in enumerate(gained) if g > 0]
            draw_text(surface, "  •  ".join(parts), 15, COLORS["btn_green_hover"], (rect.centerx, my + 228),
                      weight="bold", max_width=mw - 40)
            draw_text(surface, f"{info['number']} has been marked on both boards.", 14, COLORS["text_light"],
                      (rect.centerx, my + 250), weight="semibold")
        else:
            draw_text(surface, f"{info['number']} has been marked on both boards.", 16, COLORS["text_light"],
                      (rect.centerx, my + 238), weight="semibold")
        self.btn_modal_continue.rect.topleft = (rect.centerx - 110, my + mh - 74)
        self.btn_modal_continue.draw(surface)

    def _progress_modal_rect(self) -> pygame.Rect:
        mw, mh = 620, 446
        return pygame.Rect((VIRTUAL_WIDTH - mw) // 2, (VIRTUAL_HEIGHT - mh) // 2, mw, mh)

    def _draw_progress_modal(self, surface: pygame.Surface, state: GameState) -> None:
        surface.blit(get_overlay(), (0, 0))
        rect = self._progress_modal_rect()
        draw_panel(surface, rect, radius=24, border=COLORS["border_strong"], border_width=1.5,
                   gradient=((20, 46, 88), (11, 28, 58)))
        draw_text(surface, "BINGO Progress", 28, COLORS["text_white"], (rect.x + 32, rect.y + 44),
                  anchor="midleft")
        self.btn_progress_close.rect.center = (rect.right - 36, rect.y + 40)
        self.btn_progress_close.draw(surface)

        for p in (0, 1):
            pc = P_COLORS[p]
            row = pygame.Rect(rect.x + 24, rect.y + 84 + p * 134, rect.w - 48, 120)
            draw_rounded_rect(surface, row, None, 18, pc["main"], 1.8, gradient=pc["tint"])
            is_ai = state.agents[p] != AgentType.HUMAN
            draw_avatar(surface, (row.x + 52, row.centery), 32, "robot" if is_ai else "user", pc["main"])
            lines = state.lines_a if p == 0 else state.lines_b
            marked = state.marked_mask_a if p == 0 else state.marked_mask_b
            best = max(sum((marked >> c) & 1 for c in line) for line in ALL_LINES
                       if not all((marked >> c) & 1 for c in line)) if lines < 12 else 5
            draw_text(surface, self._player_name(p), 21, COLORS["text_white"], (row.x + 104, row.y + 28),
                      anchor="midleft")
            draw_text(surface, self._player_subtitle(p), 12, COLORS["text_muted"],
                      (row.x + 104 + _tw(self._player_name(p), 21) + 10, row.y + 29), anchor="midleft",
                      weight="semibold")
            LetterBadge.draw_letter_bar(surface, row.x + 104, row.y + 76, min(5, lines), pc["main"],
                                        radius=24, spacing=60, anchor="left")
            draw_text(surface, f"{min(5, lines)}/5", 30, COLORS["text_white"], (row.right - 28, row.y + 62),
                      anchor="midright", weight="black")
            if lines < 5:
                draw_text(surface, f"best open line {best}/5", 12, COLORS["text_muted"],
                          (row.right - 28, row.y + 92), anchor="midright", weight="semibold")

        tip = pygame.Rect(rect.x + 24, rect.bottom - 86, rect.w - 48, 62)
        draw_rounded_rect(surface, tip, COLORS["bg_card_inner"], 14, COLORS["border_light"], 1)
        draw_icon(surface, "info", (tip.x + 32, tip.centery), 24, COLORS["human_blue_light"])
        draw_text(surface, "Complete 5 lines (row, column or diagonal) to win BINGO!", 15,
                  COLORS["text_light"], (tip.x + 60, tip.centery), anchor="midleft", weight="semibold")


# --------------------------------------------------------------------------- #
def _tw(text: str, size: float, weight: str = "bold") -> float:
    from ui.theme import text_width
    return text_width(text, size, weight)


def _diag_text(diag: Dict[str, Any]) -> str:
    algo = diag.get("algorithm", "AI")
    ms = diag.get("latency_ms", 0)
    if "simulations" in diag:
        extra = f"{diag['simulations']} sims · win est. {int(round(diag.get('win_rate', 0) * 100))}%"
        if diag.get("note"):
            extra = diag["note"]
    elif "depth" in diag:
        extra = f"depth {diag['depth']} · {diag.get('nodes_evaluated', 0)} nodes"
    elif "evaluations" in diag:
        extra = f"{diag['evaluations']} successors scored"
    else:
        extra = ""
    return f"{algo}: called {diag.get('selected_move', '?')} · {extra} · {ms:.0f} ms" if extra \
        else f"{algo} · {ms:.0f} ms"
