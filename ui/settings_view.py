"""
BINGO-BD Settings Screen
Sound on/off, master volume, AI move pace and display mode.
All settings persist automatically (data/settings.json).
"""

from __future__ import annotations

from typing import Tuple, Callable, Optional

import pygame

from ui.theme import (
    COLORS,
    VIRTUAL_WIDTH,
    draw_text,
    draw_rounded_rect,
    draw_icon,
    draw_app_background,
    static_layer,
    play_sound,
)
from ui.widgets import IconButton, ToggleSwitch, Slider, SegmentedControl, draw_panel
from data.settings_manager import SettingsManager


class SettingsScreen:
    """Settings screen allowing user configuration of audio, pacing and display."""

    PANEL = pygame.Rect(310, 40, 660, 640)

    def __init__(
        self,
        on_back: Callable[[], None],
        settings: SettingsManager,
        on_toggle_fullscreen: Optional[Callable[[], None]] = None,
        is_fullscreen: Optional[Callable[[], bool]] = None,
    ):
        self.on_back = on_back
        self.settings = settings
        self.on_toggle_fullscreen = on_toggle_fullscreen
        self.is_fullscreen = is_fullscreen or (lambda: False)

        p = self.PANEL
        self.btn_back = IconButton((p.x + 44, p.y + 44), radius=22, icon="back", on_click=self.on_back)
        ctrl_x = p.right - 40
        self.rows_y = [p.y + 150, p.y + 250, p.y + 350, p.y + 450]

        self.toggle_sound = ToggleSwitch((ctrl_x - 76, self.rows_y[0] - 19, 76, 38),
                                         self.settings.sound_enabled, self._set_sound)
        self.slider_volume = Slider((ctrl_x - 230, self.rows_y[1] - 12, 230, 24),
                                    self.settings.sound_volume, self._set_volume)
        self.seg_speed = SegmentedControl((ctrl_x - 250, self.rows_y[2] - 22, 250, 44),
                                          [("Normal", "Normal"), ("Fast", "Fast")],
                                          self.settings.ai_speed, self._set_speed, font_size=16, gap=10)
        self.seg_display = SegmentedControl((ctrl_x - 250, self.rows_y[3] - 22, 250, 44),
                                            [("Window", False), ("Full screen", True)],
                                            self.is_fullscreen(), self._set_display, font_size=15, gap=10)

    # ------------------------------------------------------------------ #
    def _set_sound(self, on: bool) -> None:
        self.settings.sound_enabled = on

    def _set_volume(self, v: float) -> None:
        self.settings.sound_volume = v

    def _set_speed(self, v: str) -> None:
        self.settings.ai_speed = v

    def _set_display(self, full: bool) -> None:
        if self.on_toggle_fullscreen and full != self.is_fullscreen():
            self.on_toggle_fullscreen()

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        self.btn_back.handle_event(event, mouse_pos, self.settings)
        self.toggle_sound.handle_event(event, mouse_pos, self.settings)
        self.slider_volume.handle_event(event, mouse_pos, self.settings)
        self.seg_speed.handle_event(event, mouse_pos, self.settings)
        self.seg_display.handle_event(event, mouse_pos, self.settings)

    def _paint_static(self, surface: pygame.Surface) -> None:
        draw_app_background(surface)
        p = self.PANEL
        draw_panel(surface, p, radius=26, gradient=((18, 42, 80), (11, 28, 56)))
        draw_text(surface, "Settings", 34, COLORS["text_white"], (p.centerx, p.y + 46))
        draw_text(surface, "Saved automatically", 14, COLORS["text_muted"], (p.centerx, p.y + 80),
                  weight="semibold")
        for y in self.rows_y:
            draw_rounded_rect(surface, (p.x + 28, y - 42, p.w - 56, 84), (14, 34, 66), 16,
                              COLORS["border_light"], 1)
        draw_text(surface, "Changes to AI pace apply to the next match.", 13, COLORS["text_dim"],
                  (p.centerx, p.bottom - 40), weight="semibold")

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(static_layer("settings", self._paint_static), (0, 0))
        p = self.PANEL
        self.btn_back.draw(surface)

        # keep widgets in sync with external changes (e.g. in-game mute, F11)
        self.toggle_sound.value = self.settings.sound_enabled
        self.seg_display.value = self.is_fullscreen()

        rows = [
            ("sound_on" if self.settings.sound_enabled else "sound_off", "Sound Effects",
             "Button, call, line and result sounds"),
            ("sound_on", "Master Volume", f"{int(round(self.settings.sound_volume * 100))}%"),
            ("bolt", "AI Move Pace", "AI vs AI delay: Normal 0.8 s  •  Fast 0.2 s"),
            ("monitor", "Display", "F11 or Alt+Enter toggles full screen"),
        ]
        for (icon, title, desc), y in zip(rows, self.rows_y):
            row = pygame.Rect(p.x + 28, y - 42, p.w - 56, 84)
            draw_icon(surface, icon, (row.x + 36, y), 26, COLORS["human_blue_light"])
            draw_text(surface, title, 19, COLORS["text_white"], (row.x + 68, y - 11), anchor="midleft")
            draw_text(surface, desc, 13, COLORS["text_muted"], (row.x + 68, y + 14), anchor="midleft",
                      weight="regular")

        self.toggle_sound.draw(surface)
        self.slider_volume.draw(surface)
        self.seg_speed.draw(surface)
        self.seg_display.draw(surface)
