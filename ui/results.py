"""
BINGO-BD Screen 6: Game Over (Victory / Defeat / Draw)
Matches panel 6 of the concept sheet: radial rays, falling confetti, golden
crown, outlined "BINGO!" headline, B-I-N-G-O badges, Play Again / Back to Menu.
"""

from __future__ import annotations

import math
import random
import time
from typing import Tuple, Callable, List

import pygame

from core.state import GameState, GameMode, AgentType, DRAW
from ui.theme import (
    COLORS,
    VIRTUAL_WIDTH,
    VIRTUAL_HEIGHT,
    S,
    SP,
    draw_text,
    draw_rounded_rect,
    draw_circle,
    draw_icon,
    cached_layer,
    static_layer,
    ease_out_cubic,
    play_sound,
    text_width,
    _vertical_gradient,
)
from ui.widgets import Button, LetterBadge
from data.stats_manager import StatsManager
from data.settings_manager import SettingsManager

DIFF = {AgentType.EASY: "Easy", AgentType.MEDIUM: "Medium", AgentType.HARD: "Hard"}
CONFETTI_COLORS = [(255, 196, 46), (34, 197, 94), (56, 160, 255), (244, 63, 94), (255, 255, 255),
                   (168, 85, 247)]


def _build_rays(tint: Tuple[int, int, int]) -> pygame.Surface:
    w, h = S(VIRTUAL_WIDTH), S(VIRTUAL_HEIGHT)
    surf = _vertical_gradient((w, h), (14, 30, 60), (6, 14, 30)).convert_alpha()
    rays = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = S(640), S(200)
    rad = S(900)
    n = 18
    for i in range(n):
        a1 = (i / n) * 2 * math.pi
        a2 = ((i + 0.5) / n) * 2 * math.pi
        pygame.draw.polygon(rays, (*tint, 16), [(cx, cy),
                                                 (cx + rad * math.cos(a1), cy + rad * math.sin(a1)),
                                                 (cx + rad * math.cos(a2), cy + rad * math.sin(a2))])
    surf.blit(rays, (0, 0))
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(16, 0, -1):
        pygame.draw.circle(glow, (*tint, 7), (cx, cy), S(18 * i))
    surf.blit(glow, (0, 0))
    opaque = pygame.Surface((w, h))
    opaque.blit(surf, (0, 0))
    return opaque


class GameOverScreen:
    """Victory, Defeat, or Draw screen with statistics recording."""

    def __init__(
        self,
        state: GameState,
        on_play_again: Callable[[], None],
        on_back_menu: Callable[[], None],
        stats_mgr: StatsManager,
        settings: SettingsManager,
    ):
        self.state = state
        self.on_play_again = on_play_again
        self.on_back_menu = on_back_menu
        self.stats_mgr = stats_mgr
        self.settings = settings
        self.created = time.time()

        self.stats_mgr.record_match(state)

        btn_w, btn_h, gap = 250, 60, 30
        x0 = (VIRTUAL_WIDTH - (btn_w * 2 + gap)) // 2
        self.btn_play_again = Button((x0, 588, btn_w, btn_h), text="Play Again", icon="play",
                                     variant="green", font_size=22, radius=16,
                                     on_click=self.on_play_again, lip=5)
        self.btn_menu = Button((x0 + btn_w + gap, 588, btn_w, btn_h), text="Back to Menu", icon="home",
                               variant="navy", font_size=20, radius=16, on_click=self.on_back_menu, lip=5)

        self._init_outcome()

        rng = random.Random(state.version * 7919 + len(state.move_history))
        self.confetti: List[tuple] = []
        for _ in range(70):
            self.confetti.append((
                rng.uniform(20, VIRTUAL_WIDTH - 20),   # x
                rng.uniform(-720, 0),                  # phase
                rng.uniform(40, 110),                  # fall speed
                rng.uniform(0, math.tau),              # angle
                rng.uniform(-3, 3),                    # spin
                rng.uniform(7, 14),                    # length
                rng.choice(CONFETTI_COLORS),
                rng.uniform(0.6, 1.6),                 # sway freq
            ))
        play_sound(self.sound_name, self.settings)

    def _init_outcome(self) -> None:
        st = self.state
        winner = st.winner
        if winner == DRAW:
            self.kind = "draw"
            self.headline = "DRAW!"
            self.title = "Match Drawn"
            self.detail = "Both players reached 5 lines on the same call."
            self.sound_name = "draw"
        elif st.mode == GameMode.HUMAN_VS_AI:
            if winner == 0:
                self.kind, self.headline, self.title = "win", "BINGO!", "You Win!"
                self.detail = "You completed all 5 lines!"
                self.sound_name = "win"
            else:
                self.kind, self.headline, self.title = "lose", "So Close!", "AI Wins"
                self.detail = f"The {DIFF.get(st.agents[1], 'AI')} AI completed B-I-N-G-O first."
                self.sound_name = "lose"
        elif st.mode == GameMode.HUMAN_VS_HUMAN:
            self.kind, self.headline = "win", "BINGO!"
            self.title = f"Player {winner + 1} Wins!"
            self.detail = f"Player {winner + 1} completed all 5 lines!"
            self.sound_name = "win"
        else:
            self.kind, self.headline = "win", "BINGO!"
            self.title = f"AI {winner + 1} ({DIFF.get(st.agents[winner], '')}) Wins!"
            self.detail = "Five lines completed first."
            self.sound_name = "win"

    # ------------------------------------------------------------------ #
    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.on_play_again()
                return
            if event.key == pygame.K_ESCAPE:
                self.on_back_menu()
                return
        self.btn_play_again.handle_event(event, mouse_pos, self.settings)
        self.btn_menu.handle_event(event, mouse_pos, self.settings)

    def draw(self, surface: pygame.Surface) -> None:
        key = ("results", self.kind, self.title, self.detail, self.state.lines_a, self.state.lines_b,
               len(self.state.move_history))
        surface.blit(static_layer(key, self._paint_static), (0, 0))
        age = time.time() - self.created
        intro = ease_out_cubic(age / 0.5)
        if self.kind == "win":
            self._draw_confetti(surface, age)
            cy = 100 - 20 * (1 - intro)
            for rr, a in ((78, 14), (64, 22), (50, 30)):
                draw_circle(surface, (640, cy + 4), rr, (255, 200, 60, a))
            draw_icon(surface, "crown", (640, cy + 4), 96, (150, 90, 0))
            draw_icon(surface, "crown", (640, cy), 96, COLORS["gold"])
        self.btn_play_again.draw(surface)
        self.btn_menu.draw(surface)

    def _paint_static(self, surface: pygame.Surface) -> None:
        tint = {"win": (255, 210, 90), "lose": (255, 110, 120), "draw": (140, 190, 255)}[self.kind]
        surface.blit(cached_layer(("rays", self.kind), lambda: _build_rays(tint)), (0, 0))

        head_grad = {"win": ((255, 236, 100), (255, 150, 20)),
                     "lose": ((255, 150, 160), (226, 46, 72)),
                     "draw": ((180, 220, 255), (70, 140, 240))}[self.kind]
        size = 112 if self.kind != "lose" else 96
        draw_text(surface, self.headline, size, (4, 10, 24), (640, 212 + 8), weight="black",
                  outline=((4, 10, 24), 7))
        draw_text(surface, self.headline, size, (255, 255, 255), (640, 212), weight="black",
                  outline=((10, 26, 56), 7), gradient=head_grad)

        draw_text(surface, self.title, 46, COLORS["text_white"], (640, 312), weight="black",
                  outline=((10, 26, 56), 3), max_width=1100)
        draw_text(surface, self.detail, 21, COLORS["text_light"], (640, 362), weight="semibold")

        st = self.state
        if self.kind == "win":
            count, col = 5, COLORS["success"]
        elif self.kind == "lose":
            count, col = min(5, st.lines_a), COLORS["ai_red"]
        else:
            count, col = 5, COLORS["human_blue"]
        LetterBadge.draw_letter_bar(surface, 640, 440, count, col, radius=34, spacing=84)

        # summary chips
        if st.mode == GameMode.HUMAN_VS_AI:
            n0, n1 = "You", "AI"
        elif st.mode == GameMode.HUMAN_VS_HUMAN:
            n0, n1 = "Player 1", "Player 2"
        else:
            n0, n1 = "AI 1", "AI 2"
        chips = [(f"{n0}  {st.lines_a} lines", COLORS["human_blue_light"]),
                 (f"{n1}  {st.lines_b} lines", COLORS["ai_red_light"]),
                 (f"{len(st.move_history)} calls", COLORS["gold_glow"])]
        widths = [text_width(c[0], 16, "semibold") + 52 for c in chips]
        x = 640 - (sum(widths) + 16 * (len(chips) - 1)) / 2
        for (label, color), w in zip(chips, widths):
            r = pygame.Rect(int(x), 506, int(w), 40)
            draw_rounded_rect(surface, r, (12, 30, 60), 20, COLORS["border_light"], 1.2)
            draw_circle(surface, (r.x + 20, r.centery), 5, color)
            draw_text(surface, label, 16, COLORS["text_white"], (r.x + 34, r.centery), anchor="midleft",
                      weight="semibold")
            x += w + 16

        draw_text(surface, "Enter: play again   •   Esc: menu", 12, COLORS["text_dim"], (640, 690),
                  weight="semibold")

    def _draw_confetti(self, surface: pygame.Surface, t: float) -> None:
        for x, phase, speed, ang, spin, ln, col, sway in self.confetti:
            y = (phase + speed * t) % 780 - 40
            xx = x + 14 * math.sin(t * sway + phase)
            a = ang + spin * t
            dx, dy = math.cos(a) * ln / 2, math.sin(a) * ln / 2
            px, py = -math.sin(a) * 2.6, math.cos(a) * 2.6
            pts = [SP((xx - dx - px, y - dy - py)), SP((xx + dx - px, y + dy - py)),
                   SP((xx + dx + px, y + dy + py)), SP((xx - dx + px, y - dy + py))]
            pygame.draw.polygon(surface, col, pts)
