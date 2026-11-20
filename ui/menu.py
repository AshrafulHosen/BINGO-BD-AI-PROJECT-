"""
BINGO-BD Screen 1: Main Menu & Title Screen
Procedurally painted school-courtyard backdrop (cached per resolution), outlined
gradient logo with Bangladesh-flag "O", ribbon subtitle and menu buttons -
matching panel 1 of the UI concept sheet.
"""

from __future__ import annotations

import math
import random
from typing import Tuple, Callable

import pygame

from ui.theme import (
    COLORS,
    VIRTUAL_WIDTH,
    VIRTUAL_HEIGHT,
    S,
    SR,
    draw_text,
    draw_rounded_rect,
    draw_circle,
    draw_shadow,
    draw_gradient_vertical,
    draw_icon,
    render_text,
    text_width,
    cached_layer,
    static_layer,
    _vertical_gradient,
)
from ui.widgets import Button, IconButton
from data.settings_manager import SettingsManager

LOGO_FILL = ((255, 232, 92), (255, 160, 20))
LOGO_OUTLINE = (10, 26, 56)


def draw_logo(surface: pygame.Surface, center: Tuple[float, float], size: float = 104) -> None:
    """'BINGO-BD' logo: gradient letters, heavy outline, flag-disc replacing the O."""
    outline = (LOGO_OUTLINE, size * 0.06)
    left, right = "BING", "-BD"
    w_left = text_width(left, size, "black")
    w_right = text_width(right, size, "black")
    disc_r = size * 0.36
    gap = size * 0.03
    total = w_left + gap + disc_r * 2 + gap + w_right
    x = center[0] - total / 2
    cy = center[1]

    # drop shadow
    for txt, xx in ((left, x), (right, x + w_left + gap * 2 + disc_r * 2)):
        draw_text(surface, txt, size, (4, 10, 24), (xx, cy + size * 0.07), anchor="midleft",
                  weight="black", outline=outline)
        draw_text(surface, txt, size, (255, 255, 255), (xx, cy), anchor="midleft",
                  weight="black", outline=outline, gradient=LOGO_FILL)

    # Bangladesh flag disc as the "O"
    ocx = x + w_left + gap + disc_r
    ocy = cy + size * 0.04
    draw_circle(surface, (ocx, ocy + size * 0.06), disc_r + size * 0.06, (4, 10, 24))
    draw_circle(surface, (ocx, ocy), disc_r + size * 0.06, LOGO_OUTLINE)
    draw_circle(surface, (ocx, ocy), disc_r, None, gradient=((20, 170, 90), (0, 106, 78)))
    draw_circle(surface, (ocx - disc_r * 0.08, ocy), disc_r * 0.5, None,
                gradient=((255, 70, 70), (214, 20, 40)))
    draw_circle(surface, (ocx - disc_r * 0.32, ocy - disc_r * 0.42), disc_r * 0.16, (255, 255, 255, 90))


def _paint_tree(s: pygame.Surface, x: float, base_y: float, scale: float, dark: bool = False) -> None:
    trunk = (92, 60, 38) if not dark else (70, 46, 30)
    pygame.draw.rect(s, trunk, SR((x - 7 * scale, base_y - 70 * scale, 14 * scale, 72 * scale)))
    greens = [(46, 110, 48), (62, 138, 58), (82, 160, 70)] if not dark else \
        [(34, 86, 44), (44, 104, 52), (56, 120, 60)]
    rng = random.Random(int(x * 7 + base_y))
    for i, g in enumerate(greens):
        for _ in range(5):
            ox = rng.uniform(-48, 48) * scale
            oy = rng.uniform(-150, -70) * scale + i * 10 * scale
            r = rng.uniform(26, 40) * scale * (1 - i * 0.15)
            draw_circle(s, (x + ox, base_y + oy), r, g)


def _paint_scene() -> pygame.Surface:
    W, H = S(VIRTUAL_WIDTH), S(VIRTUAL_HEIGHT)
    s = _vertical_gradient((W, H), (96, 160, 226), (246, 214, 160)).convert_alpha()

    # sun glow + clouds
    for i in range(10, 0, -1):
        draw_circle(s, (1010, 120), 30 + i * 14, (255, 236, 180, 12))
    draw_circle(s, (1010, 120), 34, (255, 246, 214))
    rng = random.Random(4)
    for cx, cy, k in ((240, 90, 1.0), (560, 60, 0.8), (820, 130, 0.9), (1180, 70, 0.7)):
        for _ in range(6):
            draw_circle(s, (cx + rng.uniform(-60, 60) * k, cy + rng.uniform(-12, 12) * k),
                        rng.uniform(22, 38) * k, (255, 255, 255, 190))

    # far tree line
    for x in range(-20, VIRTUAL_WIDTH + 40, 46):
        draw_circle(s, (x, 330 + (x % 3) * 6), 44, (58, 116, 70))
        draw_circle(s, (x + 20, 316 + (x % 5) * 4), 36, (70, 132, 78))

    # school building
    bx0, bx1, by0, by1 = 150, 1130, 238, 476
    draw_rounded_rect(s, (bx0 - 10, by0 - 18, bx1 - bx0 + 20, 24), (236, 226, 204), 4)
    draw_gradient_vertical(s, (bx0, by0, bx1 - bx0, by1 - by0), (190, 92, 66), (160, 72, 52))
    for fy in (by0 + 78, by0 + 156):
        pygame.draw.rect(s, (232, 220, 196), SR((bx0, fy, bx1 - bx0, 8)))
    win_w, win_h = 34, 44
    for floor in range(3):
        fy = by0 + 18 + floor * 78
        x = bx0 + 26
        while x + win_w < bx1 - 20:
            if not (560 < x < 700):
                draw_rounded_rect(s, (x - 3, fy - 3, win_w + 6, win_h + 6), (240, 230, 206), 3)
                draw_gradient_vertical(s, (x, fy, win_w, win_h), (96, 134, 170), (54, 86, 122))
                pygame.draw.rect(s, (226, 216, 190), SR((x + win_w / 2 - 1, fy, 2, win_h)))
            x += 52
    # entrance block
    draw_rounded_rect(s, (560, by0 - 46, 160, by1 - by0 + 46), (206, 106, 76), 6)
    draw_rounded_rect(s, (546, by0 - 56, 188, 20), (240, 232, 214), 4)
    draw_rounded_rect(s, (580, by0 - 24, 120, 26), (250, 244, 228), 4)
    draw_text(s, "BD HIGH SCHOOL", 12, (120, 52, 36), (640, by0 - 11), weight="black")
    draw_rounded_rect(s, (598, by1 - 104, 84, 104), (88, 52, 36), 6)
    draw_rounded_rect(s, (606, by1 - 96, 32, 96), (120, 74, 48), 3)
    draw_rounded_rect(s, (642, by1 - 96, 32, 96), (120, 74, 48), 3)

    # flag pole + Bangladesh flag
    pygame.draw.rect(s, (220, 224, 230), SR((112, 170, 5, 310)))
    draw_rounded_rect(s, (117, 172, 78, 48), (0, 106, 78), 2)
    draw_circle(s, (151, 196), 15, (244, 42, 65))

    # ground
    draw_gradient_vertical(s, (0, 470, VIRTUAL_WIDTH, 250), (204, 178, 128), (170, 140, 92))
    draw_gradient_vertical(s, (0, 466, VIRTUAL_WIDTH, 22), (98, 160, 72), (74, 136, 56))

    # foreground trees
    _paint_tree(s, 70, 560, 1.5, dark=True)
    _paint_tree(s, 1210, 560, 1.6, dark=True)
    _paint_tree(s, 250, 500, 0.9)
    _paint_tree(s, 1040, 500, 0.95)

    # readability overlays: bottom fade + central dim behind the menu
    fade = _vertical_gradient((W, H), (8, 20, 40, 40), (8, 20, 40, 225))
    s.blit(fade, (0, 0))
    center_dim = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(14, 0, -1):
        rw, rh = S(260 + i * 26), S(220 + i * 20)
        pygame.draw.ellipse(center_dim, (6, 16, 34, 9), (S(640) - rw // 2, S(410) - rh // 2, rw, rh))
    s.blit(center_dim, (0, 0))

    _paint_props(s)
    opaque = pygame.Surface((W, H))
    opaque.blit(s, (0, 0))
    return opaque


def _paint_props(s: pygame.Surface) -> None:
    """Books, school bag and chalkboard (bottom corners) - concept sheet props."""
    # school bag
    draw_shadow(s, (40, 560, 110, 130), radius=26, offset=(0, 8), blur=12, alpha=140)
    draw_rounded_rect(s, (40, 560, 110, 130), None, 26, (120, 20, 30), 2,
                      gradient=((214, 52, 60), (160, 28, 40)))
    draw_rounded_rect(s, (56, 610, 78, 52), None, 14, (120, 20, 30), 2,
                      gradient=((196, 40, 52), (150, 24, 36)))
    pygame.draw.arc(s, (90, 14, 22), SR((62, 532, 66, 60)), 0, math.pi, max(2, S(7)))
    # books
    books = [((30, 98, 182), 160, 22), ((22, 150, 96), 140, 20), ((222, 130, 40), 120, 18)]
    y = 696
    for col, w, h in books:
        y -= h
        draw_rounded_rect(s, (150, y, w, h), col, 4)
        draw_rounded_rect(s, (150 + w - 18, y + 3, 14, h - 6), (244, 240, 230), 2)
    # chalkboard
    bx, by, bw, bh = 1000, 556, 250, 150
    draw_shadow(s, (bx, by, bw, bh), radius=10, offset=(0, 8), blur=12, alpha=150)
    draw_rounded_rect(s, (bx, by, bw, bh), None, 10, (96, 58, 30), 2,
                      gradient=((176, 116, 64), (132, 84, 44)))
    draw_rounded_rect(s, (bx + 12, by + 12, bw - 24, bh - 24), None, 6,
                      gradient=((44, 70, 58), (30, 50, 42)))
    draw_text(s, "B-I-N-G-O", 30, COLORS["chalk_white"], (bx + bw / 2, by + 58), weight="semibold")
    draw_circle(s, (bx + bw / 2 + 70, by + 104), 13, None, COLORS["chalk_white"], 2)
    draw_circle(s, (bx + bw / 2 + 65, by + 100), 1.8, COLORS["chalk_white"])
    draw_circle(s, (bx + bw / 2 + 75, by + 100), 1.8, COLORS["chalk_white"])
    pygame.draw.arc(s, COLORS["chalk_white"], SR((bx + bw / 2 + 63, by + 100, 14, 10)),
                    math.pi, 2 * math.pi, max(1, S(2)))
    draw_text(s, "5 lines = win!", 14, COLORS["chalk_green"], (bx + 40, by + 106),
              anchor="midleft", weight="semibold")


class MainMenuScreen:
    """Master title screen with procedural school environment and responsive menu."""

    def __init__(
        self,
        on_play: Callable[[], None],
        on_settings: Callable[[], None],
        on_stats: Callable[[], None],
        on_exit: Callable[[], None],
        settings: SettingsManager,
    ):
        self.on_play = on_play
        self.on_settings = on_settings
        self.on_stats = on_stats
        self.on_exit = on_exit
        self.settings = settings

        cx = VIRTUAL_WIDTH // 2
        self.btn_play = Button((cx - 180, 334, 360, 66), text="Play Game", icon="play",
                               variant="green", font_size=26, radius=18, on_click=self.on_play,
                               align="left", lip=5)
        self.btn_settings = Button((cx - 165, 422, 330, 54), text="Settings", icon="settings",
                                   variant="navy", font_size=20, radius=16,
                                   on_click=self.on_settings, align="left")
        self.btn_stats = Button((cx - 165, 488, 330, 54), text="Statistics", icon="statistics",
                                variant="navy", font_size=20, radius=16,
                                on_click=self.on_stats, align="left")
        self.btn_exit = Button((cx - 165, 554, 330, 54), text="Exit", icon="exit",
                               variant="navy", font_size=20, radius=16,
                               on_click=self.on_exit, align="left")
        self.btn_quick_settings = IconButton((44, 44), radius=24, icon="gear",
                                             on_click=self.on_settings, variant="plain",
                                             icon_size=30)

        self.buttons = [self.btn_play, self.btn_settings, self.btn_stats, self.btn_exit,
                        self.btn_quick_settings]

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.on_play()
            return
        for btn in self.buttons:
            btn.handle_event(event, mouse_pos, self.settings)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(static_layer("menu", self._paint_static), (0, 0))
        for btn in self.buttons:
            btn.draw(surface)

    def _paint_static(self, surface: pygame.Surface) -> None:
        surface.blit(_paint_scene(), (0, 0))
        cx = VIRTUAL_WIDTH // 2
        draw_logo(surface, (cx, 142), 108)

        # ribbon subtitle
        rib = pygame.Rect(cx - 270, 212, 540, 46)
        draw_shadow(surface, rib, radius=12, offset=(0, 5), blur=10, alpha=140)
        for side in (-1, 1):
            tail_x = rib.left - 24 if side < 0 else rib.right - 6
            draw_rounded_rect(surface, (tail_x, rib.y + 10, 30, rib.h - 4), (16, 56, 128), 4)
        draw_rounded_rect(surface, rib, None, 12, (110, 170, 250), 1.5,
                          gradient=((44, 120, 230), (24, 82, 186)))
        draw_text(surface, "Traditional Bangladeshi School Bingo", 22, COLORS["text_white"],
                  rib.center, weight="bold", shadow=((8, 30, 80), 1.5))

        draw_text(surface, "Call  •  Mark  •  Complete  •  Win", 24, COLORS["text_white"],
                  (cx, 292), weight="semibold", outline=((10, 26, 56), 2.2))

        draw_text(surface, "v1.1  •  F11 full screen", 12, (170, 186, 214),
                  (cx, VIRTUAL_HEIGHT - 18), weight="semibold")
