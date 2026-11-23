from __future__ import annotations

import time
from typing import Tuple, Optional, Callable, List, Sequence, Any

import pygame

from ui.theme import (
    COLORS,
    S,
    SR,
    draw_text,
    draw_rounded_rect,
    draw_shadow,
    draw_circle,
    draw_icon,
    text_width,
    play_sound,
    virtual_mouse,
)
from data.settings_manager import SettingsManager

Color = Tuple[int, ...]

# Variant -> (top, bottom, hover_top, hover_bottom, lip, border, text)
_VARIANTS = {
    "green": (COLORS["green_top"], COLORS["green_bottom"], (74, 226, 126), (30, 182, 88),
              COLORS["green_lip"], COLORS["green_border"], COLORS["text_white"]),
    "navy": (COLORS["navy_top"], COLORS["navy_bottom"], COLORS["navy_hover_top"],
             COLORS["navy_hover_bottom"], COLORS["navy_lip"], COLORS["navy_border"], COLORS["text_white"]),
    "danger": (COLORS["red_top"], COLORS["red_bottom"], (250, 98, 116), (220, 52, 80),
               COLORS["red_lip"], (255, 140, 154), COLORS["text_white"]),
    "blue": (COLORS["human_header_top"], COLORS["human_header_bottom"], (72, 150, 255), (40, 108, 222),
             (14, 56, 140), (120, 180, 255), COLORS["text_white"]),
}


class Button:
    """Concept-sheet style button: gradient face, 3D lip, hover lift, press sink."""

    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        text: str = "",
        icon: Optional[str] = None,
        variant: str = "navy",  # "green", "navy", "danger", "blue", "ghost"
        font_size: int = 20,
        radius: int = 14,
        on_click: Optional[Callable[[], None]] = None,
        sound_name: str = "click",
        align: str = "center",  # or "left" (menu style: icon column + label)
        lip: int = 4,
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.icon = icon
        self.variant = variant
        self.font_size = font_size
        self.radius = radius
        self.on_click = on_click
        self.sound_name = sound_name
        self.align = align
        self.lip = lip

        self.is_hovered = False
        self.is_pressed = False
        self.enabled = True
        self.visible = True

    # ------------------------------------------------------------------ #
    def handle_event(
        self,
        event: pygame.event.Event,
        mouse_pos: Tuple[int, int],
        settings: Optional[SettingsManager] = None,
    ) -> bool:
        """Processes mouse events (design-space mouse) and returns True if clicked."""
        if not self.enabled or not self.visible:
            self.is_hovered = False
            self.is_pressed = False
            return False

        self.is_hovered = self.rect.collidepoint(mouse_pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.is_pressed
            self.is_pressed = False
            if was_pressed and self.is_hovered:
                if self.sound_name:
                    play_sound(self.sound_name, settings)
                if self.on_click:
                    self.on_click()
                return True
        return False

    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        hovered = self.enabled and self.rect.collidepoint(virtual_mouse())
        pressed = hovered and self.is_pressed and pygame.mouse.get_pressed()[0]
        r = self.rect

        if self.variant == "ghost":
            border = COLORS["border_focus"] if hovered else COLORS["border_light"]
            fill = (255, 255, 255, 18) if hovered else (255, 255, 255, 0)
            draw_rounded_rect(surface, r, fill, self.radius, border, 1.5)
            self._draw_label(surface, r, COLORS["text_white"] if hovered else COLORS["text_light"])
            return

        top, bottom, htop, hbottom, lip_col, border, text_col = _VARIANTS.get(self.variant, _VARIANTS["navy"])
        if not self.enabled:
            top, bottom, lip_col = (36, 52, 80), (28, 42, 68), (14, 24, 42)
            border, text_col = (52, 72, 104), COLORS["text_dim"]
        elif hovered:
            top, bottom = htop, hbottom

        lip = self.lip if self.enabled else 2
        sink = lip if pressed else (0 if not hovered else -1)
        face = r.move(0, sink if sink > 0 else 0)
        if sink < 0:
            face = r.move(0, -1)

        if self.enabled:
            draw_shadow(surface, r.move(0, lip), radius=self.radius, offset=(0, 4), blur=10, alpha=110)
        # 3D lip
        if not pressed:
            draw_rounded_rect(surface, r.move(0, lip), lip_col, self.radius)
        draw_rounded_rect(surface, face, None, self.radius, border, 1.2, gradient=(top, bottom))
        # top gloss
        if self.enabled:
            gloss = pygame.Rect(face.x + 6, face.y + 2, face.w - 12, max(4, face.h // 3))
            draw_rounded_rect(surface, gloss, None, min(self.radius, gloss.h // 2),
                              gradient=((255, 255, 255, 46), (255, 255, 255, 0)))
        self._draw_label(surface, face, text_col)

    def _draw_label(self, surface: pygame.Surface, r: pygame.Rect, color: Color) -> None:
        fs = self.font_size
        icon_size = fs * 1.15
        if self.align == "left":
            x = r.x + 26
            if self.icon:
                draw_icon(surface, self.icon, (x + icon_size / 2, r.centery), icon_size, color)
                x += icon_size + 16
            if self.text:
                draw_text(surface, self.text, fs, color, (x, r.centery), anchor="midleft",
                          max_width=r.right - x - 12)
            return

        gap = 10 if (self.icon and self.text) else 0
        tw = text_width(self.text, fs) if self.text else 0
        total = (icon_size if self.icon else 0) + gap + tw
        x = r.centerx - total / 2
        if self.icon:
            draw_icon(surface, self.icon, (x + icon_size / 2, r.centery), icon_size, color)
            x += icon_size + gap
        if self.text:
            draw_text(surface, self.text, fs, color, (x, r.centery), anchor="midleft",
                      max_width=r.w - 16)


class IconButton(Button):
    """Circular icon-only button (back, settings, close...)."""

    def __init__(self, center: Tuple[int, int], radius: int = 24, icon: str = "back",
                 on_click: Optional[Callable[[], None]] = None, variant: str = "navy",
                 icon_size: Optional[float] = None, sound_name: str = "click"):
        super().__init__((center[0] - radius, center[1] - radius, radius * 2, radius * 2),
                         icon=icon, variant=variant, radius=radius, on_click=on_click,
                         sound_name=sound_name, lip=0)
        self.icon_size = icon_size or radius * 0.95

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        hovered = self.enabled and self.rect.collidepoint(virtual_mouse())
        c = self.rect.center
        rad = self.rect.w / 2
        if self.variant == "plain":
            if hovered:
                draw_circle(surface, c, rad, (255, 255, 255, 26))
            draw_icon(surface, self.icon, c, self.icon_size,
                      COLORS["text_white"] if hovered else COLORS["text_light"])
            return
        top, bottom, htop, hbottom, _lip, border, text_col = _VARIANTS.get(self.variant, _VARIANTS["navy"])
        if hovered:
            top, bottom = htop, hbottom
            border = COLORS["border_focus"]
        draw_shadow(surface, self.rect, radius=rad, offset=(0, 3), blur=8, alpha=100)
        draw_circle(surface, c, rad, None, border, 1.5, gradient=(top, bottom))
        draw_icon(surface, self.icon, c, self.icon_size, text_col)


# --------------------------------------------------------------------------- #
# Composite drawing helpers
# --------------------------------------------------------------------------- #
def draw_panel(
    surface: pygame.Surface,
    rect: Any,
    radius: float = 18,
    fill: Color = COLORS["bg_card"],
    border: Optional[Color] = COLORS["border_light"],
    border_width: float = 1.2,
    shadow: bool = True,
    gradient: Optional[Tuple[Color, Color]] = None,
) -> None:
    """Elevated card with soft shadow."""
    if shadow:
        draw_shadow(surface, rect, radius=radius, offset=(0, 8), blur=18, alpha=130)
    draw_rounded_rect(surface, rect, None if gradient else fill, radius, border, border_width,
                      gradient=gradient)


def draw_avatar(surface: pygame.Surface, center: Sequence[float], radius: float,
                kind: str, color: Color, ring: Optional[Color] = None) -> None:
    """Circular avatar (user / robot / users) with optional highlight ring."""
    if ring is not None:
        draw_circle(surface, center, radius + 3, ring)
    hi = tuple(min(255, int(c * 1.18) + 18) for c in color[:3])
    draw_circle(surface, center, radius, None, (255, 255, 255, 60), 1.2, gradient=(hi, color))
    draw_icon(surface, kind, center, radius * 1.15, COLORS["text_white"])


class LetterBadge:
    """Renders B-I-N-G-O progress letters with active/inactive state."""

    LETTERS = ("B", "I", "N", "G", "O")

    @staticmethod
    def draw_letter_bar(
        surface: pygame.Surface,
        center_x: float,
        center_y: float,
        completed_count: int,
        active_color: Color = COLORS["human_blue"],
        radius: float = 16,
        spacing: float = 38,
        anchor: str = "center",  # or "left": center_x is the left edge
        pulse_index: Optional[int] = None,
    ) -> None:
        n = len(LetterBadge.LETTERS)
        if anchor == "left":
            start_x = center_x + radius
        else:
            start_x = center_x - (n - 1) * spacing / 2
        hi = tuple(min(255, int(c * 1.15) + 24) for c in active_color[:3])
        for i, letter in enumerate(LetterBadge.LETTERS):
            cx = start_x + i * spacing
            if i < completed_count:
                rr = radius
                if pulse_index is not None and i == pulse_index:
                    rr = radius * (1.0 + 0.12 * abs(((time.time() * 3) % 2) - 1))
                draw_circle(surface, (cx, center_y), rr, None, (255, 255, 255, 110), 1.6,
                            gradient=(hi, active_color))
                draw_text(surface, letter, radius * 1.1, COLORS["text_white"], (cx, center_y),
                          weight="black")
            else:
                draw_circle(surface, (cx, center_y), radius, COLORS["letter_inactive"],
                            COLORS["border_light"], 1.2)
                draw_text(surface, letter, radius * 1.1, COLORS["letter_inactive_text"],
                          (cx, center_y), weight="black")


class ToggleSwitch:
    """iOS-style on/off switch."""

    def __init__(self, rect: Tuple[int, int, int, int], value: bool,
                 on_change: Callable[[bool], None]):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.on_change = on_change
        self._anim = 1.0 if value else 0.0
        self._last = time.time()

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int],
                     settings: Optional[SettingsManager] = None) -> bool:
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.rect.collidepoint(mouse_pos):
            self.value = not self.value
            self.on_change(self.value)
            play_sound("click", settings)
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        now = time.time()
        dt = min(0.05, now - self._last)
        self._last = now
        target = 1.0 if self.value else 0.0
        self._anim += (target - self._anim) * min(1.0, dt * 14)
        r = self.rect
        on_col = COLORS["green_bottom"]
        off_col = (40, 60, 92)
        t = self._anim
        col = tuple(int(off_col[i] + (on_col[i] - off_col[i]) * t) for i in range(3))
        # quantise colour to keep shape cache small
        col = tuple((c // 8) * 8 for c in col)
        draw_rounded_rect(surface, r, col, r.h / 2, COLORS["border_light"], 1)
        knob_r = r.h / 2 - 4
        kx = r.x + r.h / 2 + (r.w - r.h) * t
        draw_shadow(surface, (kx - knob_r, r.centery - knob_r, knob_r * 2, knob_r * 2),
                    radius=knob_r, offset=(0, 2), blur=4, alpha=90)
        draw_circle(surface, (kx, r.centery), knob_r, (255, 255, 255))


class Slider:
    """Horizontal 0..1 slider with draggable knob."""

    def __init__(self, rect: Tuple[int, int, int, int], value: float,
                 on_change: Callable[[float], None], step: float = 0.05):
        self.rect = pygame.Rect(rect)
        self.value = max(0.0, min(1.0, value))
        self.on_change = on_change
        self.step = step
        self.dragging = False

    def _set_from_x(self, x: float) -> None:
        t = (x - self.rect.x) / max(1, self.rect.w)
        t = round(max(0.0, min(1.0, t)) / self.step) * self.step
        if abs(t - self.value) > 1e-6:
            self.value = t
            self.on_change(t)

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int],
                     settings: Optional[SettingsManager] = None) -> bool:
        hit = self.rect.inflate(0, 24)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and hit.collidepoint(mouse_pos):
            self.dragging = True
            self._set_from_x(mouse_pos[0])
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(mouse_pos[0])
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            play_sound("click", settings)
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        r = self.rect
        track = pygame.Rect(r.x, r.centery - 4, r.w, 8)
        draw_rounded_rect(surface, track, COLORS["bg_card_inner"], 4, COLORS["border_light"], 1)
        fill_w = max(8, int(r.w * self.value))
        draw_rounded_rect(surface, (r.x, r.centery - 4, fill_w, 8), None, 4,
                          gradient=(COLORS["green_top"], COLORS["green_bottom"]))
        kx = r.x + r.w * self.value
        hovered = r.inflate(0, 24).collidepoint(virtual_mouse()) or self.dragging
        kr = 12 if hovered else 11
        draw_shadow(surface, (kx - kr, r.centery - kr, kr * 2, kr * 2), radius=kr, offset=(0, 2), blur=5, alpha=110)
        draw_circle(surface, (kx, r.centery), kr, (255, 255, 255), COLORS["green_bottom"], 2)


class SegmentedControl:
    """Row of mutually-exclusive pills (difficulty, pace, ...)."""

    def __init__(self, rect: Tuple[int, int, int, int], options: List[Tuple[str, Any]],
                 value: Any, on_change: Callable[[Any], None], font_size: int = 17,
                 gap: int = 14, captions: Optional[List[str]] = None,
                 selected_variant: str = "green"):
        self.rect = pygame.Rect(rect)
        self.options = options
        self.value = value
        self.on_change = on_change
        self.font_size = font_size
        self.gap = gap
        self.captions = captions
        self.selected_variant = selected_variant
        n = len(options)
        w = (self.rect.w - gap * (n - 1)) / n
        self.buttons: List[Button] = []
        for i, (label, val) in enumerate(options):
            b = Button((int(self.rect.x + i * (w + gap)), self.rect.y, int(w), self.rect.h),
                       text=label, variant="navy", font_size=font_size, radius=12,
                       on_click=(lambda v=val: self._select(v)), lip=3)
            self.buttons.append(b)

    def _select(self, v: Any) -> None:
        if v != self.value:
            self.value = v
            self.on_change(v)

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int],
                     settings: Optional[SettingsManager] = None) -> None:
        for b in self.buttons:
            b.handle_event(event, mouse_pos, settings)

    def draw(self, surface: pygame.Surface) -> None:
        for i, b in enumerate(self.buttons):
            selected = self.options[i][1] == self.value
            b.variant = self.selected_variant if selected else "navy"
            b.draw(surface)
            if self.captions:
                draw_text(surface, self.captions[i], 12,
                          COLORS["text_light"] if selected else COLORS["text_dim"],
                          (b.rect.centerx, b.rect.bottom + 18), weight="semibold")


class BoardCellTile:
    """Kept for API compatibility: a single standalone board tile."""

    def __init__(self, rect: Tuple[int, int, int, int], number: int, is_called: bool = False,
                 is_player_board: bool = True, theme_color: Color = COLORS["mark_blue"]):
        self.rect = pygame.Rect(rect)
        self.number = number
        self.is_called = is_called
        self.is_player_board = is_player_board
        self.theme_color = theme_color
        self.is_hovered = False

    def handle_mouse(self, mouse_pos: Tuple[int, int], can_click: bool) -> bool:
        self.is_hovered = can_click and (not self.is_called) and self.rect.collidepoint(mouse_pos)
        return self.is_hovered

    def draw(self, surface: pygame.Surface) -> None:
        draw_board_tile(surface, self.rect, self.number, self.is_called,
                        hovered=self.is_hovered, mark_color=self.theme_color)


def draw_board_tile(
    surface: pygame.Surface,
    rect: Any,
    number: int,
    called: bool,
    hovered: bool = False,
    selected: bool = False,
    latest: bool = False,
    mark_color: Color = COLORS["mark_blue"],
    clickable: bool = False,
    on_line: bool = False,
    stage: str = "all",
) -> None:
    """
    Single BINGO board tile in all its states.
    ``stage`` = "bg" (tile only), "fg" (marker + number only) or "all" -
    two-pass rendering lets line strokes sit between tile and number.
    """
    r = pygame.Rect(rect)
    if stage in ("all", "bg"):
        _draw_tile_bg(surface, r, hovered, selected, on_line)
    if stage in ("all", "fg"):
        _draw_tile_fg(surface, r, number, called, selected, latest, mark_color, clickable)


def _draw_tile_bg(surface: pygame.Surface, r: pygame.Rect, hovered: bool, selected: bool,
                  on_line: bool) -> None:
    if selected:
        bg, border, bw = COLORS["tile_selected"], COLORS["gold_dark"], 2.5
    elif hovered:
        bg, border, bw = COLORS["tile_hover"], COLORS["human_blue"], 2
    elif on_line:
        bg, border, bw = (232, 250, 238), (150, 220, 176), 1
    else:
        bg, border, bw = COLORS["tile_bg"], None, 0
    draw_rounded_rect(surface, r, bg, 8, border, bw)


def _draw_tile_fg(surface: pygame.Surface, r: pygame.Rect, number: int, called: bool, selected: bool,
                  latest: bool, mark_color: Color, clickable: bool) -> None:
    fs = r.h * 0.36
    if called:
        cr = min(r.w, r.h) * 0.36
        if latest:
            draw_circle(surface, r.center, cr + 4, COLORS["gold"])
        hi = tuple(min(255, int(c * 1.12) + 26) for c in mark_color[:3])
        draw_circle(surface, r.center, cr, None, (255, 255, 255, 120), 1.2, gradient=(hi, mark_color))
        draw_text(surface, str(number), fs, COLORS["text_white"], r.center, weight="bold")
    else:
        col = COLORS["text_dark"] if (clickable or selected) else (52, 66, 92)
        draw_text(surface, str(number), fs, col, r.center, weight="bold")
