"""
BINGO-BD UI Package
Houses presentation layer, widgets, screens, and thematic design components.
"""

from ui.theme import COLORS, VIRTUAL_WIDTH, VIRTUAL_HEIGHT, init_audio, play_sound
from ui.widgets import Button, IconButton, BoardCellTile, LetterBadge
from ui.menu import MainMenuScreen
from ui.modes import ModeSelectScreen
from ui.game import GameplayScreen
from ui.results import GameOverScreen
from ui.settings_view import SettingsScreen
from ui.stats_view import StatisticsScreen

__all__ = [
    "COLORS",
    "VIRTUAL_WIDTH",
    "VIRTUAL_HEIGHT",
    "init_audio",
    "play_sound",
    "Button",
    "IconButton",
    "BoardCellTile",
    "LetterBadge",
    "MainMenuScreen",
    "ModeSelectScreen",
    "GameplayScreen",
    "GameOverScreen",
    "SettingsScreen",
    "StatisticsScreen",
]
