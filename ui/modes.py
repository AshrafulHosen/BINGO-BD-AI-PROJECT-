"""
BINGO-BD Screen 2: Game Mode & Difficulty Selection
Matches panel 2 of the concept sheet: mode cards with icon badge + chevron,
green-glow selection, and Easy / Medium / Hard difficulty pills.
"""

from __future__ import annotations

from typing import Tuple, Callable, List, Dict, Any

import pygame

from core.state import GameMode, AgentType
from ui.theme import (
    COLORS,
    VIRTUAL_WIDTH,
    VIRTUAL_HEIGHT,
    draw_text,
    draw_rounded_rect,
    draw_shadow,
    draw_icon,
    draw_app_background,
    static_layer,
    play_sound,
    virtual_mouse,
)
from ui.widgets import Button, IconButton, SegmentedControl, draw_panel, draw_avatar
from data.settings_manager import SettingsManager

DIFFICULTIES = [("Easy", AgentType.EASY), ("Medium", AgentType.MEDIUM), ("Hard", AgentType.HARD)]
DIFF_CAPTIONS = ["Greedy heuristic", "Minimax + alpha-beta", "Monte Carlo Tree Search"]


class ModeSelectScreen:
    """Mode and difficulty selection screen."""

    PANEL = pygame.Rect(300, 20, 680, 680)

    def __init__(
        self,
        on_start_game: Callable[[GameMode, Tuple[AgentType, AgentType]], None],
        on_back: Callable[[], None],
        settings: SettingsManager,
    ):
        self.on_start_game = on_start_game
        self.on_back = on_back
        self.settings = settings

        self.selected_mode = GameMode.HUMAN_VS_AI
        self.ai_difficulty_1 = AgentType.MEDIUM
        self.ai_difficulty_2 = AgentType.HARD

        p = self.PANEL
        self.btn_back = IconButton((p.x + 44, p.y + 44), radius=22, icon="back", on_click=self.on_back)

        self.btn_start = Button((p.centerx - 150, p.bottom - 86, 300, 58), text="Start Game",
                                icon="play", variant="green", font_size=22, radius=16,
                                on_click=self._handle_start, lip=5)

        card_w, card_h = p.w - 80, 84
        x = p.x + 40
        self.mode_cards: List[Dict[str, Any]] = [
            {"mode": GameMode.HUMAN_VS_AI, "rect": pygame.Rect(x, 132, card_w, card_h),
             "title": "Human vs AI", "desc": "Play against the computer", "icon": "user",
             "color": (34, 170, 90)},
            {"mode": GameMode.HUMAN_VS_HUMAN, "rect": pygame.Rect(x, 230, card_w, card_h),
             "title": "Human vs Human", "desc": "Play with a friend on this computer", "icon": "users",
             "color": (38, 118, 226)},
            {"mode": GameMode.AI_VS_AI, "rect": pygame.Rect(x, 328, card_w, card_h),
             "title": "AI vs AI", "desc": "Watch two AIs play each other", "icon": "robot",
             "color": (128, 82, 220)},
        ]

        seg_x, seg_w = p.x + 40, p.w - 80
        self.diff_single = SegmentedControl(
            (seg_x, 470, seg_w, 50), DIFFICULTIES, self.ai_difficulty_1,
            self._set_ai1, font_size=19, gap=16, captions=DIFF_CAPTIONS)
        row_x = p.x + 190
        row_w = p.right - 40 - row_x
        self.diff_ai1 = SegmentedControl((row_x, 456, row_w, 42), DIFFICULTIES,
                                         self.ai_difficulty_1, self._set_ai1, font_size=16, gap=12)
        self.diff_ai2 = SegmentedControl((row_x, 512, row_w, 42), DIFFICULTIES,
                                         self.ai_difficulty_2, self._set_ai2, font_size=16, gap=12)

    def _set_ai1(self, d: AgentType) -> None:
        self.ai_difficulty_1 = d
        self.diff_single.value = d
        self.diff_ai1.value = d

    def _set_ai2(self, d: AgentType) -> None:
        self.ai_difficulty_2 = d

    def _handle_start(self) -> None:
        if self.selected_mode == GameMode.HUMAN_VS_AI:
            agents = (AgentType.HUMAN, self.ai_difficulty_1)
        elif self.selected_mode == GameMode.HUMAN_VS_HUMAN:
            agents = (AgentType.HUMAN, AgentType.HUMAN)
        else:
            agents = (self.ai_difficulty_1, self.ai_difficulty_2)
        self.on_start_game(self.selected_mode, agents)

    # ------------------------------------------------------------------ #
    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.on_back()
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._handle_start()
                return
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                modes = [c["mode"] for c in self.mode_cards]
                i = modes.index(self.selected_mode) + (1 if event.key == pygame.K_DOWN else -1)
                self.selected_mode = modes[i % len(modes)]
                play_sound("click", self.settings)
                return

        self.btn_back.handle_event(event, mouse_pos, self.settings)
        self.btn_start.handle_event(event, mouse_pos, self.settings)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for card in self.mode_cards:
                if card["rect"].collidepoint(mouse_pos):
                    if self.selected_mode != card["mode"]:
                        self.selected_mode = card["mode"]
                        play_sound("click", self.settings)
                    break

        if self.selected_mode == GameMode.HUMAN_VS_AI:
            self.diff_single.handle_event(event, mouse_pos, self.settings)
        elif self.selected_mode == GameMode.AI_VS_AI:
            self.diff_ai1.handle_event(event, mouse_pos, self.settings)
            self.diff_ai2.handle_event(event, mouse_pos, self.settings)

    # ------------------------------------------------------------------ #
    def _paint_static(self, surface: pygame.Surface) -> None:
        draw_app_background(surface)
        p = self.PANEL
        draw_panel(surface, p, radius=26, gradient=((18, 42, 80), (11, 28, 56)))
        draw_text(surface, "Select Game Mode", 34, COLORS["text_white"], (p.centerx, 62), weight="bold")
        draw_text(surface, "Choose how you want to play", 16, COLORS["text_muted"], (p.centerx, 98),
                  weight="semibold")
        for card in self.mode_cards:
            self._draw_mode_card(surface, card, card["mode"] == self.selected_mode, False)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(static_layer(("modes", self.selected_mode), self._paint_static), (0, 0))
        p = self.PANEL
        self.btn_back.draw(surface)

        mouse = virtual_mouse()
        for card in self.mode_cards:
            if card["mode"] != self.selected_mode and card["rect"].collidepoint(mouse):
                # hover: brighten border + subtle lift tint (drawn over the static card)
                draw_rounded_rect(surface, card["rect"], (255, 255, 255, 14), 18,
                                  COLORS["border_focus"], 1.6)

        if self.selected_mode == GameMode.HUMAN_VS_AI:
            draw_text(surface, "Choose AI Difficulty", 18, COLORS["text_white"],
                      (p.x + 40, 444), anchor="midleft", weight="bold")
            self.diff_single.draw(surface)
        elif self.selected_mode == GameMode.AI_VS_AI:
            draw_text(surface, "Configure both AI players", 18, COLORS["text_white"],
                      (p.x + 40, 428), anchor="midleft", weight="bold")
            draw_text(surface, "AI 1 (blue)", 16, COLORS["human_blue_light"], (p.x + 40, 477),
                      anchor="midleft", weight="bold")
            draw_text(surface, "AI 2 (red)", 16, COLORS["ai_red_light"], (p.x + 40, 533),
                      anchor="midleft", weight="bold")
            self.diff_ai1.draw(surface)
            self.diff_ai2.draw(surface)
        else:
            box = pygame.Rect(p.x + 40, 440, p.w - 80, 104)
            draw_rounded_rect(surface, box, COLORS["bg_card_inner"], 16, COLORS["border_light"], 1)
            draw_icon(surface, "info", (box.x + 34, box.centery), 26, COLORS["human_blue_light"])
            draw_text(surface, "Player 1 and Player 2 take turns on this computer.", 16,
                      COLORS["text_white"], (box.x + 64, box.centery - 14), anchor="midleft",
                      weight="semibold")
            draw_text(surface, "Every called number is marked on both boards.", 15,
                      COLORS["text_muted"], (box.x + 64, box.centery + 14), anchor="midleft",
                      weight="regular")

        self.btn_start.draw(surface)

    def _draw_mode_card(self, surface: pygame.Surface, card: Dict[str, Any],
                        selected: bool, hovered: bool) -> None:
        r: pygame.Rect = card["rect"]
        if selected:
            draw_shadow(surface, r, radius=18, offset=(0, 0), blur=14, alpha=120, color=(30, 200, 100))
            draw_rounded_rect(surface, r, None, 18, COLORS["green_border"], 2.2,
                              gradient=((22, 92, 74), (14, 58, 56)))
        else:
            draw_shadow(surface, r, radius=18, offset=(0, 5), blur=10, alpha=100)
            border = COLORS["border_strong"] if hovered else COLORS["border_light"]
            top = (26, 58, 104) if hovered else (20, 48, 90)
            draw_rounded_rect(surface, r, None, 18, border, 1.4, gradient=(top, (14, 36, 70)))

        icon_col = (34, 186, 96) if selected else card["color"]
        draw_avatar(surface, (r.x + 50, r.centery), 28, card["icon"], icon_col)
        draw_text(surface, card["title"], 22, COLORS["text_white"], (r.x + 96, r.centery - 13),
                  anchor="midleft", weight="bold")
        draw_text(surface, card["desc"], 15, COLORS["text_light"] if selected else COLORS["text_muted"],
                  (r.x + 96, r.centery + 16), anchor="midleft", weight="regular")
        draw_icon(surface, "check" if selected else "chevron", (r.right - 38, r.centery), 26,
                  COLORS["green_border"] if selected else COLORS["text_light"])
