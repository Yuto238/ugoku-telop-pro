# engine.py — 台本パーサー・アニメーションエンジン・MP4生成ロジック
# 動くテロップメーカー Pro

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import colorsys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ─────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────
WIDTH = 1080
HEIGHT = 1920
FPS = 30
BG_COLOR = (0, 255, 0)          # グリーンバック (BGR for OpenCV)
BG_COLOR_RGB = (0, 255, 0)      # Pillow用 RGB
TEXT_COLOR = (255, 255, 255)    # 白
SHADOW_COLOR = (0, 0, 0, 120)   # 黒シャドウ
SHADOW_OFFSET = (0, 4)
MAX_SEGMENTS = 30
TEXT_MARGIN_LEFT = 80
TEXT_MARGIN_RIGHT = 80
SAFE_SCALE = 1.12
MIN_FONT_SIZE = 30
LINE_SPACING = 10
TEXT_PADDING_X = 80
TEXT_PADDING_TOP = 80
TEXT_PADDING_BOTTOM = 140
GLOW_PADDING = 80
TOP_SAFE_MARGIN = 140
BOTTOM_SAFE_MARGIN = 180
HACKER_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&?+-"
DEBUG_VISUAL = os.getenv("UGOKU_DEBUG_VISUAL", "0") == "1"

VERTICAL_SMALL_CHARS = set("ゃゅょっゎぁぃぅぇぉャュョッァィゥェォ")
VERTICAL_PUNCT_CHARS = set("、。，．・")
VERTICAL_OPEN_BRACKETS = set("「『（([｛【〈《")
VERTICAL_CLOSE_BRACKETS = set("」』）)]｝】〉》")
VERTICAL_ROTATE_90_CHARS = set("ー")
VERTICAL_REPLACEMENTS: Dict[str, str] = {
    "〜": "︱",
    "～": "︱",
}

VERTICAL_CHAR_OFFSETS: Dict[str, Dict[str, float]] = {
    "ー": {"x": 0.00, "y": -0.02, "advance": 0.96, "rotate": 90.0, "scale": 1.00},
    "ゃ": {"x": 0.17, "y": -0.09, "advance": 0.94, "rotate": 0.0, "scale": 0.96},
    "ゅ": {"x": 0.17, "y": -0.09, "advance": 0.94, "rotate": 0.0, "scale": 0.96},
    "ょ": {"x": 0.17, "y": -0.09, "advance": 0.94, "rotate": 0.0, "scale": 0.96},
    "っ": {"x": 0.13, "y": -0.05, "advance": 0.92, "rotate": 0.0, "scale": 0.95},
    "ゎ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ぁ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ぃ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ぅ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ぇ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ぉ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ャ": {"x": 0.17, "y": -0.09, "advance": 0.94, "rotate": 0.0, "scale": 0.96},
    "ュ": {"x": 0.17, "y": -0.09, "advance": 0.94, "rotate": 0.0, "scale": 0.96},
    "ョ": {"x": 0.17, "y": -0.09, "advance": 0.94, "rotate": 0.0, "scale": 0.96},
    "ッ": {"x": 0.13, "y": -0.05, "advance": 0.92, "rotate": 0.0, "scale": 0.95},
    "ァ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ィ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ゥ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ェ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "ォ": {"x": 0.15, "y": -0.07, "advance": 0.93, "rotate": 0.0, "scale": 0.95},
    "、": {"x": 0.24, "y": -0.19, "advance": 0.84, "rotate": 0.0, "scale": 0.98},
    "。": {"x": 0.20, "y": -0.16, "advance": 0.86, "rotate": 0.0, "scale": 0.98},
    "，": {"x": 0.24, "y": -0.19, "advance": 0.84, "rotate": 0.0, "scale": 0.98},
    "．": {"x": 0.20, "y": -0.16, "advance": 0.86, "rotate": 0.0, "scale": 0.98},
    "・": {"x": 0.14, "y": -0.12, "advance": 0.86, "rotate": 0.0, "scale": 0.96},
    "「": {"x": 0.15, "y": -0.06, "advance": 0.90, "rotate": 0.0, "scale": 1.00},
    "」": {"x": -0.08, "y": -0.04, "advance": 0.90, "rotate": 0.0, "scale": 1.00},
    "『": {"x": 0.15, "y": -0.06, "advance": 0.90, "rotate": 0.0, "scale": 1.00},
    "』": {"x": -0.08, "y": -0.04, "advance": 0.90, "rotate": 0.0, "scale": 1.00},
    "（": {"x": 0.13, "y": -0.03, "advance": 0.90, "rotate": 0.0, "scale": 1.00},
    "）": {"x": -0.08, "y": -0.03, "advance": 0.90, "rotate": 0.0, "scale": 1.00},
    "！": {"x": 0.03, "y": -0.02, "advance": 0.98, "rotate": 0.0, "scale": 0.96},
    "？": {"x": 0.03, "y": -0.02, "advance": 0.98, "rotate": 0.0, "scale": 0.96},
    "…": {"x": 0.10, "y": -0.06, "advance": 0.88, "rotate": 0.0, "scale": 0.96},
    "〜": {"x": 0.03, "y": -0.04, "advance": 0.92, "rotate": 90.0, "scale": 0.96},
    "～": {"x": 0.03, "y": -0.04, "advance": 0.92, "rotate": 90.0, "scale": 0.96},
}

ANIMATION_ALIASES: Dict[str, str] = {
    "no_effect": "no_effect",
    "none": "no_effect",
    "static": "no_effect",
    "huge_impact": "huge_impact",
    "stretch_in": "stretch_in",
    "label_reveal": "label_reveal",
    "letter_fade": "letter_fade",
    "shake_accent": "shake_accent",
    "typewriter": "typewriter",
    "letter_drop": "letter_drop",
    "letter_rise": "letter_rise",
    "hacker_text": "hacker_text",
    "neon_flicker": "neon_flicker",
    "block_reveal": "block_reveal",
    "terminal_type": "terminal_type",
    "color_shift": "color_shift",
    "focus_in": "focus_in",
    "fade_up": "letter_fade",
    "soft_pop": "soft_pop",
    "pop_in": "stretch_in",
    "zoom_punch": "huge_impact",
}

FONTS_DIR = Path(__file__).parent / "fonts"
DEFAULT_FONT_CANDIDATES = [
    "NotoSansJP-Bold.otf",
    "NotoSansJP-Bold.ttf",
    "NotoSansJP-VariableFont_wght.ttf",
    "NotoSerifJP-Bold.otf",
    "NotoSerifJP-Bold.ttf",
]

# emphasis ごとのフォントサイズ
FONT_SIZE_MAP = {
    "normal":  76,
    "light":   76,
    "strong":  86,
    "impact":  108,
}

# emphasis ごとの表示時間（秒）
DURATION_MAP = {
    "normal":  1.8,
    "light":   2.0,
    "strong":  2.2,
    "impact":  2.4,
}

# ─────────────────────────────────────────────
# データクラス
# ─────────────────────────────────────────────
@dataclass
class Segment:
    index: int
    text: str
    emphasis: str          # normal / light / strong / impact
    duration: float
    font_size: int
    animation: str
    font_name: str = "Noto Sans JP Bold"
    font_path: str = ""
    text_scale_x: float = 1.0
    text_scale_y: float = 1.0
    text_direction: str = "horizontal"


# ─────────────────────────────────────────────
# イージング関数
# ─────────────────────────────────────────────
def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def ease_out_back(t: float) -> float:
    t = max(0.0, min(1.0, t))
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def ease_in_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t ** 3


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


EASING_MAP = {
    "normal": ease_out_cubic,
    "light":  ease_out_cubic,
    "strong": ease_out_back,
    "impact": ease_out_back,
}

# ─────────────────────────────────────────────
# 台本パーサー
# ─────────────────────────────────────────────
_RE_IMPACT = re.compile(r"^!!([\s\S]*?)!!$", re.DOTALL)
_RE_STRONG = re.compile(r"^\*\*([\s\S]*?)\*\*$", re.DOTALL)
_RE_LIGHT  = re.compile(r"^\*([\s\S]*?)\*$", re.DOTALL)


def _strip_inline_marks(text: str) -> str:
    """インライン強調マーク（行の一部に含まれる場合）を除去する。"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'!!(.*?)!!', r'\1', text)
    return text


def parse_emphasis(raw: str) -> Tuple[str, str]:
    """テキストから強調マークを除去し、(text, emphasis) を返す。"""
    m = _RE_IMPACT.match(raw)
    if m:
        return m.group(1).strip(), "impact"
    m = _RE_STRONG.match(raw)
    if m:
        return m.group(1).strip(), "strong"
    m = _RE_LIGHT.match(raw)
    if m:
        return m.group(1).strip(), "light"
    # 行全体が囲まれていない場合でもインライン強調マークを除去
    cleaned = _strip_inline_marks(raw.strip())
    return cleaned, "normal"


def _normalize_animation_name(name: str | None) -> str:
    if not name:
        return "auto"
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    return ANIMATION_ALIASES.get(key, "auto")


def _animation_from_emphasis(
    emphasis: str,
    emphasis_animation_map: Mapping[str, str] | None = None,
) -> str:
    if emphasis_animation_map:
        candidate = emphasis_animation_map.get(emphasis)
        normalized_candidate = _normalize_animation_name(candidate)
        if normalized_candidate != "auto":
            return normalized_candidate
    return _emphasis_to_animation(emphasis)


def parse_script(
    script_text: str,
    animation_mode: str = "auto",
    emphasis_animation_map: Mapping[str, str] | None = None,
) -> List[Segment]:
    """台本テキストを空行区切りでセグメントに分割する。"""
    normalized_mode = _normalize_animation_name(animation_mode)
    # 空行で分割
    raw_blocks = re.split(r"\n\s*\n", script_text.strip())
    segments: List[Segment] = []
    idx = 1
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        text, emphasis = parse_emphasis(block)
        if not text:
            continue
        if normalized_mode != "auto":
            anim = normalized_mode
        else:
            anim = _animation_from_emphasis(emphasis, emphasis_animation_map)
        seg = Segment(
            index=idx,
            text=text,
            emphasis=emphasis,
            duration=DURATION_MAP[emphasis],
            font_size=FONT_SIZE_MAP[emphasis],
            animation=anim,
        )
        segments.append(seg)
        idx += 1
    return segments


def _emphasis_to_animation(emphasis: str) -> str:
    return {
        "normal": "letter_fade",
        "light": "label_reveal",
        "strong": "stretch_in",
        "impact": "huge_impact",
    }.get(emphasis, "letter_fade")


# ─────────────────────────────────────────────
# アニメーション計算
# ─────────────────────────────────────────────
@dataclass
class FrameParams:
    opacity: float   # 0.0 – 1.0
    scale: float     # 1.0 = 等倍
    y_offset: int    # ピクセル単位のY補正


def _calc_frame_params(seg: Segment, frame_idx: int, total_frames: int) -> FrameParams:
    """フレームごとの opacity / scale / y_offset を計算する。"""
    dur = seg.duration
    enter_dur = max(0.25, dur * 0.25)
    exit_dur  = max(0.20, dur * 0.20)
    hold_dur  = dur - enter_dur - exit_dur

    enter_frames = int(enter_dur * FPS)
    exit_frames  = int(exit_dur  * FPS)
    hold_frames  = total_frames - enter_frames - exit_frames

    easing = EASING_MAP[seg.emphasis]
    emphasis = seg.emphasis

    if frame_idx < enter_frames:
        t = frame_idx / max(1, enter_frames - 1)
        et = easing(t)
        opacity = et

        if emphasis == "normal":
            scale = 0.96 + 0.04 * et
            y_off = int(20 * (1.0 - et))
        elif emphasis == "light":
            scale = 0.96 + 0.08 * et
            y_off = int(16 * (1.0 - et))
        elif emphasis == "strong":
            # scale: 0.94 → 1.06 → 1.0  (overshoot はease_out_backが担う)
            scale = 0.94 + 0.12 * et
            y_off = 0
        else:  # impact
            # scale: 0.88 → 1.10 → 1.0  (overshoot はease_out_backが担う)
            scale = 0.88 + 0.22 * et
            y_off = 0

    elif frame_idx < enter_frames + hold_frames:
        opacity = 1.0
        scale   = 1.0
        y_off   = 0

    else:
        ex_idx = frame_idx - enter_frames - hold_frames
        t = ex_idx / max(1, exit_frames - 1)
        et = ease_in_cubic(t)
        opacity = 1.0 - et

        if emphasis == "impact":
            scale = 1.0 - 0.04 * et
        else:
            scale = 1.0
        y_off = 0

    return FrameParams(opacity=opacity, scale=scale, y_offset=y_off)


# ─────────────────────────────────────────────
# テキスト描画（Pillow）
# ─────────────────────────────────────────────
def _load_font(size: int) -> ImageFont.FreeTypeFont:
    font_path = _default_font_path()
    if font_path is None:
        raise FileNotFoundError(
            f"日本語フォントが見つかりません。{FONTS_DIR} に配置してください。"
        )
    return ImageFont.truetype(str(font_path), size)


def _default_font_path() -> Path | None:
    for filename in DEFAULT_FONT_CANDIDATES:
        candidate = FONTS_DIR / filename
        if candidate.exists():
            return candidate

    preferred_prefixes = ("NotoSansJP", "NotoSerifJP", "MPLUS1p", "ZenMaruGothic")
    all_fonts = sorted(FONTS_DIR.glob("*.ttf")) + sorted(FONTS_DIR.glob("*.otf"))
    for prefix in preferred_prefixes:
        for path in all_fonts:
            if path.name.startswith(prefix):
                return path

    return all_fonts[0] if all_fonts else None


def _segment_text_direction(seg: Segment) -> str:
    direction = (seg.text_direction or "horizontal").strip().lower()
    if direction in ("vertical", "縦書き"):
        return "vertical"
    return "horizontal"


def _segment_scales(seg: Segment) -> Tuple[float, float]:
    sx = max(0.8, min(1.3, float(seg.text_scale_x or 1.0)))
    sy = max(0.8, min(1.3, float(seg.text_scale_y or 1.0)))
    return sx, sy


def _segment_font_path(seg: Segment) -> Path:
    if seg.font_path:
        candidate = Path(seg.font_path)
        if candidate.exists():
            return candidate
    default_path = _default_font_path()
    if default_path is not None:
        return default_path
    return FONTS_DIR / DEFAULT_FONT_CANDIDATES[0]


def _load_font_for_segment(seg: Segment, size: int) -> ImageFont.FreeTypeFont:
    font_path = _segment_font_path(seg)
    if not font_path.exists():
        raise FileNotFoundError(
            f"日本語フォントが見つかりません。{font_path} を配置してください。"
        )
    return ImageFont.truetype(str(font_path), size)


def _text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
) -> Tuple[int, int]:
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=LINE_SPACING, align="center")
    return int(round(bbox[2] - bbox[0])), int(round(bbox[3] - bbox[1]))


def _wrap_single_line(
    draw: ImageDraw.ImageDraw,
    line: str,
    font: ImageFont.FreeTypeFont,
    max_width: float,
) -> List[str]:
    if not line:
        return [""]

    wrapped: List[str] = []
    buf = ""
    for ch in line:
        candidate = buf + ch
        w, _ = _text_size(draw, candidate, font)
        if w <= max_width or not buf:
            buf = candidate
            continue
        wrapped.append(buf)
        buf = ch

    if buf:
        wrapped.append(buf)

    return wrapped if wrapped else [line]


def _wrap_text_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: float,
) -> str:
    lines: List[str] = []
    for raw in text.split("\n"):
        lines.extend(_wrap_single_line(draw, raw, font, max_width))
    return "\n".join(lines)


def _animation_safe_scale(animation: str) -> float:
    return {
        "no_effect": 1.00,
        "huge_impact": 1.12,
        "stretch_in": 1.10,
        "label_reveal": 1.05,
        "block_reveal": 1.08,
        "terminal_type": 1.00,
        "color_shift": 1.00,
        "focus_in": 1.10,
        "soft_pop": 1.08,
        "letter_fade": 1.00,
        "shake_accent": 1.06,
        "typewriter": 1.00,
        "letter_drop": 1.00,
        "letter_rise": 1.00,
        "hacker_text": 1.00,
        "neon_flicker": 1.04,
    }.get(_normalize_animation_name(animation), 1.00)


def _vertical_char_profile(ch: str) -> Dict[str, float]:
    profile: Dict[str, float] = {
        "x": 0.0,
        "y": 0.0,
        "advance": 1.12,
        "rotate": 0.0,
        "scale": 1.0,
    }
    if ch in VERTICAL_SMALL_CHARS:
        profile.update({"x": 0.16, "y": -0.08, "advance": 0.94, "scale": 0.96})
    elif ch in VERTICAL_PUNCT_CHARS:
        profile.update({"x": 0.22, "y": -0.17, "advance": 0.86, "scale": 0.98})
    elif ch in VERTICAL_OPEN_BRACKETS:
        profile.update({"x": 0.14, "y": -0.05, "advance": 0.90})
    elif ch in VERTICAL_CLOSE_BRACKETS:
        profile.update({"x": -0.08, "y": -0.04, "advance": 0.90})
    elif ch in VERTICAL_ROTATE_90_CHARS:
        profile.update({"rotate": 90.0, "advance": 0.96})
    elif ch and ord(ch[0]) < 128 and not ch.isspace():
        profile.update({"x": 0.02, "y": -0.02, "advance": 1.02, "scale": 0.94})

    if ch in VERTICAL_CHAR_OFFSETS:
        profile.update(VERTICAL_CHAR_OFFSETS[ch])
    return profile


def _normalize_vertical_char(ch: str) -> str:
    return VERTICAL_REPLACEMENTS.get(ch, ch)


def draw_vertical_char(
    ch: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int],
    stroke_width: int,
    stroke_fill: Tuple[int, int, int, int] | None,
    profile: Mapping[str, float],
) -> Image.Image:
    normalized_char = _normalize_vertical_char(ch)
    dummy = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dummy)
    bbox = dd.textbbox((0, 0), normalized_char, font=font, stroke_width=stroke_width)
    left, top, right, bottom = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
    glyph_w = max(1, right - left)
    glyph_h = max(1, bottom - top)
    pad = max(10, int(round(font.size * 0.24)))

    layer = Image.new("RGBA", (glyph_w + pad * 2, glyph_h + pad * 2), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(layer)
    ldraw.text(
        (pad - left, pad - top),
        normalized_char,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )

    glyph_scale = max(0.75, min(1.15, float(profile.get("scale", 1.0))))
    if abs(glyph_scale - 1.0) > 1e-6:
        sw = max(1, int(round(layer.width * glyph_scale)))
        sh = max(1, int(round(layer.height * glyph_scale)))
        layer = layer.resize((sw, sh), Image.Resampling.LANCZOS)

    rotate_deg = float(profile.get("rotate", 0.0))
    if abs(rotate_deg) > 1e-6:
        layer = layer.rotate(rotate_deg, expand=True, resample=Image.Resampling.BICUBIC)

    return layer


def layout_vertical_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int],
    stroke_width: int,
    stroke_fill: Tuple[int, int, int, int] | None,
) -> Tuple[List[Dict[str, Any]], Tuple[int, int, int, int], int]:
    chars = [ch for ch in text.replace("\n", "")]
    if not chars:
        chars = [""]

    entries: List[Dict[str, Any]] = []
    cursor_y = 0.0
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for ch in chars:
        profile = _vertical_char_profile(ch)
        glyph = draw_vertical_char(ch, font, fill, stroke_width, stroke_fill, profile)
        x_off = float(profile.get("x", 0.0)) * font.size
        y_off = float(profile.get("y", 0.0)) * font.size
        advance = max(1, int(round(font.size * float(profile.get("advance", 1.12)))) )

        draw_x = x_off - glyph.width / 2.0
        draw_y = cursor_y + y_off
        entries.append({
            "char": ch,
            "glyph": glyph,
            "x": draw_x,
            "y": draw_y,
            "advance": advance,
        })

        vb = get_visible_bbox(glyph)
        if vb is None:
            gx0, gy0, gx1, gy1 = 0, 0, glyph.width, glyph.height
        else:
            gx0, gy0, gx1, gy1 = vb
        min_x = min(min_x, draw_x + gx0)
        min_y = min(min_y, draw_y + gy0)
        max_x = max(max_x, draw_x + gx1)
        max_y = max(max_y, draw_y + gy1)
        cursor_y += advance

    if not math.isfinite(min_x):
        min_x = 0.0
        min_y = 0.0
        max_x = float(font.size)
        max_y = float(font.size)

    visible_bbox = (
        int(math.floor(min_x)),
        int(math.floor(min_y)),
        int(math.ceil(max_x)),
        int(math.ceil(max_y)),
    )
    content_height = max(1, visible_bbox[3] - visible_bbox[1])
    return entries, visible_bbox, content_height


def create_vertical_text_layer(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int] = (255, 255, 255, 255),
    stroke_width: int = 0,
    stroke_fill: Tuple[int, int, int, int] | None = (0, 0, 0, 150),
    padding_x: int = TEXT_PADDING_X,
    padding_top: int = TEXT_PADDING_TOP,
    padding_bottom: int = TEXT_PADDING_BOTTOM,
    extra_padding: int = 0,
    text_scale_x: float = 1.0,
    text_scale_y: float = 1.0,
) -> Tuple[Image.Image, int, int, int]:
    entries, visible_bbox, _ = layout_vertical_text(
        text=text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )

    vx0, vy0, vx1, vy1 = visible_bbox
    content_w = max(1, vx1 - vx0)
    content_h = max(1, vy1 - vy0)

    layer_w = int(content_w + padding_x * 2 + extra_padding * 2)
    layer_h = int(content_h + padding_top + padding_bottom + extra_padding * 2)
    layer = Image.new("RGBA", (max(1, layer_w), max(1, layer_h)), (0, 0, 0, 0))

    target_center_x = layer.width / 2.0
    target_center_y = (padding_top + extra_padding) + (content_h / 2.0)
    visible_center_x = (vx0 + vx1) / 2.0
    visible_center_y = (vy0 + vy1) / 2.0
    shift_x = target_center_x - visible_center_x
    shift_y = target_center_y - visible_center_y

    for entry in entries:
        glyph = entry["glyph"]
        draw_x = int(round(entry["x"] + shift_x))
        draw_y = int(round(entry["y"] + shift_y))
        layer.alpha_composite(glyph, (draw_x, draw_y))

    content_top = padding_top + extra_padding
    sx = max(0.8, min(1.3, float(text_scale_x)))
    sy = max(0.8, min(1.3, float(text_scale_y)))
    if abs(sx - 1.0) > 1e-6 or abs(sy - 1.0) > 1e-6:
        scaled_width = max(1, int(round(layer.width * sx)))
        scaled_height = max(1, int(round(layer.height * sy)))
        layer = layer.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        content_w = max(1, int(round(content_w * sx)))
        content_h = max(1, int(round(content_h * sy)))
        content_top = int(round(content_top * sy))

    return layer, content_w, content_h, content_top


def _fit_base_text_layout(
    draw: ImageDraw.ImageDraw,
    seg: Segment,
) -> Tuple[str, int]:
    available_width = WIDTH - TEXT_MARGIN_LEFT - TEXT_MARGIN_RIGHT
    direction = _segment_text_direction(seg)
    scale_x, scale_y = _segment_scales(seg)
    safe_scale = max(1.0, _animation_safe_scale(seg.animation))
    if _normalize_animation_name(seg.animation) in ("huge_impact", "stretch_in", "shake_accent", "neon_flicker"):
        safe_scale = max(safe_scale, SAFE_SCALE)

    effective_scale_x = safe_scale * scale_x
    effective_scale_y = safe_scale * scale_y

    target_width = available_width / max(0.1, effective_scale_x)
    max_layer_height = (HEIGHT - TOP_SAFE_MARGIN - BOTTOM_SAFE_MARGIN) / max(0.1, effective_scale_y)
    glow_pad = GLOW_PADDING if _normalize_animation_name(seg.animation) == "neon_flicker" else 0
    min_font_size = max(MIN_FONT_SIZE, 48) if "\n" in seg.text else MIN_FONT_SIZE

    for size in range(seg.font_size, min_font_size - 1, -2):
        font = _load_font_for_segment(seg, size)
        if direction == "vertical":
            wrapped = seg.text.replace("\n", "")
        else:
            wrapped = _wrap_text_to_width(draw, seg.text, font, target_width)
        layer, _, _, _ = create_text_layer(
            wrapped,
            font,
            direction=direction,
            text_scale_x=scale_x,
            text_scale_y=scale_y,
            padding_x=TEXT_PADDING_X,
            padding_top=TEXT_PADDING_TOP,
            padding_bottom=TEXT_PADDING_BOTTOM,
            extra_padding=glow_pad,
        )
        vb = get_visible_bbox(layer)
        vis_w = (vb[2] - vb[0]) if vb else layer.width
        vis_h = (vb[3] - vb[1]) if vb else layer.height
        if vis_w * safe_scale <= available_width and vis_h * safe_scale <= max_layer_height:
            return wrapped, size

    # ここまでで収まらない場合は最小フォントで強制改行
    fallback_size = min_font_size
    fallback_font = _load_font_for_segment(seg, fallback_size)
    if direction == "vertical":
        wrapped = seg.text.replace("\n", "")
    else:
        wrapped = _wrap_text_to_width(draw, seg.text, fallback_font, target_width)
    return wrapped, fallback_size


def _calc_center_y(seg: Segment, text_height: int) -> int:
    if seg.emphasis == "impact":
        ratio = 0.48
    elif seg.emphasis == "strong":
        ratio = 0.50
    else:
        ratio = 0.52

    shift_up = 0
    threshold = int(HEIGHT * 0.30)
    if text_height > threshold:
        shift_up = min(120, int((text_height - threshold) * 0.35))

    return int(HEIGHT * ratio) - shift_up


def clamp_layer_position(
    x: float,
    y: float,
    layer_width: int,
    layer_height: int,
    canvas_width: int,
    canvas_height: int,
    margin_x: int = TEXT_MARGIN_LEFT,
    margin_top: int = TOP_SAFE_MARGIN,
    margin_bottom: int = BOTTOM_SAFE_MARGIN,
) -> Tuple[int, int]:
    min_x = margin_x
    max_x = canvas_width - margin_x - layer_width
    min_y = margin_top
    max_y = canvas_height - margin_bottom - layer_height

    if max_x < min_x:
        x = (canvas_width - layer_width) / 2
    else:
        x = min(max(x, min_x), max_x)

    if max_y < min_y:
        y = (canvas_height - layer_height) / 2
    else:
        y = min(max(y, min_y), max_y)

    return int(round(x)), int(round(y))


def get_visible_bbox(layer: Image.Image, alpha_threshold: int = 8) -> Tuple[int, int, int, int] | None:
    if layer.mode != "RGBA":
        layer = layer.convert("RGBA")
    alpha = np.array(layer.split()[-1])
    ys, xs = np.where(alpha > alpha_threshold)
    if len(xs) == 0 or len(ys) == 0:
        return None
    left = int(xs.min())
    top = int(ys.min())
    right = int(xs.max()) + 1
    bottom = int(ys.max()) + 1
    return left, top, right, bottom


def get_visible_center(layer: Image.Image, alpha_threshold: int = 8) -> Tuple[float, float]:
    bbox = get_visible_bbox(layer, alpha_threshold=alpha_threshold)
    if bbox is None:
        return layer.width / 2.0, layer.height / 2.0
    left, top, right, bottom = bbox
    return (left + right) / 2.0, (top + bottom) / 2.0


def _katakana_heavy(text: str) -> bool:
    chars = [ch for ch in text if not ch.isspace() and ch != "\n"]
    if not chars:
        return False
    kt = 0
    for ch in chars:
        code = ord(ch)
        if (0x30A0 <= code <= 0x30FF) or ch == "ー":
            kt += 1
    return (kt / max(1, len(chars))) >= 0.6


def _optical_correction(text: str, animation: str) -> Tuple[int, int]:
    anim = _normalize_animation_name(animation)
    if anim == "huge_impact":
        dy = -4
    elif anim == "label_reveal":
        dy = 4
    else:
        dy = 6

    dx = 0
    if _katakana_heavy(text):
        dx += 2
    if "ー" in text:
        dx += 1
    return dx, dy


def _debug_draw_rect_and_center(
    bg: Image.Image,
    visible_bbox_canvas: Tuple[int, int, int, int],
    target_center: Tuple[int, int],
    label_bbox: Tuple[int, int, int, int] | None = None,
) -> None:
    if not DEBUG_VISUAL:
        return
    draw = ImageDraw.Draw(bg)
    vx0, vy0, vx1, vy1 = visible_bbox_canvas
    draw.rectangle((vx0, vy0, vx1, vy1), outline=(255, 64, 64, 255), width=2)
    tx, ty = target_center
    draw.ellipse((tx - 4, ty - 4, tx + 4, ty + 4), fill=(64, 128, 255, 255))
    draw.ellipse((WIDTH // 2 - 4, HEIGHT // 2 - 4, WIDTH // 2 + 4, HEIGHT // 2 + 4), fill=(64, 255, 160, 255))
    if label_bbox is not None:
        lx0, ly0, lx1, ly1 = label_bbox
        draw.rectangle((lx0, ly0, lx1, ly1), outline=(64, 255, 64, 255), width=2)


def create_label_box_from_visible_text(
    text_layer: Image.Image,
    target_center_x: int,
    target_center_y: int,
    padding_x: int = 40,
    padding_y: int = 24,
    radius: int = 28,
) -> Tuple[int, int, int, int, int]:
    bbox = get_visible_bbox(text_layer)
    if bbox is None:
        vis_w = max(1, text_layer.width)
        vis_h = max(1, text_layer.height)
    else:
        vis_w = max(1, bbox[2] - bbox[0])
        vis_h = max(1, bbox[3] - bbox[1])

    label_w = int(vis_w + padding_x * 2)
    label_h = int(vis_h + padding_y * 2)
    x = int(round(target_center_x - label_w / 2))
    y = int(round(target_center_y - label_h / 2))
    x, y = clamp_layer_position(x, y, label_w, label_h, WIDTH, HEIGHT)
    return x, y, label_w, label_h, radius


def create_text_layer(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int] = (255, 255, 255, 255),
    stroke_width: int = 0,
    stroke_fill: Tuple[int, int, int, int] | None = (0, 0, 0, 150),
    padding_x: int = TEXT_PADDING_X,
    padding_top: int = TEXT_PADDING_TOP,
    padding_bottom: int = TEXT_PADDING_BOTTOM,
    line_spacing: int | None = None,
    extra_padding: int = 0,
    direction: str = "horizontal",
    text_scale_x: float = 1.0,
    text_scale_y: float = 1.0,
) -> Tuple[Image.Image, int, int, int]:
    direction_mode = "vertical" if direction in ("vertical", "縦書き") else "horizontal"
    lines = text.split("\n") if text else [""]

    if line_spacing is None:
        line_spacing = max(LINE_SPACING, int(font.size * 0.25))

    if direction_mode == "vertical":
        return create_vertical_text_layer(
            text=text,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
            padding_x=padding_x,
            padding_top=padding_top,
            padding_bottom=padding_bottom,
            extra_padding=extra_padding,
            text_scale_x=text_scale_x,
            text_scale_y=text_scale_y,
        )
    else:
        dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dummy)
        bboxes: List[Tuple[int, int, int, int]] = []
        line_widths: List[int] = []
        line_heights: List[int] = []
        for line in lines:
            bbox = dd.textbbox((0, 0), line, font=font, stroke_width=stroke_width)
            bboxes.append((int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])))
            line_widths.append(int(bbox[2] - bbox[0]))
            line_heights.append(int(bbox[3] - bbox[1]))

        text_width = max(1, max(line_widths) if line_widths else 1)
        text_height = max(1, sum(line_heights) + line_spacing * max(0, len(lines) - 1))

        layer_width = int(text_width + padding_x * 2 + extra_padding * 2)
        layer_height = int(text_height + padding_top + padding_bottom + extra_padding * 2)
        layer = Image.new("RGBA", (max(1, layer_width), max(1, layer_height)), (0, 0, 0, 0))
        layer_draw = ImageDraw.Draw(layer)

        y = padding_top + extra_padding
        start_x = padding_x + extra_padding
        for i, line in enumerate(lines):
            bbox = bboxes[i]
            line_width = line_widths[i]
            x = start_x + (text_width - line_width) / 2 - bbox[0]
            draw_y = y - bbox[1]
            layer_draw.text(
                (x, draw_y),
                line,
                font=font,
                fill=fill,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
            y += line_heights[i] + line_spacing

        content_top = padding_top + extra_padding

    sx = max(0.8, min(1.3, float(text_scale_x)))
    sy = max(0.8, min(1.3, float(text_scale_y)))
    if abs(sx - 1.0) > 1e-6 or abs(sy - 1.0) > 1e-6:
        scaled_width = max(1, int(round(layer.width * sx)))
        scaled_height = max(1, int(round(layer.height * sy)))
        layer = layer.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        text_width = max(1, int(round(text_width * sx)))
        text_height = max(1, int(round(text_height * sy)))
        content_top = int(round(content_top * sy))

    return layer, text_width, text_height, content_top


def _create_main_text_layer(
    text: str,
    font: ImageFont.FreeTypeFont,
    text_rgba: Tuple[int, int, int, int],
    shadow_rgba: Tuple[int, int, int, int] | None = None,
    glow_padding: int = 0,
    direction: str = "horizontal",
    text_scale_x: float = 1.0,
    text_scale_y: float = 1.0,
) -> Tuple[Image.Image, int, int, int]:
    stroke_w = 0
    stroke_fill = None
    if shadow_rgba is not None:
        stroke_w = 2
        stroke_fill = shadow_rgba
    return create_text_layer(
        text,
        font,
        fill=text_rgba,
        stroke_width=stroke_w,
        stroke_fill=stroke_fill,
        padding_x=TEXT_PADDING_X,
        padding_top=TEXT_PADDING_TOP,
        padding_bottom=TEXT_PADDING_BOTTOM,
        extra_padding=glow_padding,
        direction=direction,
        text_scale_x=text_scale_x,
        text_scale_y=text_scale_y,
    )


def _estimate_preview_font_size(text: str) -> int:
    n = len(text.replace("\n", "").strip())
    if n <= 6:
        return 120
    if n <= 12:
        return 96
    if n <= 24:
        return 76
    return 58


def create_style_preview_image(
    text: str,
    font_path: str,
    text_scale_x: float = 1.0,
    text_scale_y: float = 1.0,
    text_direction: str = "横書き",
    canvas_width: int = 1080,
    canvas_height: int = 1920,
) -> Image.Image:
    preview_text = (text or "").strip()
    if not preview_text:
        raise ValueError("empty_preview_text")

    font_file = Path(font_path)
    if not font_file.exists():
        raise FileNotFoundError(str(font_file))

    direction = "vertical" if text_direction in ("縦書き", "vertical") else "horizontal"
    scale_x = max(0.8, min(1.3, float(text_scale_x)))
    scale_y = max(0.8, min(1.3, float(text_scale_y)))

    image = Image.new("RGBA", (canvas_width, canvas_height), (*BG_COLOR_RGB, 255))

    margin_x = 80
    margin_top = 120
    margin_bottom = 120
    max_width = canvas_width - margin_x * 2
    max_height = canvas_height - margin_top - margin_bottom

    probe = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)

    base_size = _estimate_preview_font_size(preview_text)
    chosen_layer: Image.Image | None = None
    chosen_vis_h = 0

    for size in range(base_size, 27, -2):
        font = ImageFont.truetype(str(font_file), size)
        if direction == "vertical":
            rendered_text = preview_text.replace("\n", "")
        else:
            wrapped = _wrap_text_to_width(draw, preview_text, font, max_width / max(0.8, scale_x))
            rendered_text = wrapped

        layer, _, _, _ = create_text_layer(
            rendered_text,
            font,
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 150),
            padding_x=TEXT_PADDING_X,
            padding_top=TEXT_PADDING_TOP,
            padding_bottom=TEXT_PADDING_BOTTOM,
            direction=direction,
            text_scale_x=scale_x,
            text_scale_y=scale_y,
        )
        vb = get_visible_bbox(layer)
        vis_w = (vb[2] - vb[0]) if vb else layer.width
        vis_h = (vb[3] - vb[1]) if vb else layer.height
        if vis_w <= max_width and vis_h <= max_height:
            chosen_layer = layer
            chosen_vis_h = vis_h
            break

    if chosen_layer is None:
        font = ImageFont.truetype(str(font_file), 28)
        rendered_text = preview_text.replace("\n", "") if direction == "vertical" else preview_text
        chosen_layer, _, _, _ = create_text_layer(
            rendered_text,
            font,
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 150),
            padding_x=TEXT_PADDING_X,
            padding_top=TEXT_PADDING_TOP,
            padding_bottom=TEXT_PADDING_BOTTOM,
            direction=direction,
            text_scale_x=scale_x,
            text_scale_y=scale_y,
        )
        vb = get_visible_bbox(chosen_layer)
        chosen_vis_h = (vb[3] - vb[1]) if vb else chosen_layer.height

    temp_seg = Segment(
        index=0,
        text=preview_text,
        emphasis="normal",
        duration=1.8,
        font_size=base_size,
        animation="letter_fade",
    )

    center_y = _calc_center_y(temp_seg, chosen_vis_h)
    _apply_layer(image, chosen_layer, canvas_width // 2, center_y)
    return image


def _apply_layer(
    bg: Image.Image,
    layer: Image.Image,
    center_x: int,
    center_y: int,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    opacity: float = 1.0,
    offset_x: int = 0,
    offset_y: int = 0,
) -> Tuple[int, int, int, int]:
    sx = max(1, int(layer.width * max(0.05, scale_x)))
    sy = max(1, int(layer.height * max(0.05, scale_y)))

    resized = layer.resize((sx, sy), Image.Resampling.BICUBIC)
    if opacity < 1.0:
        alpha = resized.split()[-1].point(lambda p: int(p * max(0.0, min(1.0, opacity))))
        resized.putalpha(alpha)

    vb = get_visible_bbox(resized)
    if vb is None:
        vb = (0, 0, sx, sy)
    vl, vt, vr, vbm = vb
    vcx = (vl + vr) / 2.0
    vcy = (vt + vbm) / 2.0

    x = center_x - vcx + offset_x
    y = center_y - vcy + offset_y

    min_vis_x = TEXT_MARGIN_LEFT
    max_vis_x = WIDTH - TEXT_MARGIN_RIGHT
    min_vis_y = TOP_SAFE_MARGIN
    max_vis_y = HEIGHT - BOTTOM_SAFE_MARGIN

    cur_left = x + vl
    cur_right = x + vr
    cur_top = y + vt
    cur_bottom = y + vbm

    if cur_left < min_vis_x:
        x += min_vis_x - cur_left
    if cur_right > max_vis_x:
        x -= cur_right - max_vis_x
    if cur_top < min_vis_y:
        y += min_vis_y - cur_top
    if cur_bottom > max_vis_y:
        y -= cur_bottom - max_vis_y

    x = int(round(x))
    y = int(round(y))
    bg.alpha_composite(resized, (x, y))

    visible_bbox_canvas = (x + vl, y + vt, x + vr, y + vbm)
    _debug_draw_rect_and_center(bg, visible_bbox_canvas, (center_x, center_y))
    return visible_bbox_canvas


def _layout_chars(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    seg: Segment,
) -> List[Tuple[str, int, int, int]]:
    scale_x, scale_y = _segment_scales(seg)
    lines = text.split("\n")
    ascent, descent = font.getmetrics()
    line_h = max(1, int(round((ascent + descent) * scale_y)))
    line_spacing = max(LINE_SPACING, int(font.size * 0.25))
    total_h = max(1, len(lines) * line_h + max(0, len(lines) - 1) * line_spacing)

    dx, dy = _optical_correction(text, seg.animation)
    block_center_y = _calc_center_y(seg, total_h) + dy
    block_top = int(round(block_center_y - total_h / 2.0))

    positions: List[Tuple[str, int, int, int]] = []
    y = block_top
    for line in lines:
        advances: List[int] = []
        for ch in line:
            adv = int(round(draw.textlength(ch, font=font) * scale_x))
            if adv <= 0:
                adv = max(1, int(round(font.size * (0.35 if ch.isspace() else 0.52) * scale_x)))
            advances.append(adv)

        line_w = sum(advances)
        line_visual_dx = 0.0
        if line:
            line_layer, _, _, _ = create_text_layer(
                line,
                font,
                fill=(255, 255, 255, 255),
                stroke_width=1,
                stroke_fill=(0, 0, 0, 150),
                padding_x=20,
                padding_top=12,
                padding_bottom=16,
                line_spacing=line_spacing,
                text_scale_x=scale_x,
                text_scale_y=scale_y,
            )
            lcx, _ = get_visible_center(line_layer)
            line_visual_dx = lcx - (line_layer.width / 2.0)

        x = int(round((WIDTH - line_w) / 2.0 - line_visual_dx)) + dx
        for ch in line:
            adv = int(round(draw.textlength(ch, font=font) * scale_x))
            if adv <= 0:
                adv = max(1, int(round(font.size * (0.35 if ch.isspace() else 0.52) * scale_x)))
            positions.append((ch, x, y, adv))
            x += adv
        y += line_h + line_spacing

    return positions


def _draw_char_layer(
    img: Image.Image,
    ch: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    alpha: int = 255,
    offset_x: int = 0,
    offset_y: int = 0,
    advance: int | None = None,
    text_scale_x: float = 1.0,
    text_scale_y: float = 1.0,
) -> None:
    a, d = font.getmetrics()
    line_h = max(1, int(round((a + d) * text_scale_y)))
    dummy = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dummy)
    bbox = dd.textbbox((0, 0), ch, font=font, stroke_width=1)
    over_top = max(0, -int(bbox[1]))
    over_bottom = max(0, int(bbox[3]) - line_h)

    adv = advance if advance is not None else int(round(dd.textlength(ch, font=font)))
    if adv <= 0:
        adv = max(1, int(round(font.size * (0.35 if ch.isspace() else 0.52))))

    pad_x = max(8, int(round(12 * text_scale_x)))
    pad_top = 8 + over_top
    pad_bottom = 10 + over_bottom
    layer_w = max(1, adv + pad_x * 2)
    layer_h = max(1, line_h + pad_top + pad_bottom)
    ch_layer = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(ch_layer)
    ldraw.text(
        (pad_x, pad_top),
        ch,
        font=font,
        fill=(255, 255, 255, max(0, min(255, alpha))),
        stroke_width=1,
        stroke_fill=(0, 0, 0, min(150, alpha)),
    )

    sx = max(0.8, min(1.3, float(text_scale_x)))
    sy = max(0.8, min(1.3, float(text_scale_y)))
    if abs(sx - 1.0) > 1e-6 or abs(sy - 1.0) > 1e-6:
        sw = max(1, int(round(ch_layer.width * sx)))
        sh = max(1, int(round(ch_layer.height * sy)))
        ch_layer = ch_layer.resize((sw, sh), Image.Resampling.LANCZOS)

    center_x = int(round(x + adv / 2.0)) + offset_x
    center_y = int(round(y + line_h / 2.0)) + offset_y
    _apply_layer(img, ch_layer, center_x, center_y)


def render_huge_impact(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    p = frame_idx / max(1, total_frames - 1)
    if p < 0.55:
        scale = 0.78 + (1.12 - 0.78) * ease_out_back(p / 0.55)
    elif p < 0.80:
        scale = 1.12 - (1.12 - 1.0) * ease_in_out_cubic((p - 0.55) / 0.25)
    else:
        scale = 1.0

    opacity = min(1.0, p / 0.20)
    if p > 0.88:
        opacity *= 1.0 - 0.20 * ((p - 0.88) / 0.12)

    layer, _, th, _ = _create_main_text_layer(
        text,
        font,
        (*TEXT_COLOR, 255),
        shadow_rgba=(0, 0, 0, 150),
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    vb = get_visible_bbox(layer)
    vis_h = (vb[3] - vb[1]) if vb else th
    dx, dy = _optical_correction(text, seg.animation)
    center_y = _calc_center_y(seg, vis_h) + dy
    _apply_layer(img, layer, WIDTH // 2 + dx, center_y, scale, scale, opacity)


def render_stretch_in(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    p = frame_idx / max(1, total_frames - 1)
    if p < 0.60:
        scale_x = 0.45 + (1.12 - 0.45) * ease_out_cubic(p / 0.60)
    elif p < 0.82:
        scale_x = 1.12 - (1.12 - 1.0) * ease_in_out_cubic((p - 0.60) / 0.22)
    else:
        scale_x = 1.0

    opacity = min(1.0, p / 0.25)

    layer, tw, th, _ = _create_main_text_layer(
        text,
        font,
        (*TEXT_COLOR, 255),
        shadow_rgba=(0, 0, 0, 140),
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    available_width = WIDTH - TEXT_MARGIN_LEFT - TEXT_MARGIN_RIGHT
    content_w = max(1, tw)
    if content_w * scale_x > available_width:
        scale_x = available_width / content_w

    vb = get_visible_bbox(layer)
    vis_h = (vb[3] - vb[1]) if vb else th
    dx, dy = _optical_correction(text, seg.animation)
    center_y = _calc_center_y(seg, vis_h) + dy
    _apply_layer(img, layer, WIDTH // 2 + dx, center_y, scale_x=scale_x, scale_y=1.0, opacity=opacity)


def render_label_reveal(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    p = frame_idx / max(1, total_frames - 1)
    text_layer, tw, th, _ = _create_main_text_layer(
        text,
        font,
        (255, 255, 255, 255),
        shadow_rgba=(0, 0, 0, 140),
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    px = int(font.size * 0.45)
    py = int(font.size * 0.30)

    reveal = ease_out_cubic(min(1.0, p / 0.55))
    dx, dy = _optical_correction(text, seg.animation)
    vb = get_visible_bbox(text_layer)
    vis_h = (vb[3] - vb[1]) if vb else th
    center_x = WIDTH // 2 + dx
    center_y = _calc_center_y(seg, vis_h) + dy
    lx, ly, full_w, full_h, radius = create_label_box_from_visible_text(
        text_layer,
        center_x,
        center_y,
        padding_x=px,
        padding_y=py,
        radius=26,
    )

    label_w = max(2, int(full_w * reveal))
    x = lx + (full_w - label_w) // 2
    y = ly
    label_color = (36, 52, 110, 255)
    draw.rounded_rectangle((x, y, x + label_w, y + full_h), radius=radius, fill=label_color)
    if DEBUG_VISUAL:
        _debug_draw_rect_and_center(img, (center_x - 1, center_y - 1, center_x + 1, center_y + 1), (center_x, center_y), (lx, ly, lx + full_w, ly + full_h))

    text_alpha = int(255 * max(0.0, min(1.0, (p - 0.20) / 0.45)))
    if text_alpha > 0:
        _apply_layer(img, text_layer, center_x, center_y, opacity=text_alpha / 255.0)


def render_soft_pop(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    p = frame_idx / max(1, total_frames - 1)

    # Soft Pop: やわらかく拡大してから自然に等倍へ戻す
    if p < 0.58:
        scale = 0.92 + (1.06 - 0.92) * ease_out_cubic(p / 0.58)
    elif p < 0.82:
        scale = 1.06 - (1.06 - 1.0) * ease_in_out_cubic((p - 0.58) / 0.24)
    else:
        scale = 1.0

    opacity = min(1.0, p / 0.18)

    layer, _, th, _ = _create_main_text_layer(
        text,
        font,
        (*TEXT_COLOR, 255),
        shadow_rgba=(0, 0, 0, 140),
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    vb = get_visible_bbox(layer)
    vis_h = (vb[3] - vb[1]) if vb else th
    dx, dy = _optical_correction(text, seg.animation)
    center_y = _calc_center_y(seg, vis_h) + dy
    _apply_layer(img, layer, WIDTH // 2 + dx, center_y, scale, scale, opacity)


def render_block_reveal(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    p = frame_idx / max(1, total_frames - 1)
    reveal_progress = ease_out_cubic(min(1.0, p / 0.65))
    block_progress = ease_out_cubic(min(1.0, p / 0.82))

    text_layer, tw, th, _ = _create_main_text_layer(
        text,
        font,
        (*TEXT_COLOR, 255),
        shadow_rgba=(0, 0, 0, 140),
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    vb = get_visible_bbox(text_layer)
    vis_w = (vb[2] - vb[0]) if vb else max(1, tw)
    vis_h = (vb[3] - vb[1]) if vb else max(1, th)
    dx, dy = _optical_correction(text, seg.animation)
    center_x = WIDTH // 2 + dx
    center_y = _calc_center_y(seg, vis_h) + dy

    reveal_mask = Image.new("L", (text_layer.width, text_layer.height), 0)
    md = ImageDraw.Draw(reveal_mask)
    if direction == "vertical":
        reveal_h = int(text_layer.height * reveal_progress)
        md.rectangle((0, 0, text_layer.width, reveal_h), fill=255)
    else:
        reveal_w = int(text_layer.width * reveal_progress)
        md.rectangle((0, 0, reveal_w, text_layer.height), fill=255)

    revealed = Image.new("RGBA", text_layer.size, (0, 0, 0, 0))
    revealed.paste(text_layer, (0, 0), reveal_mask)
    _apply_layer(img, revealed, center_x, center_y, opacity=1.0)

    block_alpha = 235
    if p > 0.86:
        block_alpha = int(max(0, 235 * (1.0 - (p - 0.86) / 0.14)))
    if block_alpha <= 0:
        return

    block_color = (17, 24, 39, block_alpha)
    if direction == "vertical":
        block_w = max(24, int(vis_w * 1.35))
        block_h = max(24, int(vis_h * 0.40))
        travel = vis_h + block_h * 2
        top_start = center_y - vis_h // 2 - block_h
        block_x = center_x - block_w // 2
        block_y = int(round(top_start + travel * block_progress))
    else:
        block_w = max(24, int(vis_w * 0.40))
        block_h = max(24, int(vis_h * 1.35))
        travel = vis_w + block_w * 2
        left_start = center_x - vis_w // 2 - block_w
        block_x = int(round(left_start + travel * block_progress))
        block_y = center_y - block_h // 2

    radius = max(8, int(min(block_w, block_h) * 0.14))
    block_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    bd = ImageDraw.Draw(block_layer)
    bd.rounded_rectangle(
        (block_x, block_y, block_x + block_w, block_y + block_h),
        radius=radius,
        fill=block_color,
    )
    img.alpha_composite(block_layer)


def render_terminal_type(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    p = frame_idx / max(1, total_frames - 1)
    reveal_ratio = min(1.0, p / 0.72)

    total_chars = max(1, len(text))
    visible_count = min(total_chars, int(math.floor(total_chars * reveal_ratio)))
    visible_text = text[:visible_count]

    cursor_on = ((frame_idx // max(1, FPS // 4)) % 2) == 0
    cursor = "｜" if direction == "vertical" else "▌"
    if cursor_on and visible_count < total_chars:
        visible_text += cursor
    elif cursor_on and visible_count >= total_chars:
        visible_text += cursor

    layer, _, th, _ = _create_main_text_layer(
        visible_text,
        font,
        (240, 255, 240, 255),
        shadow_rgba=(0, 0, 0, 150),
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    vb = get_visible_bbox(layer)
    vis_h = (vb[3] - vb[1]) if vb else th
    dx, dy = _optical_correction(visible_text or text, seg.animation)
    center_y = _calc_center_y(seg, vis_h) + dy
    _apply_layer(img, layer, WIDTH // 2 + dx, center_y, opacity=1.0)


def render_color_shift(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    t = frame_idx / max(1, FPS)
    hue = (t * 0.25) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
    fill = (int(r * 255), int(g * 255), int(b * 255), 255)

    layer, _, th, _ = _create_main_text_layer(
        text,
        font,
        fill,
        shadow_rgba=(0, 0, 0, 145),
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    vb = get_visible_bbox(layer)
    vis_h = (vb[3] - vb[1]) if vb else th
    dx, dy = _optical_correction(text, seg.animation)
    center_y = _calc_center_y(seg, vis_h) + dy
    _apply_layer(img, layer, WIDTH // 2 + dx, center_y, opacity=1.0)


def render_focus_in(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    p = frame_idx / max(1, total_frames - 1)
    progress = ease_out_cubic(min(1.0, p / 0.45))
    blur_radius = max(0.0, (1.0 - progress) * 18.0)
    scale = 1.08 - 0.08 * progress
    opacity = 0.28 + 0.72 * progress

    text_layer, _, th, _ = create_text_layer(
        text,
        font,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 150),
        padding_x=TEXT_PADDING_X,
        padding_top=TEXT_PADDING_TOP,
        padding_bottom=TEXT_PADDING_BOTTOM,
        extra_padding=60,
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )

    base_vb = get_visible_bbox(text_layer)
    vis_h = (base_vb[3] - base_vb[1]) if base_vb else th

    layer = text_layer
    if blur_radius > 0.05:
        layer = layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    dx, dy = _optical_correction(text, seg.animation)
    center_y = _calc_center_y(seg, vis_h) + dy
    _apply_layer(img, layer, WIDTH // 2 + dx, center_y, scale, scale, opacity)


def render_letter_fade(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    if direction == "vertical":
        p = frame_idx / max(1, total_frames - 1)
        layer, _, th, _ = _create_main_text_layer(
            text,
            font,
            (*TEXT_COLOR, 255),
            shadow_rgba=(0, 0, 0, 130),
            direction=direction,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )
        vb = get_visible_bbox(layer)
        vis_h = (vb[3] - vb[1]) if vb else th
        dx, dy = _optical_correction(text, seg.animation)
        center_y = _calc_center_y(seg, vis_h) + dy
        opacity = min(1.0, max(0.0, p / 0.25))
        y_off = int(18 * (1.0 - opacity))
        _apply_layer(img, layer, WIDTH // 2 + dx, center_y, opacity=opacity, offset_y=y_off)
        return

    chars = _layout_chars(draw, text, font, seg)
    count = max(1, len(chars))
    max_delay_range = max(1, int(total_frames * 0.60))
    step = max(1, min(int(0.05 * FPS), max_delay_range // max(1, count - 1)))
    appear_frames = max(4, int(0.18 * FPS))

    for i, (ch, x, y, adv) in enumerate(chars):
        start = i * step
        lt = (frame_idx - start) / appear_frames
        if lt <= 0.0:
            continue
        t = max(0.0, min(1.0, lt))
        alpha = int(255 * ease_out_cubic(t))
        y_off = int(14 * (1.0 - t))
        _draw_char_layer(
            img,
            ch,
            font,
            x,
            y,
            alpha=alpha,
            offset_y=y_off,
            advance=adv,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )


def render_shake_accent(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    p = frame_idx / max(1, total_frames - 1)
    pop = min(1.0, p / 0.35)
    scale = 0.90 + (1.06 - 0.90) * ease_out_back(pop)
    if p > 0.42:
        scale = 1.0

    shake_start = 0.44
    shake_end = min(0.92, shake_start + min(0.40, max(0.20, seg.duration * 0.18)) / seg.duration)
    x_off = 0
    if shake_start <= p <= shake_end:
        local = (p - shake_start) / max(1e-6, (shake_end - shake_start))
        amp = 8 * (1.0 - 0.25 * local)
        x_off = int(round(amp * math.sin(local * math.pi * 12)))

    opacity = min(1.0, p / 0.16)
    layer, _, th, _ = _create_main_text_layer(
        text,
        font,
        (*TEXT_COLOR, 255),
        shadow_rgba=(0, 0, 0, 150),
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    vb = get_visible_bbox(layer)
    vis_h = (vb[3] - vb[1]) if vb else th
    dx, dy = _optical_correction(text, seg.animation)
    center_y = _calc_center_y(seg, vis_h) + dy
    _apply_layer(img, layer, WIDTH // 2 + dx, center_y, scale, scale, opacity, offset_x=x_off)


def render_typewriter(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    if direction == "vertical":
        chars = [ch for ch in text.replace("\n", "")]
        total_chars = max(1, len(chars))
        reveal_ratio = min(1.0, (frame_idx + 1) / max(1, int(total_frames * 0.90)))
        visible = min(total_chars, int(math.ceil(total_chars * reveal_ratio)))
        visible_text = "".join(chars[:visible])
        layer, _, th, _ = _create_main_text_layer(
            visible_text,
            font,
            (*TEXT_COLOR, 255),
            shadow_rgba=(0, 0, 0, 130),
            direction=direction,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )
        vb = get_visible_bbox(layer)
        vis_h = (vb[3] - vb[1]) if vb else th
        dx, dy = _optical_correction(visible_text or text, seg.animation)
        center_y = _calc_center_y(seg, vis_h) + dy
        _apply_layer(img, layer, WIDTH // 2 + dx, center_y, opacity=1.0)
        return

    chars = _layout_chars(draw, text, font, seg)
    count = max(1, len(chars))
    reveal_ratio = min(1.0, (frame_idx + 1) / max(1, int(total_frames * 0.90)))
    visible = min(count, int(math.ceil(count * reveal_ratio)))

    for i, (ch, x, y, adv) in enumerate(chars):
        if i >= visible:
            break
        _draw_char_layer(
            img,
            ch,
            font,
            x,
            y,
            alpha=255,
            advance=adv,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )

    if visible < count and (frame_idx // 6) % 2 == 0:
        a, d = font.getmetrics()
        line_h = max(1, a + d)
        if visible > 0:
            last_ch, last_x, last_y, last_adv = chars[visible - 1]
            cx = int(round(last_x + last_adv + 2))
            cy = int(round(last_y + 4))
        else:
            dx, dy = _optical_correction(text, seg.animation)
            cy = int(round(_calc_center_y(seg, line_h) + dy - line_h / 2 + 4))
            cx = WIDTH // 2 + dx
        draw.line((cx, cy, cx, cy + line_h - 8), fill=(255, 255, 255, 230), width=3)


def render_letter_drop(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    if direction == "vertical":
        p = frame_idx / max(1, total_frames - 1)
        layer, _, th, _ = _create_main_text_layer(
            text,
            font,
            (*TEXT_COLOR, 255),
            shadow_rgba=(0, 0, 0, 130),
            direction=direction,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )
        vb = get_visible_bbox(layer)
        vis_h = (vb[3] - vb[1]) if vb else th
        dx, dy = _optical_correction(text, seg.animation)
        center_y = _calc_center_y(seg, vis_h) + dy
        et = ease_out_back(min(1.0, p / 0.65))
        y_off = int(-60 * (1.0 - et))
        alpha = min(1.0, p / 0.22)
        _apply_layer(img, layer, WIDTH // 2 + dx, center_y, opacity=alpha, offset_y=y_off)
        return

    chars = _layout_chars(draw, text, font, seg)
    step = max(1, int(0.04 * FPS))
    anim_frames = max(6, int(0.24 * FPS))
    for i, (ch, x, y, adv) in enumerate(chars):
        t = (frame_idx - i * step) / anim_frames
        if t <= 0:
            continue
        t = max(0.0, min(1.0, t))
        et = ease_out_back(t)
        y_off = int(-80 * (1.0 - et))
        alpha = int(255 * ease_out_cubic(t))
        _draw_char_layer(
            img,
            ch,
            font,
            x,
            y,
            alpha=alpha,
            offset_y=y_off,
            advance=adv,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )


def render_letter_rise(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    if direction == "vertical":
        p = frame_idx / max(1, total_frames - 1)
        layer, _, th, _ = _create_main_text_layer(
            text,
            font,
            (*TEXT_COLOR, 255),
            shadow_rgba=(0, 0, 0, 130),
            direction=direction,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )
        vb = get_visible_bbox(layer)
        vis_h = (vb[3] - vb[1]) if vb else th
        dx, dy = _optical_correction(text, seg.animation)
        center_y = _calc_center_y(seg, vis_h) + dy
        et = ease_out_cubic(min(1.0, p / 0.65))
        y_off = int(60 * (1.0 - et))
        alpha = min(1.0, p / 0.22)
        _apply_layer(img, layer, WIDTH // 2 + dx, center_y, opacity=alpha, offset_y=y_off)
        return

    chars = _layout_chars(draw, text, font, seg)
    step = max(1, int(0.04 * FPS))
    anim_frames = max(8, int(0.26 * FPS))
    for i, (ch, x, y, adv) in enumerate(chars):
        t = (frame_idx - i * step) / anim_frames
        if t <= 0:
            continue
        t = max(0.0, min(1.0, t))
        et = ease_out_cubic(t)
        y_off = int(80 * (1.0 - et))
        alpha = int(255 * et)
        _draw_char_layer(
            img,
            ch,
            font,
            x,
            y,
            alpha=alpha,
            offset_y=y_off,
            advance=adv,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )


def render_hacker_text(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    if direction == "vertical":
        chars = [ch for ch in text.replace("\n", "")]
        total_chars = max(1, len(chars))
        reveal = int(round(ease_in_out_cubic(frame_idx / max(1, total_frames - 1)) * total_chars))
        out_chars: List[str] = []
        for i, target in enumerate(chars):
            if i < reveal or target.isspace():
                out_chars.append(target)
            else:
                idx = (frame_idx * 7 + i * 13) % len(HACKER_CHARSET)
                out_chars.append(HACKER_CHARSET[idx])
        out_text = "".join(out_chars)
        layer, _, th, _ = _create_main_text_layer(
            out_text,
            font,
            (*TEXT_COLOR, 255),
            shadow_rgba=(0, 0, 0, 130),
            direction=direction,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )
        vb = get_visible_bbox(layer)
        vis_h = (vb[3] - vb[1]) if vb else th
        dx, dy = _optical_correction(out_text or text, seg.animation)
        center_y = _calc_center_y(seg, vis_h) + dy
        _apply_layer(img, layer, WIDTH // 2 + dx, center_y, opacity=1.0)
        return

    chars = _layout_chars(draw, text, font, seg)
    count = max(1, len(chars))
    reveal = int(round(ease_in_out_cubic(frame_idx / max(1, total_frames - 1)) * count))

    for i, (target, x, y, adv) in enumerate(chars):
        if i < reveal or target.isspace():
            out_ch = target
        else:
            idx = (frame_idx * 7 + i * 13) % len(HACKER_CHARSET)
            out_ch = HACKER_CHARSET[idx]
        _draw_char_layer(
            img,
            out_ch,
            font,
            x,
            y,
            alpha=255,
            advance=adv,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )


def render_neon_flicker(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    p = frame_idx / max(1, total_frames - 1)
    layer, _, th, _ = _create_main_text_layer(
        text,
        font,
        (255, 255, 255, 255),
        shadow_rgba=(0, 0, 0, 120),
        glow_padding=GLOW_PADDING,
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    vb = get_visible_bbox(layer)
    vis_h = (vb[3] - vb[1]) if vb else th
    dx, dy = _optical_correction(text, seg.animation)
    center_y = _calc_center_y(seg, vis_h) + dy

    intensity = 1.0
    if 0.20 <= p <= 0.50:
        seq = [0.28, 1.0, 0.42, 1.0, 0.66, 1.0, 0.80, 1.0]
        idx = min(len(seq) - 1, int(((p - 0.20) / 0.30) * len(seq)))
        intensity = seq[idx]

    glow, _, _, _ = _create_main_text_layer(
        text,
        font,
        (102, 220, 255, int(170 * intensity)),
        shadow_rgba=(102, 220, 255, int(120 * intensity)),
        glow_padding=GLOW_PADDING,
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=6))
    _apply_layer(img, glow, WIDTH // 2 + dx, center_y, opacity=min(1.0, 0.95 * intensity))
    _apply_layer(img, layer, WIDTH // 2 + dx, center_y, opacity=max(0.55, intensity))


def render_no_effect(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    seg: Segment,
    text: str,
    font: ImageFont.FreeTypeFont,
    frame_idx: int,
    total_frames: int,
) -> None:
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)
    layer, _, th, _ = _create_main_text_layer(
        text,
        font,
        (*TEXT_COLOR, 255),
        shadow_rgba=(0, 0, 0, 140),
        direction=direction,
        text_scale_x=scale_x_style,
        text_scale_y=scale_y_style,
    )
    vb = get_visible_bbox(layer)
    vis_h = (vb[3] - vb[1]) if vb else th
    dx, dy = _optical_correction(text, seg.animation)
    center_y = _calc_center_y(seg, vis_h) + dy
    _apply_layer(img, layer, WIDTH // 2 + dx, center_y, opacity=1.0)


ANIMATION_RENDERERS = {
    "no_effect": render_no_effect,
    "huge_impact": render_huge_impact,
    "stretch_in": render_stretch_in,
    "label_reveal": render_label_reveal,
    "soft_pop": render_soft_pop,
    "block_reveal": render_block_reveal,
    "terminal_type": render_terminal_type,
    "color_shift": render_color_shift,
    "focus_in": render_focus_in,
    "letter_fade": render_letter_fade,
    "shake_accent": render_shake_accent,
    "typewriter": render_typewriter,
    "letter_drop": render_letter_drop,
    "letter_rise": render_letter_rise,
    "hacker_text": render_hacker_text,
    "neon_flicker": render_neon_flicker,
}


def _draw_text_frame(
    seg: Segment,
    params: FrameParams,
    frame_idx: int,
    total_frames: int,
) -> np.ndarray:
    """1フレーム分のRGBA Pillowイメージを生成し、numpy配列(BGR)で返す。"""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (*BG_COLOR_RGB, 255))
    draw = ImageDraw.Draw(img)

    wrapped_base_text, base_font_size = _fit_base_text_layout(draw, seg)

    base_font = _load_font_for_segment(seg, base_font_size)
    animation = _normalize_animation_name(seg.animation)
    renderer = ANIMATION_RENDERERS.get(animation)
    direction = _segment_text_direction(seg)
    scale_x_style, scale_y_style = _segment_scales(seg)

    if renderer is None:
        font_size = max(12, int(base_font_size * params.scale))
        font = _load_font_for_segment(seg, font_size)
        layer, _, th, _ = _create_main_text_layer(
            wrapped_base_text,
            font,
            (*TEXT_COLOR, 255),
            shadow_rgba=(0, 0, 0, 120),
            direction=direction,
            text_scale_x=scale_x_style,
            text_scale_y=scale_y_style,
        )
        vb = get_visible_bbox(layer)
        vis_h = (vb[3] - vb[1]) if vb else th
        dx, dy = _optical_correction(wrapped_base_text, seg.animation)
        center_y = _calc_center_y(seg, vis_h) + dy
        _apply_layer(
            img,
            layer,
            WIDTH // 2 + dx,
            center_y,
            opacity=max(0.0, min(1.0, params.opacity)),
            offset_y=params.y_offset,
        )
    else:
        renderer(img, draw, seg, wrapped_base_text, base_font, frame_idx, total_frames)

    # RGBA → BGR (OpenCV)
    arr = np.array(img)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    return bgr


# ─────────────────────────────────────────────
# MP4生成
# ─────────────────────────────────────────────
def _check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpegが見つかりません。FFmpegをインストールしてください。"
        )


def attach_sound_to_mp4(
    video_path: Path,
    output_path: Path,
    sound_path: Path | None = None,
    video_duration: float | None = None,
    add_silent_track: bool = False,
) -> None:
    """既存MP4に効果音（または無音トラック）を付与する。"""
    _check_ffmpeg()

    if not video_path.exists() or video_path.stat().st_size == 0:
        raise RuntimeError(f"入力動画が見つかりません: {video_path}")

    duration = max(0.01, float(video_duration or 0.0)) if video_duration else None

    if sound_path is None and not add_silent_track:
        if video_path.resolve() == output_path.resolve():
            return
        shutil.copy2(video_path, output_path)
        return

    cmd = ["ffmpeg", "-y", "-i", str(video_path)]

    if sound_path is not None:
        if not sound_path.exists() or sound_path.stat().st_size == 0:
            raise RuntimeError(f"効果音ファイルが見つかりません: {sound_path}")
        cmd.extend(["-i", str(sound_path)])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"])

    cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])
    if duration is not None:
        cmd.extend(["-t", f"{duration:.3f}"])

    cmd.extend([
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音声合成に失敗しました。\n{result.stderr}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("音声合成後のMP4が生成されませんでした。")


def generate_segment_mp4(
    seg: Segment,
    output_path: Path,
    temp_dir: Path,
    style_settings: Mapping[str, Any] | None = None,
) -> None:
    """1セグメントのMP4を生成する。失敗時は1回リトライ。"""
    _check_ffmpeg()

    if style_settings:
        seg.font_name = str(style_settings.get("font_name", seg.font_name))
        seg.font_path = str(style_settings.get("font_path", seg.font_path))
        seg.text_scale_x = float(style_settings.get("text_scale_x", seg.text_scale_x))
        seg.text_scale_y = float(style_settings.get("text_scale_y", seg.text_scale_y))
        direction_value = style_settings.get("text_direction", seg.text_direction)
        if direction_value in ("横書き", "horizontal"):
            seg.text_direction = "horizontal"
        elif direction_value in ("縦書き", "vertical"):
            seg.text_direction = "vertical"

    temp_path = temp_dir / f"temp_{seg.index:03d}.mp4"

    def _render(out: Path) -> None:
        total_frames = max(1, int(seg.duration * FPS))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out), fourcc, FPS, (WIDTH, HEIGHT))
        if not writer.isOpened():
            raise RuntimeError(f"VideoWriterを開けませんでした: {out}")
        for fi in range(total_frames):
            params = _calc_frame_params(seg, fi, total_frames)
            frame = _draw_text_frame(seg, params, fi, total_frames)
            writer.write(frame)
        writer.release()

    def _ffmpeg_convert(src: Path, dst: Path) -> None:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",
            "-movflags", "+faststart",
            str(dst),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpegエラー:\n{result.stderr}")

    def _try_generate() -> bool:
        try:
            _render(temp_path)
            _ffmpeg_convert(temp_path, output_path)
            if temp_path.exists():
                temp_path.unlink()
            # 0バイトチェック
            if output_path.exists() and output_path.stat().st_size > 0:
                return True
            return False
        except Exception:
            return False

    success = _try_generate()
    if not success:
        # 1回リトライ
        if output_path.exists():
            output_path.unlink()
        if temp_path.exists():
            temp_path.unlink()
        success = _try_generate()

    if not success:
        raise RuntimeError(
            f"セグメント{seg.index:02d}のMP4生成に失敗しました。\n"
            "台本を短くするか、もう一度お試しください。"
        )


def merge_segments_to_single_mp4(mp4_paths: List[Path], output_dir: Path) -> Path:
    """セグメントMP4を順番に結合し、1本のMP4を返す。"""
    _check_ffmpeg()

    valid_paths = [p for p in mp4_paths if p.exists() and p.stat().st_size > 0]
    if not valid_paths:
        raise RuntimeError("結合対象のMP4がありません。")

    output_dir.mkdir(parents=True, exist_ok=True)
    concat_list = output_dir / "concat_list.txt"
    merged_path = output_dir / "ugoku_telop_merged.mp4"

    # concat demuxer用リスト
    lines = []
    for p in valid_paths:
        escaped = str(p.resolve()).replace("'", r"'\\''")
        lines.append(f"file '{escaped}'")
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

    copy_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(merged_path),
    ]

    reencode_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(merged_path),
    ]

    copy_result = subprocess.run(copy_cmd, capture_output=True, text=True)
    if copy_result.returncode != 0:
        reencode_result = subprocess.run(reencode_cmd, capture_output=True, text=True)
        if reencode_result.returncode != 0:
            raise RuntimeError(
                "MP4結合に失敗しました。\n"
                "[copy mode error]\n"
                f"{copy_result.stderr}\n"
                "[re-encode mode error]\n"
                f"{reencode_result.stderr}"
            )

    if not merged_path.exists() or merged_path.stat().st_size == 0:
        raise RuntimeError("MP4結合後のファイルが生成されませんでした。")

    if concat_list.exists():
        concat_list.unlink()

    return merged_path


# ─────────────────────────────────────────────
# ZIP生成
# ─────────────────────────────────────────────
def build_zip(
    segments: List[Segment],
    mp4_paths: List[Path],
    script_text: str,
    zip_path: Path,
    style_settings: Mapping[str, Any] | None = None,
) -> None:
    """MP4群 + script.txt + segments.json + README.txt をZIP化する。"""
    import zipfile
    from datetime import datetime

    seg_data = []
    for seg, mp4 in zip(segments, mp4_paths):
        size = mp4.stat().st_size if mp4.exists() else 0
        seg_data.append({
            "index":     seg.index,
            "filename":  mp4.name,
            "text":      seg.text,
            "emphasis":  seg.emphasis,
            "duration":  seg.duration,
            "animation": seg.animation,
            "font_size": seg.font_size,
            "font_name": seg.font_name,
            "text_scale_x": seg.text_scale_x,
            "text_scale_y": seg.text_scale_y,
            "text_direction": "縦書き" if seg.text_direction == "vertical" else "横書き",
            "size":      size,
        })

    readme = (
        "このZIPには、台本から生成されたMP4形式の動くテロップ素材がセグメントごとに入っています。\n\n"
        "使い方：\n"
        "1. ZIPを解凍します\n"
        "2. ugoku_telop_001.mp4 から順番に動画編集ソフトへ読み込みます\n"
        "3. タイムラインに番号順に並べます\n"
        "4. グリーンバック素材の場合は、クロマキーで緑を抜いてください\n\n"
        "CapCutの場合：\n"
        "素材を読み込み、クロマキーまたは背景削除で緑を選択してください。\n\n"
        "Premiere Proの場合：\n"
        "素材を上のトラックに配置し、Ultraキーで緑を抜いてください。\n\n"
        "DaVinci Resolveの場合：\n"
        "素材を上のトラックに配置し、Delta Keyerなどで緑を抜いてください。\n"
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for mp4 in mp4_paths:
            if mp4.exists():
                zf.write(mp4, mp4.name)
        zf.writestr("script.txt", script_text)
        zf.writestr("segments.json", json.dumps(seg_data, ensure_ascii=False, indent=2))
        zf.writestr("README.txt", readme)
