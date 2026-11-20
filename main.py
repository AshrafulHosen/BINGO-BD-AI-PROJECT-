"""
BINGO-BD: Traditional Bangladeshi School Bingo with Strategic AI Opponents
Main desktop application entry point.

Rendering pipeline
------------------
1. The process is made per-monitor DPI aware on Windows *before* SDL starts,
   so Windows never bitmap-stretches (blurs) the window on 125 % / 150 % /
   200 % display scaling.
2. The default window size is chosen from the desktop size and DPI factor
   (1280x720, 1600x900 or 1920x1080 design sizes x DPI), and the window is
   freely resizable / F11 full-screen.
3. Every frame, screens draw directly at the window's *physical* resolution
   (ui.theme.set_scale) into a letter-boxed 16:9 viewport.  There is no
   up-scaling step, so text and vector shapes are pixel-sharp at any size.
"""

from __future__ import annotations

import os
import sys

# --- High-DPI awareness: must happen before pygame/SDL creates a window ---- #
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
os.environ.setdefault("SDL_HINT_WINDOWS_DPI_SCALING", "0")

_SYSTEM_DPI_SCALE = 1.0
if sys.platform == "win32":
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
        try:
            _SYSTEM_DPI_SCALE = max(1.0, ctypes.windll.user32.GetDpiForSystem() / 96.0)
        except Exception:
            _SYSTEM_DPI_SCALE = 1.0
    except Exception:
        pass

# Run from any working directory (assets/data paths are project-relative)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pygame  # noqa: E402
from typing import Tuple, Optional  # noqa: E402

from core.state import GameMode, AgentType, GameState  # noqa: E402
from core.controller import GameController  # noqa: E402
from data.stats_manager import StatsManager  # noqa: E402
from data.settings_manager import SettingsManager  # noqa: E402
from ui import theme  # noqa: E402
from ui.theme import (  # noqa: E402
    COLORS,
    VIRTUAL_WIDTH,
    VIRTUAL_HEIGHT,
    init_audio,
    pre_init_audio,
)
from ui.menu import MainMenuScreen  # noqa: E402
from ui.modes import ModeSelectScreen  # noqa: E402
from ui.game import GameplayScreen  # noqa: E402
from ui.results import GameOverScreen  # noqa: E402
from ui.settings_view import SettingsScreen  # noqa: E402
from ui.stats_view import StatisticsScreen  # noqa: E402

MIN_WINDOW = (960, 540)


def _pick_default_window_size() -> Tuple[int, int]:
    """Largest 16:9 design size (x DPI) that fits comfortably on the desktop."""
    try:
        desk_w, desk_h = pygame.display.get_desktop_sizes()[0]
    except Exception:
        info = pygame.display.Info()
        desk_w, desk_h = info.current_w or 1280, info.current_h or 720
    usable_w, usable_h = desk_w * 0.9, desk_h * 0.86
    for base_w, base_h in ((1920, 1080), (1600, 900), (1280, 720)):
        w, h = int(base_w * _SYSTEM_DPI_SCALE), int(base_h * _SYSTEM_DPI_SCALE)
        if w <= usable_w and h <= usable_h:
            return w, h
    # fall back to 16:9 that fits the usable area
    scale = min(usable_w / VIRTUAL_WIDTH, usable_h / VIRTUAL_HEIGHT)
    return max(MIN_WINDOW[0], int(VIRTUAL_WIDTH * scale)), max(MIN_WINDOW[1], int(VIRTUAL_HEIGHT * scale))


def _make_window_icon() -> pygame.Surface:
    surf = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255, 196, 46), (32, 32), 30)
    pygame.draw.circle(surf, (16, 40, 78), (32, 32), 30, 4)
    font = pygame.font.Font(theme._resolve_font_path("black"), 40) if theme._resolve_font_path("black") \
        else pygame.font.Font(None, 52)
    t = font.render("B", True, (16, 40, 78))
    surf.blit(t, t.get_rect(center=(32, 34)))
    return surf


class BingoApp:
    """Master application controller managing scenes and window events."""

    def __init__(self):
        pre_init_audio()
        pygame.init()
        init_audio()

        pygame.display.set_caption("BINGO-BD — Traditional Bangladeshi School Bingo")
        try:
            pygame.display.set_icon(_make_window_icon())
        except Exception:
            pass

        self.windowed_size = _pick_default_window_size()
        self.fullscreen = False
        self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self._update_viewport()

        self.clock = pygame.time.Clock()
        self.is_running = True

        # Managers
        self.stats_mgr = StatsManager()
        self.settings_mgr = SettingsManager()

        # Scene state
        self.current_scene = "MENU"
        self.game_controller: Optional[GameController] = None
        self.game_screen: Optional[GameplayScreen] = None
        self.game_over_screen: Optional[GameOverScreen] = None

        self.menu_screen = MainMenuScreen(
            on_play=self.open_mode_selection,
            on_settings=self.open_settings,
            on_stats=self.open_statistics,
            on_exit=self.quit_app,
            settings=self.settings_mgr,
        )
        self.mode_screen = ModeSelectScreen(
            on_start_game=self.start_game,
            on_back=self.open_menu,
            settings=self.settings_mgr,
        )
        self.settings_screen = SettingsScreen(
            on_back=self.open_menu,
            settings=self.settings_mgr,
            on_toggle_fullscreen=self.toggle_fullscreen,
            is_fullscreen=lambda: self.fullscreen,
        )
        self.stats_screen = StatisticsScreen(
            on_back=self.open_menu,
            stats_mgr=self.stats_mgr,
            settings=self.settings_mgr,
        )

    # ------------------------------------------------------------------ #
    # Window / viewport
    # ------------------------------------------------------------------ #
    def _update_viewport(self) -> None:
        """Compute the letter-boxed 16:9 viewport at physical resolution."""
        self.window = pygame.display.get_surface()
        win_w, win_h = self.window.get_size()
        scale = min(win_w / VIRTUAL_WIDTH, win_h / VIRTUAL_HEIGHT)
        theme.set_scale(scale)
        vw = min(win_w, int(round(VIRTUAL_WIDTH * scale)))
        vh = min(win_h, int(round(VIRTUAL_HEIGHT * scale)))
        self.view_rect = pygame.Rect((win_w - vw) // 2, (win_h - vh) // 2, vw, vh)
        self.view_scale = scale
        self.viewport = self.window.subsurface(self.view_rect)

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.windowed_size = self.window.get_size()
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self._update_viewport()

    def _to_virtual(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        """Physical window coordinates -> 1280x720 design coordinates."""
        return (
            int((pos[0] - self.view_rect.x) / self.view_scale),
            int((pos[1] - self.view_rect.y) / self.view_scale),
        )

    # ------------------------------------------------------------------ #
    # Scene navigation
    # ------------------------------------------------------------------ #
    def _leave_game(self) -> None:
        if self.game_controller is not None:
            self.game_controller.cancel()

    def open_menu(self) -> None:
        self._leave_game()
        self.current_scene = "MENU"

    def open_mode_selection(self) -> None:
        self.current_scene = "MODE_SELECT"

    def open_settings(self) -> None:
        self.current_scene = "SETTINGS"

    def open_statistics(self) -> None:
        self.current_scene = "STATISTICS"

    def start_game(self, mode: GameMode, agents: Tuple[AgentType, AgentType]) -> None:
        """Launches a fresh match with chosen mode and AI agents."""
        self._leave_game()
        self.game_controller = GameController(mode=mode, agents=agents)
        self.game_controller.step_delay_sec = 0.2 if self.settings_mgr.ai_speed == "Fast" else 0.8
        self.game_screen = GameplayScreen(
            controller=self.game_controller,
            on_menu=self.open_menu,
            on_game_over=self.handle_game_over,
            settings=self.settings_mgr,
        )
        self.current_scene = "GAME"

    def handle_game_over(self, state: GameState) -> None:
        """Transitions to Screen 6 Game Over screen."""
        self.game_over_screen = GameOverScreen(
            state=state,
            on_play_again=self.play_again,
            on_back_menu=self.open_menu,
            stats_mgr=self.stats_mgr,
            settings=self.settings_mgr,
        )
        self.current_scene = "GAME_OVER"

    def play_again(self) -> None:
        if self.game_controller:
            self.start_game(self.game_controller.mode, self.game_controller.agents)
        else:
            self.open_mode_selection()

    def quit_app(self) -> None:
        self.is_running = False

    def _active_screen(self):
        return {
            "MENU": self.menu_screen,
            "MODE_SELECT": self.mode_screen,
            "GAME": self.game_screen,
            "GAME_OVER": self.game_over_screen,
            "SETTINGS": self.settings_screen,
            "STATISTICS": self.stats_screen,
        }.get(self.current_scene)

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        while self.is_running:
            virtual_mouse = self._to_virtual(pygame.mouse.get_pos())
            theme.set_virtual_mouse(virtual_mouse)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                    break
                if event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED):
                    if not self.fullscreen:
                        w, h = self.window.get_size() if event.type == pygame.WINDOWSIZECHANGED \
                            else (event.w, event.h)
                        if w < MIN_WINDOW[0] or h < MIN_WINDOW[1]:
                            pygame.display.set_mode((max(w, MIN_WINDOW[0]), max(h, MIN_WINDOW[1])),
                                                    pygame.RESIZABLE)
                    self._update_viewport()
                    continue
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and \
                        (event.mod & pygame.KMOD_ALT):
                    self.toggle_fullscreen()
                    continue

                if hasattr(event, "pos"):
                    virtual_mouse = self._to_virtual(event.pos)
                    theme.set_virtual_mouse(virtual_mouse)

                screen = self._active_screen()
                if screen is not None:
                    screen.handle_event(event, virtual_mouse)

            if not self.is_running:
                break

            if self.current_scene == "GAME" and self.game_screen:
                self.game_screen.update()

            # Draw at physical resolution into the letter-boxed viewport
            self.window.fill(COLORS["bg_dark"])
            screen = self._active_screen()
            if screen is not None:
                screen.draw(self.viewport)
            pygame.display.flip()

            # Full frame-rate while focused, light idle rate otherwise
            self.clock.tick(60 if pygame.key.get_focused() else 20)

        pygame.quit()


if __name__ == "__main__":
    app = BingoApp()
    app.run()
    sys.exit(0)
