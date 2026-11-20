"""
BINGO-BD UI Theme & Rendering Kit
=================================

Design tokens (colours, type scale) matched to "BINGO-BD Game UI Concept Sheet.png"
plus a small resolution-independent rendering layer.

Resolution model
----------------
All screens are laid out in a fixed *design space* of 1280 x 720 units
(``VIRTUAL_WIDTH`` x ``VIRTUAL_HEIGHT``).  At runtime ``set_scale`` is called
with ``min(window_w / 1280, window_h / 720)`` and every helper in this module
converts design units to physical pixels *before* drawing.  Nothing is drawn
small and stretched afterwards, so text and shapes are pixel-crisp at 720p,
1080p, 1440p and 4K alike.

Anti-aliasing
-------------
* Text: TrueType hinting at the exact physical pixel size.
* Rounded rectangles, circles and icons: rendered 3x super-sampled, then
  ``smoothscale``d down once and cached (keyed by size/colour), so the
  per-frame cost is a single blit.
"""

from __future__ import annotations

import math
import os
import sys
from typing import Dict, Tuple, Optional, Sequence, Any

import pygame

from data.settings_manager import SettingsManager

VIRTUAL_WIDTH = 1280
VIRTUAL_HEIGHT = 720

Color = Tuple[int, ...]

# --------------------------------------------------------------------------- #
# Design tokens (sampled from the concept sheet)
# --------------------------------------------------------------------------- #
COLORS: Dict[str, Color] = {
    # Surfaces
    "bg_dark": (8, 20, 40),              # app background (deep navy)
    "bg_dark_gradient": (14, 34, 66),    # top of background gradient
    "bg_card": (14, 35, 68),             # panel / card
    "bg_card_alt": (20, 46, 86),         # elevated card
    "bg_card_inner": (10, 26, 52),       # recessed well
    "border_light": (40, 74, 122),       # hairline border
    "border_strong": (62, 104, 164),
    "border_focus": (74, 158, 255),      # focus / active turn glow

    # Text
    "text_white": (255, 255, 255),
    "text_light": (222, 232, 246),
    "text_muted": (150, 172, 204),
    "text_dim": (104, 128, 164),
    "text_dark": (16, 28, 48),

    # Primary action (green)
    "green_top": (52, 211, 102),
    "green_bottom": (22, 163, 74),
    "green_lip": (12, 112, 52),
    "green_border": (110, 236, 150),
    "btn_green": (34, 186, 88),
    "btn_green_hover": (74, 222, 128),

    # Secondary (navy)
    "navy_top": (26, 58, 106),
    "navy_bottom": (16, 40, 78),
    "navy_lip": (7, 20, 42),
    "navy_border": (54, 96, 158),
    "navy_hover_top": (34, 74, 134),
    "navy_hover_bottom": (22, 52, 100),

    # Danger
    "red_top": (244, 72, 92),
    "red_bottom": (204, 36, 64),
    "red_lip": (130, 18, 40),

    # Player 1 / Human (blue)
    "human_blue": (30, 123, 234),
    "human_blue_light": (96, 170, 255),
    "human_header_top": (48, 132, 242),
    "human_header_bottom": (26, 92, 204),
    "human_band": (22, 74, 168),

    # Player 2 / AI (red)
    "ai_red": (226, 46, 72),
    "ai_red_light": (255, 120, 136),
    "ai_header_top": (240, 72, 90),
    "ai_header_bottom": (196, 30, 58),
    "ai_band": (160, 24, 48),

    # Board tiles
    "tile_bg": (248, 250, 253),
    "tile_grid": (204, 214, 230),
    "tile_hover": (226, 238, 255),
    "tile_selected": (255, 244, 200),
    "mark_blue": (30, 123, 234),
    "mark_blue_ring": (140, 196, 255),

    # Gold accents
    "gold": (255, 196, 46),
    "gold_dark": (226, 150, 10),
    "gold_glow": (255, 214, 92),
    "gold_light": (255, 236, 160),

    # Status
    "success": (34, 197, 94),
    "warning": (250, 176, 40),

    # BINGO letter states
    "letter_inactive": (30, 52, 88),
    "letter_inactive_text": (98, 124, 164),

    # Overlay
    "modal_overlay": (4, 10, 24, 190),

    # Chalkboard / school props
    "chalkboard_bg": (34, 54, 46),
    "chalkboard_frame": (150, 96, 52),
    "chalk_white": (240, 244, 240),
    "chalk_green": (130, 230, 170),
}

# Backwards-compatible aliases used by older code paths
COLORS.update({
    "human_card_header": COLORS["human_header_bottom"],
    "ai_card_header": COLORS["ai_header_bottom"],
    "tile_called": COLORS["mark_blue"],
    "tile_border": COLORS["tile_grid"],
})

# Type scale (design units)
FONT_SIZES = {
    "display": 96,
    "h1": 40,
    "h2": 30,
    "h3": 22,
    "body": 17,
    "small": 14,
    "micro": 12,
}

# --------------------------------------------------------------------------- #
# Scale management
# --------------------------------------------------------------------------- #
_scale: float = 1.0
_virtual_mouse: Tuple[int, int] = (-1, -1)
_SS = 3  # super-sampling factor for shapes


def set_scale(scale: float) -> None:
    """Set design->physical scale; clears size-dependent caches when it changes."""
    global _scale
    scale = max(0.25, float(scale))
    if abs(scale - _scale) > 1e-6:
        _scale = scale
        clear_caches()


def get_scale() -> float:
    return _scale


def S(v: float) -> int:
    """Design units -> physical pixels."""
    return int(round(v * _scale))


def SF(v: float) -> float:
    return v * _scale


def SR(rect: Any) -> pygame.Rect:
    """Design-space rect -> physical rect (edges rounded independently: no gaps)."""
    r = pygame.Rect(rect) if not isinstance(rect, pygame.Rect) else rect
    x0, y0 = S(r.x), S(r.y)
    x1, y1 = S(r.x + r.w), S(r.y + r.h)
    return pygame.Rect(x0, y0, max(1, x1 - x0), max(1, y1 - y0))


def SP(pt: Sequence[float]) -> Tuple[int, int]:
    return S(pt[0]), S(pt[1])


def set_virtual_mouse(pos: Tuple[int, int]) -> None:
    global _virtual_mouse
    _virtual_mouse = pos


def virtual_mouse() -> Tuple[int, int]:
    return _virtual_mouse


# --------------------------------------------------------------------------- #
# Caches
# --------------------------------------------------------------------------- #
_shape_cache: Dict[Any, pygame.Surface] = {}
_text_cache: Dict[Any, pygame.Surface] = {}
_misc_cache: Dict[Any, pygame.Surface] = {}
_fonts: Dict[Tuple[int, str], pygame.font.Font] = {}


def _fast(surf: pygame.Surface) -> pygame.Surface:
    """Convert to the display pixel format so SDL can use its fast blit path."""
    if pygame.display.get_init() and pygame.display.get_surface() is not None:
        try:
            if surf.get_flags() & pygame.SRCALPHA:
                return surf.convert_alpha()
            return surf.convert()
        except Exception:
            return surf
    return surf


def _cache_put(cache: Dict[Any, pygame.Surface], key: Any, surf: pygame.Surface, cap: int) -> pygame.Surface:
    surf = _fast(surf)
    if len(cache) >= cap:
        # drop oldest half (dicts keep insertion order)
        for k in list(cache.keys())[: cap // 2]:
            del cache[k]
    cache[key] = surf
    return surf


def clear_caches() -> None:
    _shape_cache.clear()
    _text_cache.clear()
    _misc_cache.clear()
    _fonts.clear()


# --------------------------------------------------------------------------- #
# Colour helpers
# --------------------------------------------------------------------------- #
def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1: Color, c2: Color, t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def with_alpha(c: Color, a: int) -> Tuple[int, int, int, int]:
    return (c[0], c[1], c[2], max(0, min(255, a)))


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# --------------------------------------------------------------------------- #
# Fonts
# --------------------------------------------------------------------------- #
_FONT_FILES = {
    "regular": ["segoeui.ttf", "arial.ttf"],
    "semibold": ["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"],
    "bold": ["segoeuib.ttf", "arialbd.ttf"],
    "black": ["seguibl.ttf", "ariblk.ttf", "segoeuib.ttf", "arialbd.ttf"],
}
_FONT_FALLBACK_NAMES = {
    "regular": (["segoeui", "dejavusans", "liberationsans", "helvetica", "arial"], False),
    "semibold": (["segoeuisemibold", "dejavusans", "liberationsans", "helvetica", "arial"], True),
    "bold": (["segoeui", "dejavusans", "liberationsans", "helvetica", "arial"], True),
    "black": (["segoeuiblack", "arialblack", "dejavusans", "liberationsans", "arial"], True),
}
_font_path_cache: Dict[str, Optional[str]] = {}


def _resolve_font_path(weight: str) -> Optional[str]:
    if weight in _font_path_cache:
        return _font_path_cache[weight]
    path: Optional[str] = None
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for fname in _FONT_FILES.get(weight, []):
        p = os.path.join(windir, "Fonts", fname)
        if os.path.exists(p):
            path = p
            break
    if path is None:
        names, bold = _FONT_FALLBACK_NAMES.get(weight, (["arial"], False))
        for n in names:
            try:
                p = pygame.font.match_font(n, bold=bold)
            except Exception:
                p = None
            if p:
                path = p
                break
    _font_path_cache[weight] = path
    return path


def get_font(size: float, bold: bool = False, weight: Optional[str] = None) -> pygame.font.Font:
    """Font at the *physical* pixel size for design size ``size``."""
    if weight is None:
        weight = "bold" if bold else "regular"
    px = max(6, int(round(size * _scale)))
    key = (px, weight)
    f = _fonts.get(key)
    if f is None:
        path = _resolve_font_path(weight)
        try:
            f = pygame.font.Font(path, px) if path else pygame.font.Font(None, int(px * 1.3))
        except Exception:
            f = pygame.font.Font(None, int(px * 1.3))
        _fonts[key] = f
    return f


def render_text(
    text: str,
    size: float,
    color: Color,
    weight: str = "bold",
    outline: Optional[Tuple[Color, float]] = None,
    gradient: Optional[Tuple[Color, Color]] = None,
) -> pygame.Surface:
    """Cached rendered text surface (physical pixels)."""
    key = (text, size, weight, tuple(color), outline, gradient, _scale)
    surf = _text_cache.get(key)
    if surf is not None:
        return surf

    font = get_font(size, weight=weight)
    base = font.render(text, True, color if gradient is None else (255, 255, 255))
    if gradient is not None:
        g = _vertical_gradient((base.get_width(), base.get_height()), gradient[0], gradient[1])
        g.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        base = g

    if outline is not None:
        o_col, o_w = outline
        ow = max(1, S(o_w))
        o_txt = font.render(text, True, o_col)
        w, h = base.get_width() + ow * 2, base.get_height() + ow * 2
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        steps = max(12, ow * 6)
        for i in range(steps):
            a = 2 * math.pi * i / steps
            out.blit(o_txt, (ow + round(math.cos(a) * ow), ow + round(math.sin(a) * ow)))
        out.blit(o_txt, (ow, ow))
        out.blit(base, (ow, ow))
        base = out

    base = _cache_put(_text_cache, key, base, 3000)
    return base


def draw_text(
    surface: pygame.Surface,
    text: str,
    size: float,
    color: Color,
    pos: Sequence[float],
    anchor: str = "center",
    weight: str = "bold",
    outline: Optional[Tuple[Color, float]] = None,
    gradient: Optional[Tuple[Color, Color]] = None,
    shadow: Optional[Tuple[Color, float]] = None,
    max_width: Optional[float] = None,
) -> pygame.Rect:
    """
    Draw text positioned in design units.  ``anchor`` is any pygame.Rect
    attribute name (center, midleft, topleft, midright, ...).
    Returns the physical rect drawn.
    """
    if max_width is not None:
        # shrink-to-fit: reduce size until it fits (keeps layouts clip-free)
        while size > 8 and get_font(size, weight=weight).size(text)[0] > S(max_width):
            size -= 1
    surf = render_text(text, size, color, weight, outline, gradient)
    rect = surf.get_rect()
    setattr(rect, anchor, SP(pos))
    if shadow is not None:
        s_col, s_off = shadow
        sh = render_text(text, size, s_col, weight, outline, None)
        surface.blit(sh, rect.move(0, S(s_off)))
    surface.blit(surf, rect)
    return rect


def text_width(text: str, size: float, weight: str = "bold") -> float:
    """Text width in design units."""
    return get_font(size, weight=weight).size(text)[0] / _scale


# --------------------------------------------------------------------------- #
# Shapes (super-sampled + cached)
# --------------------------------------------------------------------------- #
def _vertical_gradient(size: Tuple[int, int], top: Color, bottom: Color) -> pygame.Surface:
    w, h = max(1, size[0]), max(1, size[1])
    col = pygame.Surface((1, h), pygame.SRCALPHA)
    ta = top[3] if len(top) > 3 else 255
    ba = bottom[3] if len(bottom) > 3 else 255
    for y in range(h):
        t = y / max(1, h - 1)
        c = lerp_color(top, bottom, t)
        col.set_at((0, y), (c[0], c[1], c[2], int(lerp(ta, ba, t))))
    return pygame.transform.scale(col, (w, h))


def _rounded_surface(
    w: int, h: int, radius: int, fill: Optional[Color],
    gradient: Optional[Tuple[Color, Color]],
    border: Optional[Color], border_w: int,
) -> pygame.Surface:
    ss = _SS if max(w, h) <= 900 else 2
    W, H, R = w * ss, h * ss, max(0, radius * ss)
    R = min(R, W // 2, H // 2)
    base_rgb = (gradient[0] if gradient else fill) or (0, 0, 0)
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    surf.fill((base_rgb[0], base_rgb[1], base_rgb[2], 0))
    if gradient is not None:
        g = _vertical_gradient((W, H), gradient[0], gradient[1])
        mask = pygame.Surface((W, H), pygame.SRCALPHA)
        mask.fill((255, 255, 255, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, W, H), border_radius=R)
        g.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf = g
    elif fill is not None:
        pygame.draw.rect(surf, fill, (0, 0, W, H), border_radius=R)
    if border is not None and border_w > 0:
        if len(border) > 3 and border[3] < 255 and (fill is not None or gradient is not None):
            # blend translucent borders over the fill instead of overwriting it
            layer = pygame.Surface((W, H), pygame.SRCALPHA)
            layer.fill((border[0], border[1], border[2], 0))
            pygame.draw.rect(layer, border, (0, 0, W, H), width=border_w * ss, border_radius=R)
            surf.blit(layer, (0, 0))
        else:
            pygame.draw.rect(surf, border, (0, 0, W, H), width=border_w * ss, border_radius=R)
    return pygame.transform.smoothscale(surf, (w, h))


def draw_rounded_rect(
    surface: pygame.Surface,
    rect: Any,
    color: Optional[Color],
    radius: float = 12,
    border_color: Optional[Color] = None,
    border_width: float = 1,
    gradient: Optional[Tuple[Color, Color]] = None,
) -> pygame.Rect:
    """Anti-aliased rounded rect in design units (optional vertical gradient)."""
    pr = SR(rect)
    bw = max(1, S(border_width)) if border_color is not None and border_width > 0 else 0
    key = ("rr", pr.w, pr.h, S(radius), tuple(color) if color else None,
           gradient, tuple(border_color) if border_color else None, bw)
    surf = _shape_cache.get(key)
    if surf is None:
        surf = _rounded_surface(pr.w, pr.h, S(radius), color, gradient, border_color, bw)
        surf = _cache_put(_shape_cache, key, surf, 1500)
    surface.blit(surf, pr.topleft)
    return pr


def draw_shadow(
    surface: pygame.Surface,
    rect: Any,
    radius: float = 16,
    offset: Tuple[float, float] = (0, 6),
    blur: float = 14,
    alpha: int = 120,
    color: Color = (0, 6, 18),
) -> None:
    """Soft drop shadow (box-blur via down/up-sampling), cached."""
    pr = SR(rect)
    b = max(2, S(blur))
    key = ("sh", pr.w, pr.h, S(radius), b, alpha, tuple(color))
    surf = _shape_cache.get(key)
    if surf is None:
        w, h = pr.w + b * 2, pr.h + b * 2
        base = pygame.Surface((w, h), pygame.SRCALPHA)
        base.fill((color[0], color[1], color[2], 0))
        pygame.draw.rect(base, (color[0], color[1], color[2], alpha), (b, b, pr.w, pr.h),
                         border_radius=S(radius))
        f = max(2, b // 2)
        small = pygame.transform.smoothscale(base, (max(1, w // f), max(1, h // f)))
        surf = pygame.transform.smoothscale(small, (w, h))
        surf = _cache_put(_shape_cache, key, surf, 1500)
    surface.blit(surf, (pr.x - b + S(offset[0]), pr.y - b + S(offset[1])))


def draw_circle(
    surface: pygame.Surface,
    center: Sequence[float],
    radius: float,
    color: Optional[Color],
    border_color: Optional[Color] = None,
    border_width: float = 0,
    gradient: Optional[Tuple[Color, Color]] = None,
) -> None:
    """Anti-aliased circle in design units (optional border / gradient)."""
    r = max(1, S(radius))
    bw = max(1, S(border_width)) if border_color is not None and border_width > 0 else 0
    key = ("c", r, tuple(color) if color else None, gradient,
           tuple(border_color) if border_color else None, bw)
    surf = _shape_cache.get(key)
    if surf is None:
        surf = _rounded_surface(r * 2, r * 2, r, color, gradient, border_color, bw)
        surf = _cache_put(_shape_cache, key, surf, 1500)
    cx, cy = SP(center)
    surface.blit(surf, (cx - r, cy - r))


def draw_gradient_vertical(
    surface: pygame.Surface,
    rect: Any,
    top_color: Color,
    bottom_color: Color,
) -> None:
    """Vertical gradient (design units), cached."""
    pr = SR(rect)
    key = ("grad", pr.w, pr.h, tuple(top_color), tuple(bottom_color))
    surf = _shape_cache.get(key)
    if surf is None:
        surf = _vertical_gradient((pr.w, pr.h), top_color, bottom_color)
        surf = _cache_put(_shape_cache, key, surf, 1500)
    surface.blit(surf, pr.topleft)


def draw_thick_line(
    surface: pygame.Surface,
    p1: Sequence[float],
    p2: Sequence[float],
    width: float,
    color: Color,
) -> None:
    """Anti-aliased thick line with round caps (design units). Not cached."""
    x1, y1 = SF(p1[0]), SF(p1[1])
    x2, y2 = SF(p2[0]), SF(p2[1])
    w = max(1.0, SF(width))
    pad = int(w) + 2
    minx, miny = int(min(x1, x2)) - pad, int(min(y1, y2)) - pad
    maxx, maxy = int(max(x1, x2)) + pad, int(max(y1, y2)) + pad
    ss = 2
    W, H = (maxx - minx) * ss, (maxy - miny) * ss
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    surf.fill((color[0], color[1], color[2], 0))
    a = (int((x1 - minx) * ss), int((y1 - miny) * ss))
    b = (int((x2 - minx) * ss), int((y2 - miny) * ss))
    rw = int(w * ss)
    pygame.draw.line(surf, color, a, b, rw)
    pygame.draw.circle(surf, color, a, rw // 2)
    pygame.draw.circle(surf, color, b, rw // 2)
    surface.blit(pygame.transform.smoothscale(surf, (W // ss, H // ss)), (minx, miny))


def get_overlay(alpha_color: Color = COLORS["modal_overlay"]) -> pygame.Surface:
    """Full-screen translucent overlay surface (cached per scale)."""
    w, h = S(VIRTUAL_WIDTH), S(VIRTUAL_HEIGHT)
    key = ("overlay", w, h, tuple(alpha_color))
    surf = _misc_cache.get(key)
    if surf is None:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill(alpha_color)
        _misc_cache[key] = surf
    return surf


def cached_layer(key: Any, builder) -> pygame.Surface:
    """Generic per-scale cache for expensive full-screen layers."""
    full_key = ("layer", key, _scale)
    surf = _misc_cache.get(full_key)
    if surf is None:
        surf = _fast(builder())
        _misc_cache[full_key] = surf
    return surf


def static_layer(key: Any, painter) -> pygame.Surface:
    """
    Pre-compose a screen's static chrome (background, panels, shadows) into a
    single opaque surface.  ``painter(surface)`` draws in design units.  One
    opaque blit per frame replaces dozens of large per-pixel-alpha blits,
    which keeps 4K frame times low.
    """
    def build() -> pygame.Surface:
        surf = pygame.Surface((S(VIRTUAL_WIDTH), S(VIRTUAL_HEIGHT)))
        painter(surf)
        return surf.convert() if pygame.display.get_surface() is not None else surf
    full_key = ("static", key, _scale)
    surf = _misc_cache.get(full_key)
    if surf is None:
        if len(_misc_cache) > 64:
            for k in [k for k in _misc_cache if k[0] == "static"][:16]:
                del _misc_cache[k]
        surf = build()
        _misc_cache[full_key] = surf
    return surf


def draw_app_background(surface: pygame.Surface) -> None:
    """Standard navy gradient background with subtle radial glow (cached)."""
    def build() -> pygame.Surface:
        w, h = S(VIRTUAL_WIDTH), S(VIRTUAL_HEIGHT)
        surf = _vertical_gradient((w, h), COLORS["bg_dark_gradient"], COLORS["bg_dark"]).convert()
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, int(h * 0.38)
        maxr = int(w * 0.55)
        for i in range(24, 0, -1):
            r = int(maxr * i / 24)
            pygame.draw.circle(glow, (40, 90, 170, 3), (cx, cy), r)
        surf.blit(glow, (0, 0))
        return surf
    surface.blit(cached_layer("app_bg", build), (0, 0))


# --------------------------------------------------------------------------- #
# Vector icons (super-sampled + cached)
# --------------------------------------------------------------------------- #
def _icon_paint(s: pygame.Surface, icon: str, n: int, color: Color) -> None:
    """Paint ``icon`` on an n x n surface (already super-sampled)."""
    clear = (color[0], color[1], color[2], 0)
    u = n / 24.0  # icon grid unit (24-unit icon box)

    def P(x: float, y: float) -> Tuple[int, int]:
        return int(x * u), int(y * u)

    def line(pts, w=2.4):
        pts = [P(*p) for p in pts]
        width = max(1, int(w * u))
        pygame.draw.lines(s, color, False, pts, width)
        for p in pts:
            pygame.draw.circle(s, color, p, width // 2)

    if icon == "play":
        pygame.draw.polygon(s, color, [P(7, 4.5), P(7, 19.5), P(19.5, 12)])
    elif icon == "pause":
        pygame.draw.rect(s, color, (*P(6, 5), int(4 * u), int(14 * u)), border_radius=int(u))
        pygame.draw.rect(s, color, (*P(14, 5), int(4 * u), int(14 * u)), border_radius=int(u))
    elif icon in ("settings", "gear"):
        for i in range(8):
            a = i * math.pi / 4
            tw = 3.4
            pts = []
            for dx, dy in ((-tw / 2, 0), (tw / 2, 0), (tw / 2, 10.5), (-tw / 2, 10.5)):
                x = 12 + dx * math.cos(a) - dy * math.sin(a)
                y = 12 + dx * math.sin(a) + dy * math.cos(a)
                pts.append(P(x, y))
            pygame.draw.polygon(s, color, pts)
        pygame.draw.circle(s, color, P(12, 12), int(8 * u))
        pygame.draw.circle(s, clear, P(12, 12), int(3.4 * u))
    elif icon in ("statistics", "chart"):
        for x, h in ((4.5, 7), (10.5, 12), (16.5, 17)):
            pygame.draw.rect(s, color, (int(x * u), int((20 - h) * u), int(4 * u), int(h * u)),
                             border_radius=int(u))
    elif icon == "exit":
        line([(13, 5), (6, 5), (6, 19), (13, 19)], 2.4)
        line([(10, 12), (20, 12)], 2.4)
        line([(16.5, 8.5), (20, 12), (16.5, 15.5)], 2.4)
    elif icon == "user":
        pygame.draw.circle(s, color, P(12, 8), int(4.6 * u))
        pygame.draw.ellipse(s, color, (*P(4, 14), int(16 * u), int(12 * u)))
        pygame.draw.rect(s, clear, (0, int(21 * u), n, n))
    elif icon == "users":
        pygame.draw.circle(s, color, P(9, 8), int(4 * u))
        pygame.draw.ellipse(s, color, (*P(2, 13.5), int(14 * u), int(11 * u)))
        pygame.draw.circle(s, color, P(17, 9), int(3.3 * u))
        pygame.draw.ellipse(s, color, (*P(13, 14), int(10 * u), int(9 * u)))
        pygame.draw.rect(s, clear, (0, int(21 * u), n, n))
    elif icon == "robot":
        pygame.draw.rect(s, color, (*P(4.5, 8), int(15 * u), int(12 * u)), border_radius=int(3.5 * u))
        pygame.draw.rect(s, color, (*P(11, 4), int(2 * u), int(4 * u)))
        pygame.draw.circle(s, color, P(12, 3.5), int(1.8 * u))
        pygame.draw.rect(s, color, (*P(2, 12), int(2 * u), int(5 * u)), border_radius=int(u))
        pygame.draw.rect(s, color, (*P(20, 12), int(2 * u), int(5 * u)), border_radius=int(u))
        hole = clear
        pygame.draw.circle(s, hole, P(9, 13), int(1.9 * u))
        pygame.draw.circle(s, hole, P(15, 13), int(1.9 * u))
        pygame.draw.rect(s, hole, (*P(9, 16.6), int(6 * u), int(1.6 * u)), border_radius=int(u))
    elif icon == "back":
        line([(19, 12), (5.5, 12)], 2.6)
        line([(11, 6), (5, 12), (11, 18)], 2.6)
    elif icon == "chevron":
        line([(9, 5.5), (15.5, 12), (9, 18.5)], 2.8)
    elif icon in ("close", "x"):
        line([(6.5, 6.5), (17.5, 17.5)], 2.6)
        line([(17.5, 6.5), (6.5, 17.5)], 2.6)
    elif icon == "crown":
        pygame.draw.polygon(s, color, [P(3, 18), P(3, 7), P(8, 12), P(12, 4), P(16, 12), P(21, 7), P(21, 18)])
        pygame.draw.rect(s, color, (*P(3, 19), int(18 * u), int(2.5 * u)), border_radius=int(u))
        for x, y in ((3, 6.5), (12, 3.5), (21, 6.5)):
            pygame.draw.circle(s, color, P(x, y), int(1.8 * u))
    elif icon == "info":
        pygame.draw.circle(s, color, P(12, 12), int(10 * u), max(1, int(2.2 * u)))
        pygame.draw.circle(s, color, P(12, 7.5), int(1.5 * u))
        line([(12, 11), (12, 17)], 2.4)
    elif icon == "check":
        line([(5, 12.5), (10, 17.5), (19.5, 7)], 3.0)
    elif icon == "home":
        pygame.draw.polygon(s, color, [P(12, 3), P(22, 12), P(19, 12), P(19, 21), P(5, 21), P(5, 12), P(2, 12)])
        pygame.draw.rect(s, clear, (*P(10, 14), int(4 * u), int(7 * u)))
    elif icon == "restart":
        rect = pygame.Rect(*P(4.5, 4.5), int(15 * u), int(15 * u))
        pygame.draw.arc(s, color, rect, math.radians(-30), math.radians(250), max(1, int(2.6 * u)))
        pygame.draw.polygon(s, color, [P(18.8, 2.8), P(20.6, 10.2), P(13.6, 8.2)])
    elif icon in ("sound_on", "sound_off"):
        pygame.draw.polygon(s, color, [P(3, 9), P(8, 9), P(13, 4.5), P(13, 19.5), P(8, 15), P(3, 15)])
        if icon == "sound_on":
            for r in (4.5, 8):
                rect = pygame.Rect(int((13 - r) * u), int((12 - r) * u), int(2 * r * u), int(2 * r * u))
                pygame.draw.arc(s, color, rect, math.radians(-50), math.radians(50), max(1, int(2 * u)))
        else:
            line([(16, 9), (21, 15)], 2.4)
            line([(21, 9), (16, 15)], 2.4)
    elif icon == "trash":
        pygame.draw.rect(s, color, (*P(4, 5), int(16 * u), int(2.4 * u)), border_radius=int(u))
        pygame.draw.rect(s, color, (*P(9, 2.5), int(6 * u), int(3 * u)), border_radius=int(u))
        pygame.draw.polygon(s, color, [P(5.5, 8.5), P(18.5, 8.5), P(17.3, 21), P(6.7, 21)])
        hole = clear
        for x in (9.3, 13.3):
            pygame.draw.rect(s, hole, (*P(x, 11), int(1.4 * u), int(7.5 * u)))
    elif icon == "trophy":
        pygame.draw.polygon(s, color, [P(6, 3), P(18, 3), P(17, 11), P(12, 14.5), P(7, 11)])
        pygame.draw.rect(s, color, (*P(11, 14), int(2 * u), int(4 * u)))
        pygame.draw.rect(s, color, (*P(7, 18), int(10 * u), int(3 * u)), border_radius=int(u))
        pygame.draw.arc(s, color, pygame.Rect(*P(2, 4), int(7 * u), int(7 * u)),
                        math.radians(90), math.radians(270), max(1, int(2 * u)))
        pygame.draw.arc(s, color, pygame.Rect(*P(15, 4), int(7 * u), int(7 * u)),
                        math.radians(-90), math.radians(90), max(1, int(2 * u)))
    elif icon == "bolt":
        pygame.draw.polygon(s, color, [P(13.5, 2), P(5, 13.5), P(11, 13.5), P(9.5, 22), P(19, 9.5), P(13, 9.5)])
    elif icon == "monitor":
        pygame.draw.rect(s, color, (*P(2.5, 4), int(19 * u), int(13 * u)), max(1, int(2.2 * u)),
                         border_radius=int(2 * u))
        pygame.draw.rect(s, color, (*P(8, 19.5), int(8 * u), int(2.2 * u)), border_radius=int(u))
    else:
        pygame.draw.circle(s, color, P(12, 12), int(4 * u))


def draw_icon(
    surface: pygame.Surface,
    icon_type: str,
    center: Sequence[float],
    size: float = 24,
    color: Color = (255, 255, 255),
) -> None:
    """Draw a crisp anti-aliased vector icon (design units)."""
    px = max(4, S(size))
    key = ("icon", icon_type, px, tuple(color))
    surf = _shape_cache.get(key)
    if surf is None:
        ss = 4
        n = px * ss
        big = pygame.Surface((n, n), pygame.SRCALPHA)
        big.fill((color[0], color[1], color[2], 0))
        _icon_paint(big, icon_type, n, color)
        surf = pygame.transform.smoothscale(big, (px, px))
        surf = _cache_put(_shape_cache, key, surf, 1500)
    cx, cy = SP(center)
    surface.blit(surf, (cx - px // 2, cy - px // 2))


# --------------------------------------------------------------------------- #
# Audio
# --------------------------------------------------------------------------- #
_sounds: Dict[str, pygame.mixer.Sound] = {}
_sound_initialized = False
_SOUND_NAMES = ("click", "call", "line", "win", "lose", "draw")


def _asset_dir() -> str:
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets")


def pre_init_audio() -> None:
    """Call BEFORE pygame.init(): small buffer = low-latency sound effects."""
    try:
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    except Exception:
        pass


def init_audio() -> None:
    """Initialise the mixer and preload all sound effects (never raises)."""
    global _sound_initialized
    if _sound_initialized:
        return
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(16)
        _sound_initialized = True
        sound_dir = os.path.join(_asset_dir(), "sounds")
        for name in _SOUND_NAMES:
            fpath = os.path.join(sound_dir, f"{name}.wav")
            if os.path.exists(fpath):
                try:
                    _sounds[name] = pygame.mixer.Sound(fpath)
                except Exception:
                    pass
    except Exception:
        _sound_initialized = False


def play_sound(name: str, settings: Optional[SettingsManager] = None) -> None:
    """Play a preloaded effect on a free channel (non-blocking, never raises)."""
    if not _sound_initialized:
        return
    if settings is not None and not settings.sound_enabled:
        return
    snd = _sounds.get(name)
    if snd is None:
        return
    try:
        vol = settings.sound_volume if settings else 0.7
        ch = pygame.mixer.find_channel(True)
        if ch is not None:
            ch.set_volume(vol)
            ch.play(snd)
    except Exception:
        pass
