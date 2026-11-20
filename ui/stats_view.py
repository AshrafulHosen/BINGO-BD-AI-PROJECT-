"""
BINGO-BD Statistics Screen
Cumulative records, Human-vs-AI breakdown by difficulty (with win-rate bars),
recent matches, and a two-step "Clear Stats" confirmation.
"""

from __future__ import annotations

from typing import Tuple, Callable

import pygame

from ui.theme import (
    COLORS,
    VIRTUAL_WIDTH,
    VIRTUAL_HEIGHT,
    draw_text,
    draw_rounded_rect,
    draw_circle,
    draw_icon,
    draw_app_background,
    static_layer,
    get_overlay,
    play_sound,
)
from ui.widgets import Button, IconButton, draw_panel
from data.stats_manager import StatsManager
from data.settings_manager import SettingsManager

MODE_LABEL = {"HUMAN_VS_AI": "Human vs AI", "HUMAN_VS_HUMAN": "Human vs Human", "AI_VS_AI": "AI vs AI"}


class StatisticsScreen:
    """Statistics screen showing cumulative performance and difficulty breakdown."""

    PANEL = pygame.Rect(110, 24, 1060, 672)

    def __init__(self, on_back: Callable[[], None], stats_mgr: StatsManager, settings: SettingsManager):
        self.on_back = on_back
        self.stats_mgr = stats_mgr
        self.settings = settings
        self.show_confirm_clear = False

        p = self.PANEL
        self.btn_back = IconButton((p.x + 44, p.y + 44), radius=22, icon="back", on_click=self.on_back)
        self.btn_clear = Button((p.right - 190, p.y + 22, 160, 44), text="Clear Stats", icon="trash",
                                variant="danger", font_size=15, radius=12, on_click=self._prompt_clear, lip=3)
        cx = VIRTUAL_WIDTH // 2
        self.btn_confirm_yes = Button((cx - 150, 410, 140, 48), text="Yes, clear", variant="danger",
                                      font_size=16, radius=12, on_click=self._execute_clear)
        self.btn_confirm_no = Button((cx + 10, 410, 140, 48), text="Cancel", variant="navy",
                                     font_size=16, radius=12, on_click=self._cancel_clear)

    def _prompt_clear(self) -> None:
        self.show_confirm_clear = True

    def _cancel_clear(self) -> None:
        self.show_confirm_clear = False

    def _execute_clear(self) -> None:
        self.stats_mgr.clear()
        self.show_confirm_clear = False

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        if self.show_confirm_clear:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.show_confirm_clear = False
                return
            self.btn_confirm_yes.handle_event(event, mouse_pos, self.settings)
            self.btn_confirm_no.handle_event(event, mouse_pos, self.settings)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        self.btn_back.handle_event(event, mouse_pos, self.settings)
        self.btn_clear.handle_event(event, mouse_pos, self.settings)

    CARD_W, CARD_GAP = 236, 20
    CARDS = [
        ("Total Matches", "total_matches", COLORS["human_blue_light"], "statistics"),
        ("Human Wins", "human_wins", COLORS["btn_green_hover"], "trophy"),
        ("AI Wins", "ai_wins", COLORS["ai_red_light"], "robot"),
        ("Draws", "draws", COLORS["gold_glow"], "users"),
    ]
    ROWS = [("Easy", "Heuristic", "EASY"), ("Medium", "Minimax", "MEDIUM"), ("Hard", "MCTS", "HARD")]

    def _card_rect(self, i: int) -> pygame.Rect:
        p = self.PANEL
        x0 = p.x + (p.w - (self.CARD_W * 4 + self.CARD_GAP * 3)) / 2
        return pygame.Rect(int(x0 + i * (self.CARD_W + self.CARD_GAP)), p.y + 96, self.CARD_W, 100)

    def _table_rect(self) -> pygame.Rect:
        p = self.PANEL
        return pygame.Rect(p.x + 30, p.y + 216, p.w - 60, 236)

    def _table_cols(self) -> list:
        t = self._table_rect()
        return [t.x + 24, t.x + 250, t.x + 360, t.x + 490, t.x + 600, t.x + 700]

    def _paint_static(self, surface: pygame.Surface) -> None:
        draw_app_background(surface)
        p = self.PANEL
        draw_panel(surface, p, radius=26, gradient=((18, 42, 80), (11, 28, 56)))
        draw_text(surface, "Match Statistics", 34, COLORS["text_white"], (p.centerx, p.y + 46))
        for i, (title, _key, col, icon) in enumerate(self.CARDS):
            r = self._card_rect(i)
            draw_rounded_rect(surface, r, (16, 38, 74), 18, COLORS["border_light"], 1.2)
            draw_circle(surface, (r.x + 40, r.centery), 24, (*col[:3], 40))
            draw_icon(surface, icon, (r.x + 40, r.centery), 24, col)
            draw_text(surface, title, 14, COLORS["text_muted"], (r.x + 78, r.y + 32), anchor="midleft",
                      weight="semibold")
        t = self._table_rect()
        cols = self._table_cols()
        draw_rounded_rect(surface, t, (14, 34, 66), 18, COLORS["border_light"], 1.2)
        draw_text(surface, "Human vs AI by difficulty", 18, COLORS["text_white"], (t.x + 24, t.y + 28),
                  anchor="midleft")
        heads = ["Difficulty", "Matches", "Human wins", "AI wins", "Draws", "Human win rate"]
        for h, x in zip(heads, cols):
            draw_text(surface, h, 13, COLORS["text_dim"], (x, t.y + 64), anchor="midleft", weight="black")
        draw_rounded_rect(surface, (t.x + 20, t.y + 82, t.w - 40, 1), COLORS["border_light"], 0)
        for i, (name, algo, _k) in enumerate(self.ROWS):
            y = t.y + 114 + i * 42
            draw_text(surface, name, 16, COLORS["text_white"], (cols[0], y), anchor="midleft")
            draw_text(surface, algo, 13, COLORS["text_muted"], (cols[0] + 74, y + 1), anchor="midleft",
                      weight="semibold")
        rr = pygame.Rect(p.x + 30, p.y + 470, p.w - 60, 176)
        draw_rounded_rect(surface, rr, (14, 34, 66), 18, COLORS["border_light"], 1.2)
        draw_text(surface, "Recent matches", 18, COLORS["text_white"], (rr.x + 24, rr.y + 28), anchor="midleft")

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(static_layer("stats", self._paint_static), (0, 0))
        p = self.PANEL
        self.btn_back.draw(surface)
        self.btn_clear.draw(surface)
        stats = self.stats_mgr.stats

        for i, (_title, key, _col, _icon) in enumerate(self.CARDS):
            r = self._card_rect(i)
            draw_text(surface, str(stats.get(key, 0)), 36, COLORS["text_white"], (r.x + 78, r.y + 66),
                      anchor="midleft", weight="black")

        t = self._table_rect()
        cols = self._table_cols()
        by = stats.get("by_difficulty", {})
        for i, (_name, _algo, key) in enumerate(self.ROWS):
            d = by.get(key, {})
            y = t.y + 114 + i * 42
            m, hw, aw, dr = d.get("matches", 0), d.get("human_wins", 0), d.get("ai_wins", 0), d.get("draws", 0)
            draw_text(surface, str(m), 16, COLORS["text_light"], (cols[1], y), anchor="midleft", weight="semibold")
            draw_text(surface, str(hw), 16, COLORS["btn_green_hover"], (cols[2], y), anchor="midleft")
            draw_text(surface, str(aw), 16, COLORS["ai_red_light"], (cols[3], y), anchor="midleft")
            draw_text(surface, str(dr), 16, COLORS["gold_glow"], (cols[4], y), anchor="midleft")
            rate = hw / m if m else 0.0
            bar = pygame.Rect(cols[5], y - 6, 200, 12)
            draw_rounded_rect(surface, bar, COLORS["bg_card_inner"], 6, COLORS["border_light"], 1)
            if rate > 0:
                draw_rounded_rect(surface, (bar.x, bar.y, max(12, int(bar.w * rate)), bar.h), None, 6,
                                  gradient=(COLORS["green_top"], COLORS["green_bottom"]))
            draw_text(surface, f"{rate * 100:.0f}%" if m else "—", 15, COLORS["text_white"],
                      (bar.right + 14, y), anchor="midleft")

        # Recent matches
        rr = pygame.Rect(p.x + 30, p.y + 470, p.w - 60, 176)
        recent = stats.get("recent_history", [])[:4]
        if not recent:
            draw_text(surface, "No matches played yet — go call some numbers!", 15, COLORS["text_muted"],
                      (rr.centerx, rr.centery + 12), weight="semibold")
        for i, h in enumerate(recent):
            y = rr.y + 66 + i * 30
            res = h.get("winner", "?")
            col = COLORS["gold_glow"] if res == "Draw" else (
                COLORS["human_blue_light"] if res == "Player 1" else COLORS["ai_red_light"])
            draw_circle(surface, (rr.x + 30, y), 5, col)
            mode = MODE_LABEL.get(h.get("mode", ""), h.get("mode", ""))
            draw_text(surface, f"{mode}  ({h.get('agent_0', '').title()} vs {h.get('agent_1', '').title()})",
                      14, COLORS["text_light"], (rr.x + 46, y), anchor="midleft", weight="semibold")
            draw_text(surface, f"Winner: {res}", 14, col, (rr.x + 520, y), anchor="midleft")
            draw_text(surface, f"{h.get('lines_p1', 0)}–{h.get('lines_p2', 0)} lines · {h.get('calls_count', 0)} calls",
                      14, COLORS["text_muted"], (rr.x + 680, y), anchor="midleft", weight="semibold")
            draw_text(surface, h.get("timestamp", "")[5:16], 13, COLORS["text_dim"], (rr.right - 24, y),
                      anchor="midright", weight="semibold")

        if self.show_confirm_clear:
            surface.blit(get_overlay(), (0, 0))
            c = pygame.Rect((VIRTUAL_WIDTH - 440) // 2, 250, 440, 240)
            draw_panel(surface, c, radius=22, border=COLORS["ai_red"], border_width=2,
                       gradient=((24, 46, 86), (14, 30, 60)))
            draw_icon(surface, "trash", (c.centerx, c.y + 46), 34, COLORS["ai_red_light"])
            draw_text(surface, "Clear all statistics?", 22, COLORS["text_white"], (c.centerx, c.y + 96))
            draw_text(surface, "This permanently resets every record.", 15, COLORS["text_muted"],
                      (c.centerx, c.y + 128), weight="semibold")
            self.btn_confirm_yes.draw(surface)
            self.btn_confirm_no.draw(surface)
