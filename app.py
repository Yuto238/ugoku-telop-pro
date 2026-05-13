# app.py — 動くテロップメーカー Pro
# Streamlit UI

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from animations import (
    ANIMATION_PRESETS,
    ANIMATION_OPTIONS,
    EMPHASIS_FALLBACK_MAP,
    EMPHASIS_UI_ROWS,
    LABEL_TO_INTERNAL,
    PRESET_ANIMATION_MAP,
    PRESET_DESCRIPTIONS,
)
from engine import (
    MAX_SEGMENTS,
    attach_sound_to_mp4,
    build_zip,
    create_style_preview_image,
    generate_segment_mp4,
    merge_segments_to_single_mp4,
    parse_script,
)

# ─────────────────────────────────────────────
# サンプル台本
# ─────────────────────────────────────────────
SAMPLE_DIR = Path(__file__).parent / "sample_scripts"


def _load_sample(name: str) -> str:
    p = SAMPLE_DIR / name
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


SAMPLE_OSHARE  = _load_sample("oshare.txt")
SAMPLE_BEAUTY  = _load_sample("beauty.txt")
SAMPLE_SHORTS  = _load_sample("shorts.txt")

SAMPLE_SCRIPTS = {
    "スタイリッシュリール用": SAMPLE_OSHARE,
    "美容リール用": SAMPLE_BEAUTY,
    "ショート動画用": SAMPLE_SHORTS,
}

BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "fonts"

FONT_OPTIONS = {
    "Noto Serif JP": ["NotoSerifJP-Bold.ttf", "NotoSerifJP-Bold.otf"],
    "M Plus 1p": ["MPLUS1p-Bold.ttf", "MPLUS1p-Bold.otf"],
    "Zen Maru Gothic": ["ZenMaruGothic-Bold.ttf", "ZenMaruGothic-Bold.otf"],
    "Dela Gothic One": ["DelaGothicOne-Regular.ttf", "DelaGothicOne-Regular.otf"],
    "Rampart One": ["RampartOne-Regular.ttf", "RampartOne-Regular.otf"],
    "Hachi Maru Pop": ["HachiMaruPop-Regular.ttf", "HachiMaruPop-Regular.otf"],
    "Shippori Mincho B1": ["ShipporiMinchoB1-Regular.ttf", "ShipporiMinchoB1-Regular.otf"],
    "Yusei Magic": ["YuseiMagic-Regular.ttf", "YuseiMagic-Regular.otf"],
}

FONT_FALLBACK_OPTIONS = {
    "Noto Serif JP": [
        "NotoSansJP-Bold.ttf",
        "NotoSansJP-Bold.otf",
        "NotoSansJP-VariableFont_wght.ttf",
    ],
}


def _resolve_font_path(font_name: str, candidates: list[str]) -> Path | None:
    for filename in candidates:
        path = FONTS_DIR / filename
        if path.exists():
            return path

    for fallback in FONT_FALLBACK_OPTIONS.get(font_name, []):
        fallback_path = FONTS_DIR / fallback
        if fallback_path.exists():
            return fallback_path

    if candidates:
        head = candidates[0].split("-")[0].lower()
        for path in sorted(FONTS_DIR.glob("*.ttf")) + sorted(FONTS_DIR.glob("*.otf")):
            if head and path.name.lower().startswith(head):
                return path
    return None


def _normalize_direction(value: str) -> str:
    return "vertical" if value == "縦書き" else "horizontal"


def _apply_style_to_segments(segments: list, style_settings: dict) -> None:
    for seg in segments:
        seg.font_name = style_settings["font_name"]
        seg.font_path = style_settings["font_path"]
        seg.text_scale_x = float(style_settings["text_scale_x"])
        seg.text_scale_y = float(style_settings["text_scale_y"])
        seg.text_direction = _normalize_direction(style_settings["text_direction"])


SFX_MODE_NONE = "効果音なし"
SFX_MODE_SAME = "全テロップに同じ効果音を付ける"
SFX_MODE_BY_EMPHASIS = "強調レベルごとに効果音を設定する"
SFX_ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a"}
SFX_EMPHASIS_LABELS = {
    "normal": "通常文",
    "light": "軽く強調",
    "strong": "強く強調",
    "impact": "大きく強調",
}


def _save_uploaded_audio_file(uploaded_file, output_dir: Path, stem: str) -> Path | None:
    if uploaded_file is None:
        return None

    suffix = Path(uploaded_file.name or "").suffix.lower()
    if suffix not in SFX_ALLOWED_EXTENSIONS:
        suffix = ".audio"

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{stem}{suffix}"
    out_path.write_bytes(uploaded_file.getvalue())
    return out_path


EXPORT_MODE_DESCRIPTIONS = {
    "セグメントMP4をZIPでダウンロード": "編集ソフトで細かく配置したい方向け。セグメントごとに読み込めます。",
    "1本のMP4動画としてダウンロード": "すぐに動画へ重ねたい方向け。確認用の1本動画を生成します。",
    "両方生成する": "確認用にも編集用にも使いたい方向け。ZIPと1本MP4をまとめて生成します。",
}


def _card_start(title: str, description: str = "", kicker: str = "", css_class: str = "") -> None:
    classes = "card-shell"
    if css_class:
        classes = f"{classes} {css_class}"
    header = [f"<div class='{classes}'>"]
    if kicker:
        header.append(f"<div class='card-kicker'>{kicker}</div>")
    header.append(f"<h3 class='card-title'>{title}</h3>")
    if description:
        header.append(f"<p class='card-description'>{description}</p>")
    st.markdown("".join(header), unsafe_allow_html=True)


def _card_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def _render_export_result(result: dict | None) -> None:
    if not result:
        st.markdown(
            """
            <div class="result-placeholder">
                <div class="result-placeholder-icon">🎬</div>
                <div class="result-placeholder-title">ここに生成結果が表示されます</div>
                <div class="result-placeholder-text">設定を整えてから、MP4素材を書き出してください。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <div class="result-success">
            <div class="result-success-title">✅ 生成が完了しました</div>
            <div class="result-success-text">{result['success_message']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result.get("zip_bytes"):
        st.download_button(
            label="📥 ZIPをダウンロード",
            data=result["zip_bytes"],
            file_name=result["zip_name"],
            mime="application/zip",
            key=f"zip_dl_{result['stamp']}",
            width="stretch",
        )

    if result.get("mp4_bytes"):
        st.download_button(
            label="📥 1本MP4をダウンロード",
            data=result["mp4_bytes"],
            file_name=result["mp4_name"],
            mime="video/mp4",
            key=f"mp4_dl_{result['stamp']}",
            width="stretch",
        )

    if result.get("errors"):
        for idx, msg in result["errors"]:
            st.error(f"セグメント{idx:02d}のMP4生成に失敗しました。\n{msg}")

    if result.get("mp4_bytes"):
        st.markdown("<div class='inline-label'>最新の書き出しプレビュー</div>", unsafe_allow_html=True)
        st.video(result["mp4_bytes"])


def get_app_password() -> str:
    DEFAULT_APP_PASSWORD = "TelopPro_2026_B7Q"
    try:
        return st.secrets.get("APP_PASSWORD", DEFAULT_APP_PASSWORD)
    except Exception:
        return DEFAULT_APP_PASSWORD


def check_password() -> bool:
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.markdown(
        """
        <style>
            .login-wrapper {
                max-width: 620px;
                margin: 90px auto 32px auto;
                padding: 42px;
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 28px;
                box-shadow: 0 18px 45px rgba(15, 27, 61, 0.12);
                text-align: center;
            }

            .login-badge {
                display: inline-block;
                background: #fff7ed;
                color: #f59e0b;
                border: 1px solid #fed7aa;
                padding: 6px 12px;
                border-radius: 999px;
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 16px;
            }

            .login-title {
                font-size: 34px;
                font-weight: 900;
                color: #111827;
                margin-bottom: 12px;
            }

            .login-description {
                color: #6b7280;
                line-height: 1.8;
                margin-bottom: 8px;
            }
        </style>
        <div class="login-wrapper">
            <div class="login-badge">BOOTH購入者専用</div>
            <div class="login-title">動くテロップメーカー Pro</div>
            <div class="login-description">
                台本からMP4テロップ素材を一括生成する購入者専用ツールです。<br>
                BOOTHでダウンロードした案内ファイルに記載されたパスワードを入力してください。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    password = st.text_input("購入者用パスワード", type="password", key="auth_password")
    if st.button("ログイン", use_container_width=True):
        if not password:
            st.error("パスワードを入力してください。")
        elif password == get_app_password():
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("パスワードが違います。BOOTHでダウンロードした「Pro版アクセスURL.txt」をご確認ください。")

    st.caption("パスワードが分からない場合は、BOOTHでダウンロードした「Pro版アクセスURL.txt」をご確認ください。")
    st.stop()


def logout_button() -> None:
    with st.sidebar:
        if st.button("ログアウト", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

# ─────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="動くテロップメーカー Pro",
    page_icon="🎬",
    layout="wide"
)

check_password()

# ─────────────────────────────────────────────
# カスタムCSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    :root {
        --bg: #F7F8FB;
        --panel: #FFFFFF;
        --panel-soft: #FAFAF7;
        --text: #111827;
        --text-strong: #17213A;
        --muted: #4B5563;
        --muted-soft: #6B7280;
        --line: #E5E7EB;
        --navy: #17213A;
        --navy-2: #1E293B;
        --gold: #F59E0B;
        --gold-soft: #FFB84D;
        --blue: #2563EB;
        --indigo: #6366F1;
        --shadow: 0 18px 45px rgba(17, 24, 39, 0.06);
    }

    .stApp {
        background: linear-gradient(180deg, #FAFAF7 0%, #F7F8FB 100%);
        color: var(--text-strong);
    }

    .block-container {
        max-width: 1180px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }

    .main-title, .sub-copy {
        display: none;
    }

    .hero {
        position: relative;
        overflow: hidden;
        background: radial-gradient(circle at top right, rgba(245, 158, 11, 0.24), transparent 34%), linear-gradient(135deg, #111827 0%, #17213A 52%, #1E293B 100%);
        color: #fff;
        padding: 40px 42px;
        border-radius: 30px;
        box-shadow: 0 22px 60px rgba(15, 23, 42, 0.22);
        margin-bottom: 28px;
    }

    .hero::after {
        content: "";
        position: absolute;
        inset: auto -80px -120px auto;
        width: 240px;
        height: 240px;
        border-radius: 999px;
        background: radial-gradient(circle, rgba(255,184,77,.30) 0%, rgba(255,184,77,0) 70%);
    }

    .hero-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 12px;
        border-radius: 999px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.14);
        color: #FDE68A;
        font-size: 12px;
        font-weight: 800;
        margin-bottom: 16px;
        letter-spacing: .04em;
    }

    .hero h1 {
        font-size: 44px;
        line-height: 1.08;
        letter-spacing: -0.04em;
        margin: 0 0 12px 0;
    }

    .hero-subcopy {
        font-size: 18px;
        line-height: 1.75;
        color: rgba(255,255,255,0.92);
        margin-bottom: 10px;
        font-weight: 700;
    }

    .hero-description {
        font-size: 15px;
        line-height: 1.9;
        color: rgba(255,255,255,0.76);
        max-width: 760px;
        margin: 0;
    }

    .badges {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 22px;
    }

    .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border-radius: 999px;
        padding: 9px 13px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.14);
        color: #F9FAFB;
        font-size: 13px;
        font-weight: 700;
    }

    .flow-intro {
        color: var(--muted);
        margin: 0 0 20px 0;
        font-size: 15px;
        line-height: 1.8;
    }

    .steps {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin: 0 0 28px 0;
    }

    .step {
        background: rgba(255,255,255,0.88);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 22px;
        box-shadow: var(--shadow);
    }

    .step-num {
        color: var(--gold);
        font-size: 12px;
        font-weight: 900;
        letter-spacing: .08em;
        margin-bottom: 8px;
    }

    .step-title {
        color: var(--text-strong);
        font-size: 18px;
        font-weight: 900;
        margin-bottom: 8px;
    }

    .step-text {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.75;
    }

    .card-shell {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 24px;
        box-shadow: var(--shadow);
        margin-bottom: 22px;
    }

    .preview-shell {
        background: linear-gradient(180deg, #111827 0%, #17213A 100%);
        color: #fff;
    }

    .card-kicker {
        color: var(--indigo);
        font-size: 12px;
        font-weight: 900;
        letter-spacing: .08em;
        margin-bottom: 10px;
        text-transform: uppercase;
    }

    .preview-shell .card-kicker {
        color: #93C5FD;
    }

    .card-title {
        margin: 0 0 6px 0;
        font-size: 26px;
        line-height: 1.2;
        color: var(--text-strong);
        font-weight: 900;
    }

    .preview-shell .card-title {
        color: #fff;
    }

    .card-description {
        margin: 0 0 18px 0;
        color: var(--muted);
        line-height: 1.8;
        font-size: 14px;
    }

    .preview-shell .card-description {
        color: rgba(255,255,255,0.74);
    }

    .mini-label, .inline-label {
        color: var(--muted-soft);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: .04em;
        margin: 6px 0 10px 0;
        text-transform: uppercase;
    }

    .inline-label {
        margin-top: 16px;
    }

    .preset-choice {
        background: #F9FAFB;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 16px;
        min-height: 120px;
    }

    .preset-choice.active {
        border-color: rgba(37, 99, 235, 0.32);
        background: linear-gradient(180deg, rgba(37,99,235,0.06) 0%, rgba(255,255,255,1) 100%);
        box-shadow: 0 12px 28px rgba(37, 99, 235, 0.08);
    }

    .preset-choice-title {
        color: var(--text-strong);
        font-size: 17px;
        font-weight: 900;
        margin-bottom: 8px;
    }

    .preset-choice-desc {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.75;
    }

    .preset-note {
        background: #EEF4FF;
        border: 1px solid #D7E3FF;
        border-radius: 16px;
        padding: 12px 14px;
        color: #33436F;
        font-size: 14px;
        margin: 10px 0 16px;
    }

    .preset-map-card {
        background: #F9FAFB;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 16px;
        height: 100%;
    }

    .preset-map-level {
        font-size: 12px;
        font-weight: 800;
        color: var(--muted-soft);
        margin-bottom: 5px;
    }

    .preset-map-effect {
        font-size: 18px;
        font-weight: 900;
        color: var(--text-strong);
        margin-bottom: 4px;
    }

    .preset-map-meta {
        font-size: 12px;
        color: #8A92A8;
        margin-bottom: 6px;
    }

    .preset-map-desc {
        font-size: 13px;
        color: var(--muted);
        line-height: 1.7;
    }

    .preview-stage {
        background: radial-gradient(circle at top, rgba(255,184,77,0.12), rgba(255,184,77,0) 40%), rgba(255,255,255,0.04);
        border: 1px dashed rgba(255,255,255,0.14);
        border-radius: 24px;
        padding: 16px;
        text-align: center;
    }

    .preview-placeholder {
        min-height: 360px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        border-radius: 20px;
        background: rgba(255,255,255,0.04);
        color: rgba(255,255,255,0.70);
        font-size: 15px;
        line-height: 1.8;
        padding: 24px;
    }

    .preview-placeholder strong {
        color: #fff;
        font-size: 18px;
        margin-bottom: 8px;
    }

    .script-guide {
        background: #FFF8EA;
        border: 1px solid #FDE7BE;
        border-radius: 18px;
        padding: 16px 18px;
        color: #7A5800;
        font-size: 14px;
        line-height: 1.8;
        margin-bottom: 16px;
    }

    .script-stats {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin: 14px 0 4px;
    }

    .stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border-radius: 999px;
        padding: 8px 12px;
        background: #F3F4F6;
        color: var(--text-strong);
        font-size: 13px;
        font-weight: 800;
    }

    .summary-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
    }

    .summary-item {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        padding: 12px 14px;
        background: #F9FAFB;
        border: 1px solid var(--line);
        border-radius: 16px;
        color: var(--muted);
        font-size: 13px;
    }

    .summary-item strong {
        color: var(--text-strong);
        font-size: 14px;
    }

    .export-choice {
        background: #F9FAFB;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }

    .export-choice-title {
        color: var(--text-strong);
        font-size: 15px;
        font-weight: 900;
        margin-bottom: 4px;
    }

    .export-choice-desc {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.7;
    }

    .result-placeholder,
    .result-success {
        border-radius: 20px;
        padding: 18px 18px;
        margin-bottom: 14px;
    }

    .result-placeholder {
        background: #F9FAFB;
        border: 1px dashed var(--line);
        text-align: center;
    }

    .result-placeholder-icon {
        font-size: 28px;
        margin-bottom: 8px;
    }

    .result-placeholder-title,
    .result-success-title {
        color: var(--text-strong);
        font-size: 18px;
        font-weight: 900;
        margin-bottom: 6px;
    }

    .result-placeholder-text,
    .result-success-text {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.8;
    }

    .result-success {
        background: linear-gradient(180deg, rgba(34,197,94,0.08) 0%, rgba(255,255,255,1) 100%);
        border: 1px solid rgba(34,197,94,0.18);
    }

    .footer-note, .notice-box {
        background: #F3F4F6;
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 22px 24px;
        color: var(--muted);
        font-size: 14px;
        line-height: 1.9;
        margin-top: 24px;
    }

    .anim-card {
        background: #ffffff;
        border: 1.5px solid var(--line);
        border-radius: 22px;
        padding: 20px 22px;
        box-shadow: var(--shadow);
        height: 100%;
    }

    .anim-label {
        font-size: 20px;
        font-weight: 900;
        color: var(--text-strong);
        margin: 0 0 2px 0;
    }

    .anim-internal {
        font-size: 11px;
        color: #9AA0B4;
        font-family: monospace;
        margin-bottom: 10px;
    }

    .anim-desc {
        font-size: 13.5px;
        color: var(--muted);
        line-height: 1.7;
        margin-bottom: 12px;
    }

    .anim-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 12px;
    }

    .anim-tag {
        background: #F3F4F6;
        color: #33436F;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 12px;
        font-weight: 700;
    }

    .anim-sample {
        background: #FFF8EA;
        border: 1px solid #FDE7BE;
        padding: 7px 12px;
        border-radius: 10px;
        font-size: 13px;
        color: #7A5800;
        margin-bottom: 14px;
    }

    .list-hero {
        background: linear-gradient(135deg, rgba(37,99,235,0.08) 0%, rgba(99,102,241,0.06) 55%, rgba(255,255,255,0.92) 100%);
        border: 1px solid rgba(99,102,241,0.12);
        border-radius: 26px;
        padding: 26px 28px;
        box-shadow: var(--shadow);
        margin-bottom: 20px;
    }

    .list-hero-title {
        color: var(--text-strong);
        font-size: 30px;
        font-weight: 900;
        letter-spacing: -0.03em;
        margin-bottom: 8px;
    }

    .list-hero-text {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.85;
        max-width: 760px;
    }

    .list-metrics {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 16px;
    }

    .list-metric {
        background: #FFFFFF;
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 8px 12px;
        color: var(--text-strong);
        font-size: 13px;
        font-weight: 800;
    }

    .action-card {
        background: #FFFFFF;
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 18px 20px;
        margin-bottom: 18px;
        box-shadow: var(--shadow);
    }

    .action-card-title {
        color: var(--text-strong);
        font-size: 18px;
        font-weight: 900;
        margin-bottom: 6px;
    }

    .action-card-text {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.75;
        margin-bottom: 14px;
    }

    .anim-meta-label {
        font-size: 12px;
        color: #8087A0;
        margin-bottom: 6px;
        font-weight: 700;
    }

    .anim-result {
        margin-top: 12px;
        padding: 14px;
        border-radius: 18px;
        background: #F9FAFB;
        border: 1px solid var(--line);
    }

    .seg-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-left: 6px;
    }

    .badge-normal  { background: #E8F4FD; color: #1A73E8; }
    .badge-light   { background: #E8FDF4; color: #1AA86E; }
    .badge-strong  { background: #FFF3E0; color: #E67E22; }
    .badge-impact  { background: #FDE8E8; color: #E74C3C; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        margin-bottom: 18px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 999px;
        background: rgba(255,255,255,0.8);
        border: 1px solid var(--line);
        padding: 10px 16px;
        font-weight: 800;
        color: var(--muted);
    }

    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: var(--text-strong) !important;
        box-shadow: 0 8px 20px rgba(17,24,39,0.06);
    }

    .stTextArea textarea,
    .stTextInput input,
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div {
        background: #FCFCFD !important;
        border: 1px solid var(--line) !important;
        border-radius: 18px !important;
        color: var(--text-strong) !important;
        box-shadow: none !important;
    }

    .stTextArea textarea {
        min-height: 420px;
        font-size: 15px !important;
        line-height: 1.8 !important;
        padding: 1rem 1.1rem !important;
    }

    .stSlider [data-baseweb="slider"] {
        padding-top: 6px;
    }

    .stRadio > label,
    .stSelectbox > label,
    .stTextArea > label,
    .stTextInput > label,
    .stSlider > label {
        font-weight: 800 !important;
        color: var(--text-strong) !important;
        font-size: 14px !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 999px !important;
        font-weight: 900 !important;
        padding: 0.92rem 1.35rem !important;
        border: none !important;
        transition: all .18s ease !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #17213A 0%, #2563EB 100%) !important;
        color: #fff !important;
        box-shadow: 0 16px 28px rgba(37, 99, 235, 0.16) !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        filter: brightness(1.02);
    }

    .stDownloadButton > button {
        background: linear-gradient(135deg, #F59E0B 0%, #FFB84D 100%) !important;
        color: #17213A !important;
        box-shadow: 0 16px 28px rgba(245, 158, 11, 0.18) !important;
    }

    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #2563EB 0%, #6366F1 100%);
    }

    .stAlert {
        border-radius: 18px !important;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 1.2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .hero {
            padding: 28px 22px;
            border-radius: 24px;
        }

        .hero h1 {
            font-size: 32px;
        }

        .hero-subcopy {
            font-size: 16px;
        }

        .steps {
            grid-template-columns: 1fr;
        }

        .card-shell {
            padding: 20px;
            border-radius: 20px;
        }

        .preview-placeholder {
            min-height: 240px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ヘッダー
# ─────────────────────────────────────────────
if "script_input" not in st.session_state:
    st.session_state["script_input"] = ""

if "export_result" not in st.session_state:
    st.session_state["export_result"] = None

logout_button()

# ─────────────────────────────────────────────
# タブ
# ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["🎬 台本から生成", "🎨 アニメーション一覧"])

with tab1:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-eyebrow">CREATOR TOOL · PRO WORKFLOW</div>
            <h1>動くテロップメーカー Pro</h1>
            <div class="hero-subcopy">台本を貼るだけで、MP4テロップ素材を一括生成。</div>
            <p class="hero-description">
                リール・ショート動画・店舗紹介動画に使える動くテロップ素材を、台本からまとめて作成できます。<br>
                強調したい言葉をマークするだけで、エフェクト付きのMP4素材を書き出せます。
            </p>
            <div class="badges">
                <span class="badge">MP4出力</span>
                <span class="badge">ZIP一括</span>
                <span class="badge">1本MP4対応</span>
                <span class="badge">9:16対応</span>
                <span class="badge">商用利用向け</span>
                <span class="badge">グリーンバック対応</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="steps">
            <div class="step">
                <div class="step-num">STEP 1</div>
                <div class="step-title">台本を貼る</div>
                <div class="step-text">空行ごとにセグメント化されるので、動画の流れに沿ってテキストを並べるだけです。</div>
            </div>
            <div class="step">
                <div class="step-num">STEP 2</div>
                <div class="step-title">強調したい言葉をマーク</div>
                <div class="step-text">*軽く*、**強く**、!!大きく!! の3段階で、印象に合わせた動きを自動で付けられます。</div>
            </div>
            <div class="step">
                <div class="step-num">STEP 3</div>
                <div class="step-title">MP4 / ZIPで書き出す</div>
                <div class="step-text">編集用ZIPでも確認用の1本MP4でも出力でき、動画制作フローにそのまま乗せられます。</div>
            </div>
        </div>
        <p class="flow-intro">入力 → 設定 → プレビュー → 書き出しの流れで、迷わず使えるように画面を整理しています。</p>
        """,
        unsafe_allow_html=True,
    )

    available_fonts = {
        display_name: resolved
        for display_name, candidates in FONT_OPTIONS.items()
        if (resolved := _resolve_font_path(display_name, candidates)) is not None
    }

    detected_font_files = sorted(
        [p.name for p in FONTS_DIR.glob("*.ttf")] + [p.name for p in FONTS_DIR.glob("*.otf")]
    )
    missing_fonts = [
        f"{display_name}（{candidates[0]}）"
        for display_name, candidates in FONT_OPTIONS.items()
        if _resolve_font_path(display_name, candidates) is None
    ]

    if not available_fonts:
        st.error(
            "日本語フォントが見つかりません。\n"
            "fonts フォルダに以下のいずれかのフォントファイルを配置してください。\n\n"
            "- NotoSerifJP-Bold.ttf\n"
            "- MPLUS1p-Bold.ttf\n"
            "- ZenMaruGothic-Bold.ttf\n"
            "- DelaGothicOne-Regular.ttf\n"
            "- RampartOne-Regular.ttf\n"
            "- HachiMaruPop-Regular.ttf\n"
            "- ShipporiMinchoB1-Regular.ttf\n"
            "- YuseiMagic-Regular.ttf"
        )
        st.info(f"現在参照中の fonts フォルダ：\n{FONTS_DIR}")
        st.stop()

    left_col, right_col = st.columns([1.18, 0.82], gap="large")

    preset_descriptions = {
        "おしゃれリール用": "余白と雰囲気を重視した、静かで上品な動き。",
        "美容リール用": "やわらかく垢抜けた印象に合う動き。",
        "ショート動画用": "テンポよく目を引く、強めの動き。",
    }

    sound_mode = SFX_MODE_NONE
    global_sound_upload = None
    emphasis_sound_uploads = {
        "normal": None,
        "light": None,
        "strong": None,
        "impact": None,
    }

    with left_col:
        _card_start("用途別プリセット", "目的に合わせておすすめの動きをベース設定にできます。", kicker="Preset")
        selected_usecase_preset = st.selectbox(
            "用途別プリセット",
            list(PRESET_ANIMATION_MAP.keys()),
            index=0,
        )
        st.markdown(
            f"<div class='preset-note'>{PRESET_DESCRIPTIONS.get(selected_usecase_preset, '')}</div>",
            unsafe_allow_html=True,
        )
        preset_cols = st.columns(3)
        for idx, preset_name in enumerate(PRESET_ANIMATION_MAP.keys()):
            active_class = "active" if preset_name == selected_usecase_preset else ""
            with preset_cols[idx]:
                st.markdown(
                    f"""
                    <div class="preset-choice {active_class}">
                        <div class="preset-choice-title">{preset_name}</div>
                        <div class="preset-choice-desc">{preset_descriptions.get(preset_name, '')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        base_map = PRESET_ANIMATION_MAP[selected_usecase_preset]

        def _apply_preset_to_state() -> None:
            st.session_state["normal_animation"] = base_map["normal"]
            st.session_state["light_animation"] = base_map["light"]
            st.session_state["strong_animation"] = base_map["strong"]
            st.session_state["impact_animation"] = base_map["impact"]

        if "effect_preset_initialized" not in st.session_state:
            _apply_preset_to_state()
            st.session_state["effect_preset_initialized"] = True

        preset_btn_col1, preset_btn_col2 = st.columns(2)
        with preset_btn_col1:
            if st.button("このプリセットを反映", width="stretch"):
                _apply_preset_to_state()
                st.rerun()
        with preset_btn_col2:
            if st.button("おすすめ設定に戻す", width="stretch"):
                _apply_preset_to_state()
                st.rerun()
        _card_end()

        _card_start("エフェクト設定", "通常文から大きな強調まで、4段階の表現を分かりやすく調整できます。", kicker="Effects")
        option_keys = list(ANIMATION_OPTIONS.keys())
        effect_left, effect_right = st.columns(2)
        with effect_left:
            normal_animation = st.selectbox(
                "通常文｜記法：なし",
                options=option_keys,
                format_func=lambda x: ANIMATION_OPTIONS[x],
                key="normal_animation",
            )
            strong_animation = st.selectbox(
                "強く強調｜記法：**テキスト**",
                options=option_keys,
                format_func=lambda x: ANIMATION_OPTIONS[x],
                key="strong_animation",
            )
        with effect_right:
            light_animation = st.selectbox(
                "軽く強調｜記法：*テキスト*",
                options=option_keys,
                format_func=lambda x: ANIMATION_OPTIONS[x],
                key="light_animation",
            )
            impact_animation = st.selectbox(
                "大きく強調｜記法：!!テキスト!!",
                options=option_keys,
                format_func=lambda x: ANIMATION_OPTIONS[x],
                key="impact_animation",
            )

        selected_preset_animation_map = {
            "normal": normal_animation,
            "light": light_animation,
            "strong": strong_animation,
            "impact": impact_animation,
        }

        invalid_levels: list[str] = []
        effective_animation_map: dict[str, str] = {}
        for row in EMPHASIS_UI_ROWS:
            level = row["key"]
            candidate = selected_preset_animation_map.get(level, "")
            if candidate in ANIMATION_OPTIONS:
                effective_animation_map[level] = candidate
            else:
                effective_animation_map[level] = EMPHASIS_FALLBACK_MAP[level]
                invalid_levels.append(level)

        if invalid_levels:
            st.warning("選択されたエフェクトが未実装のため、標準エフェクトに置き換えました。")

        st.markdown("<div class='mini-label'>現在のエフェクト設定</div>", unsafe_allow_html=True)
        summary_cols_top = st.columns(2)
        summary_cols_bottom = st.columns(2)
        summary_cols = [summary_cols_top[0], summary_cols_top[1], summary_cols_bottom[0], summary_cols_bottom[1]]
        for idx, row in enumerate(EMPHASIS_UI_ROWS):
            anim_key = effective_animation_map[row["key"]]
            anim_info = ANIMATION_PRESETS.get(anim_key, {})
            effect_label = anim_info.get("label", anim_key)
            effect_desc = ANIMATION_OPTIONS.get(anim_key, effect_label)
            with summary_cols[idx]:
                st.markdown(
                    f"""
                    <div class="preset-map-card">
                        <div class="preset-map-level">{row['title']}</div>
                        <div class="preset-map-effect">{effect_label}</div>
                        <div class="preset-map-meta">{row['notation']}</div>
                        <div class="preset-map-desc">{effect_desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        _anim_options = ["自動（上の強調レベル別設定を使う）"] + [v["label"] for v in ANIMATION_PRESETS.values()]
        animation_label = st.selectbox(
            "アニメーション一括上書き（任意）",
            _anim_options,
            index=0,
        )
        selected_animation = "auto" if animation_label.startswith("自動") else LABEL_TO_INTERNAL.get(animation_label, "auto")
        if selected_animation == "auto":
            st.caption("現在は上で選んだ強調レベル別の設定で生成されます。")
        else:
            override_label = ANIMATION_PRESETS.get(selected_animation, {}).get("label", selected_animation)
            st.info(f"個別指定が優先されます：すべての強調レベルに `{override_label}` を適用します。")
        _card_end()

        _card_start("文字スタイル設定", "フォントや文字の縦横比、縦書き / 横書きを調整できます。", kicker="Style")
        if missing_fonts:
            st.warning("見つからないフォント：\n- " + "\n- ".join(missing_fonts))

        font_names = list(available_fonts.keys())
        default_font_name = "Noto Serif JP" if "Noto Serif JP" in font_names else font_names[0]
        if "selected_font_name" in st.session_state and st.session_state["selected_font_name"] not in font_names:
            del st.session_state["selected_font_name"]
        selected_font_index = font_names.index(default_font_name)

        style_col1, style_col2 = st.columns(2)
        with style_col1:
            selected_font_name = st.selectbox(
                "フォント",
                options=font_names,
                index=selected_font_index,
                key="selected_font_name",
            )
            text_direction = st.radio(
                "文字方向",
                options=["横書き", "縦書き"],
                index=0,
                key="text_direction",
                horizontal=True,
            )
        with style_col2:
            text_scale_x = st.slider(
                "文字の横幅",
                min_value=0.8,
                max_value=1.3,
                value=1.0,
                step=0.05,
                key="text_scale_x",
                help="1.0が標準です。数値を大きくすると横に広がり、小さくすると細くなります。",
            )
            text_scale_y = st.slider(
                "文字の縦幅",
                min_value=0.8,
                max_value=1.3,
                value=1.0,
                step=0.05,
                key="text_scale_y",
                help="1.0が標準です。数値を大きくすると縦に伸び、小さくすると低くなります。",
            )

        preview_text = st.text_input(
            "プレビュー用テキスト",
            value="一味違うリールに",
            key="preview_text",
        )

        with st.expander("フォント検出デバッグ（開発用）", expanded=False):
            st.write("Fonts dir:", str(FONTS_DIR))
            st.write("Detected font files:", detected_font_files)
            st.write("Configured fonts:", list(FONT_OPTIONS.keys()))
            st.write("Configured count:", len(FONT_OPTIONS))
            st.write("Available fonts:", list(available_fonts.keys()))
            st.write("Available count:", len(available_fonts))
            if missing_fonts:
                st.write("Missing font files:", missing_fonts)
        _card_end()

        _card_start("効果音設定", "ユーザー自身が用意した音声をアップロードして、各MP4に合成できます。", kicker="Sound FX")
        sound_mode = st.radio(
            "効果音の付け方",
            options=[SFX_MODE_NONE, SFX_MODE_SAME, SFX_MODE_BY_EMPHASIS],
            index=0,
            key="sound_mode",
        )

        if sound_mode == SFX_MODE_SAME:
            global_sound_upload = st.file_uploader(
                "全テロップ共通の効果音（mp3 / wav / m4a）",
                type=["mp3", "wav", "m4a"],
                key="sound_upload_same",
            )
            if global_sound_upload is None:
                st.caption("未選択の場合は効果音なしで出力します。")

        if sound_mode == SFX_MODE_BY_EMPHASIS:
            emphasis_sound_uploads["normal"] = st.file_uploader(
                "通常文（任意）",
                type=["mp3", "wav", "m4a"],
                key="sound_upload_normal",
            )
            emphasis_sound_uploads["light"] = st.file_uploader(
                "軽く強調（任意）",
                type=["mp3", "wav", "m4a"],
                key="sound_upload_light",
            )
            emphasis_sound_uploads["strong"] = st.file_uploader(
                "強く強調（任意）",
                type=["mp3", "wav", "m4a"],
                key="sound_upload_strong",
            )
            emphasis_sound_uploads["impact"] = st.file_uploader(
                "大きく強調（任意）",
                type=["mp3", "wav", "m4a"],
                key="sound_upload_impact",
            )

        st.warning(
            "効果音ファイルはご自身で利用権利を確認したものをご使用ください。\n"
            "再配布・商用利用・加工が禁止されている音源の使用はお控えください。"
        )
        _card_end()

        selected_font_path = str(available_fonts[selected_font_name])
        style_settings = {
            "font_name": selected_font_name,
            "font_path": selected_font_path,
            "text_scale_x": float(text_scale_x),
            "text_scale_y": float(text_scale_y),
            "text_direction": text_direction,
        }

        _card_start("サンプル台本", "用途に近い台本を呼び出して、すぐに動きを確認できます。", kicker="Samples")
        sample_col1, sample_col2, sample_col3 = st.columns(3)
        with sample_col1:
            if st.button("✨ スタイリッシュリール用", use_container_width=True):
                st.session_state["script_input"] = SAMPLE_SCRIPTS["スタイリッシュリール用"]
                st.rerun()
        with sample_col2:
            if st.button("💄 美容リール用", use_container_width=True):
                st.session_state["script_input"] = SAMPLE_SCRIPTS["美容リール用"]
                st.rerun()
        with sample_col3:
            if st.button("⚡ ショート動画用", use_container_width=True):
                st.session_state["script_input"] = SAMPLE_SCRIPTS["ショート動画用"]
                st.rerun()
        _card_end()

        _card_start("台本を入力", "空行ごとに1つのテロップ素材として生成されます。強調したい言葉は *このように*、**このように**、!!このように!! マークしてください。", kicker="Script")
        st.markdown(
            """
            <div class="script-guide">
                <strong>強調マークの使い方</strong><br>
                <code>*テキスト*</code> → 軽く強調 ／ <code>**テキスト**</code> → 強く強調 ／ <code>!!テキスト!!</code> → 大きく強調<br>
                マークなしは通常テキストとして扱われます。<br><br>
                <strong>改行ルール</strong><br>
                空行ごとに1つのテロップ素材として分割されます。<br>
                1つのテロップ内で改行したい場合は、空行を入れずに改行してください。<br><br>
                例）これは2行テロップになります：<br>
                テロップに<br>
                少しだけ動きを<br><br>
                例）これは2つのテロップになります：<br>
                テロップに<br><br>
                少しだけ動きを
            </div>
            """,
            unsafe_allow_html=True,
        )
        script_input = st.text_area(
            label="台本",
            key="script_input",
            height=420,
            placeholder=(
                "ここに台本を貼り付けてください。\n\n"
                "今日は\n\n"
                "*少しだけ*\n\n"
                "**いつもと違う動画に**\n\n"
                "!!一味違うリールに!!"
            ),
            label_visibility="collapsed",
        )

        segs = []
        if script_input.strip():
            segs = parse_script(
                script_input,
                animation_mode=selected_animation,
                emphasis_animation_map=effective_animation_map,
            )
            _apply_style_to_segments(segs, style_settings)
            count = len(segs)
            total_dur = sum(s.duration for s in segs)
            st.markdown(
                f"<div class='script-stats'><span class='stat-pill'>{count} セグメント</span><span class='stat-pill'>合計 約 {total_dur:.1f} 秒</span></div>",
                unsafe_allow_html=True,
            )

            if count > MAX_SEGMENTS:
                st.warning(
                    f"⚠️ セグメント数が {MAX_SEGMENTS} を超えています（現在 {count} 件）。\n\n"
                    "安定して生成するため、台本を短くするか分割してください。"
                )

            if style_settings["text_direction"] == "縦書き" and any(len(s.text.replace("\n", "")) >= 15 for s in segs):
                st.warning(
                    "縦書きは短い言葉向けです。\n"
                    "15文字以上のセグメントでは、文字が小さくなる可能性があります。"
                )

            with st.expander("セグメント一覧を確認する", expanded=False):
                badge_map = {
                    "normal": ("badge-normal", "通常"),
                    "light":  ("badge-light",  "軽強調"),
                    "strong": ("badge-strong", "強強調"),
                    "impact": ("badge-impact", "インパクト"),
                }
                for s in segs:
                    cls, label = badge_map.get(s.emphasis, ("badge-normal", s.emphasis))
                    st.markdown(
                        f"**{s.index:02d}.** {s.text} <span class='seg-badge {cls}'>{label}</span> <small style='color:#9aa0b4'>{s.duration}s / {s.animation}</small>",
                        unsafe_allow_html=True,
                    )
        _card_end()

    with right_col:
        _card_start("仕上がりプレビュー", "文字スタイルの見た目を確認できます。書き出し後は1本MP4のプレビューもここで確認できます。", kicker="Preview", css_class="preview-shell")
        st.markdown("<div class='preview-stage'>", unsafe_allow_html=True)
        preview_result = st.session_state.get("export_result")
        if preview_text.strip():
            try:
                preview_image = create_style_preview_image(
                    text=preview_text,
                    font_path=selected_font_path,
                    text_scale_x=float(text_scale_x),
                    text_scale_y=float(text_scale_y),
                    text_direction=text_direction,
                    canvas_width=1080,
                    canvas_height=1920,
                )
                st.image(preview_image, caption="現在の文字スタイルプレビュー", width="stretch")
            except FileNotFoundError:
                st.error("選択されたフォントが見つかりません。")
            except Exception:
                st.error("プレビュー画像の生成に失敗しました。")
        else:
            st.markdown(
                """
                <div class="preview-placeholder">
                    <strong>ここに文字スタイルのプレビューが表示されます</strong>
                    フォント、文字方向、縦横スケール、プレビュー用テキストを設定すると仕上がりを確認できます。
                </div>
                """,
                unsafe_allow_html=True,
            )

        if preview_result and preview_result.get("mp4_bytes"):
            st.markdown("<div class='inline-label'>最新の書き出しMP4プレビュー</div>", unsafe_allow_html=True)
            st.video(preview_result["mp4_bytes"])
        st.markdown("</div>", unsafe_allow_html=True)
        _card_end()

        _card_start("書き出し設定", "用途に合わせて、編集用ZIP・確認用1本MP4・両方生成から選べます。", kicker="Export")
        export_mode = st.radio(
            "書き出し方法",
            options=list(EXPORT_MODE_DESCRIPTIONS.keys()),
            index=0,
            horizontal=False,
        )
        for mode, description in EXPORT_MODE_DESCRIPTIONS.items():
            active_border = "style='border-color: rgba(37,99,235,0.28); background: linear-gradient(180deg, rgba(37,99,235,0.06) 0%, rgba(255,255,255,1) 100%);'" if mode == export_mode else ""
            st.markdown(
                f"""
                <div class="export-choice" {active_border}>
                    <div class="export-choice-title">{mode}</div>
                    <div class="export-choice-desc">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        generate_btn = st.button(
            "🚀 MP4素材を書き出す",
            type="primary",
            width="stretch",
            disabled=not script_input.strip(),
        )
        st.caption("生成には数十秒かかる場合があります。長めの台本では少しお待ちください。")
        _card_end()

        _card_start("現在の設定まとめ", "今のプリセット・エフェクト・文字スタイル・出力形式を一覧で確認できます。", kicker="Summary")
        override_summary = "自動" if selected_animation == "auto" else ANIMATION_PRESETS.get(selected_animation, {}).get("label", selected_animation)
        summary_rows = [
            ("用途別プリセット", selected_usecase_preset),
            ("アニメーション上書き", override_summary),
            ("通常文", ANIMATION_PRESETS.get(effective_animation_map["normal"], {}).get("label", effective_animation_map["normal"])),
            ("軽く強調", ANIMATION_PRESETS.get(effective_animation_map["light"], {}).get("label", effective_animation_map["light"])),
            ("強く強調", ANIMATION_PRESETS.get(effective_animation_map["strong"], {}).get("label", effective_animation_map["strong"])),
            ("大きく強調", ANIMATION_PRESETS.get(effective_animation_map["impact"], {}).get("label", effective_animation_map["impact"])),
            ("効果音モード", sound_mode),
            ("フォント", selected_font_name),
            ("文字方向", text_direction),
            ("横幅", f"{text_scale_x:.2f}"),
            ("縦幅", f"{text_scale_y:.2f}"),
            ("書き出し方法", export_mode),
        ]

        if sound_mode == SFX_MODE_SAME:
            summary_rows.append(("共通効果音", global_sound_upload.name if global_sound_upload else "なし"))
        elif sound_mode == SFX_MODE_BY_EMPHASIS:
            for level in ("normal", "light", "strong", "impact"):
                uploaded = emphasis_sound_uploads[level]
                summary_rows.append((f"{SFX_EMPHASIS_LABELS[level]}の効果音", uploaded.name if uploaded else "なし"))

        st.markdown("<div class='summary-grid'>", unsafe_allow_html=True)
        for label, value in summary_rows:
            st.markdown(
                f"<div class='summary-item'><span>{label}</span><strong>{value}</strong></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        _card_end()

        _card_start("生成結果", "書き出し後のダウンロードと完了メッセージをここにまとめます。", kicker="Downloads")
        progress_host = st.container()
        result_host = st.container()
        with result_host:
            _render_export_result(st.session_state.get("export_result"))
        _card_end()

    if generate_btn:
        if not script_input.strip():
            st.error("台本を入力してください。")
            st.stop()

        segments = parse_script(
            script_input,
            animation_mode=selected_animation,
            emphasis_animation_map=effective_animation_map,
        )
        _apply_style_to_segments(segments, style_settings)

        if len(segments) == 0:
            st.error("台本を入力してください。")
            st.stop()

        if len(segments) > MAX_SEGMENTS:
            st.error(
                f"セグメント数が {MAX_SEGMENTS} を超えています（現在 {len(segments)} 件）。\n\n"
                "安定して生成するため、台本を短くするか分割してください。"
            )
            st.stop()

        st.session_state["export_result"] = None

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mp4_paths = []
            errors = []
            total = len(segments)

            sound_dir = tmp_path / "uploaded_sounds"
            emphasis_sound_paths: dict[str, Path | None] = {
                "normal": None,
                "light": None,
                "strong": None,
                "impact": None,
            }
            if sound_mode == SFX_MODE_SAME and global_sound_upload is not None:
                shared_path = _save_uploaded_audio_file(global_sound_upload, sound_dir, "shared_sound")
                for level in emphasis_sound_paths:
                    emphasis_sound_paths[level] = shared_path
            elif sound_mode == SFX_MODE_BY_EMPHASIS:
                for level in emphasis_sound_paths:
                    emphasis_sound_paths[level] = _save_uploaded_audio_file(
                        emphasis_sound_uploads.get(level),
                        sound_dir,
                        f"sound_{level}",
                    )

            has_any_sound = any(path is not None for path in emphasis_sound_paths.values())

            with progress_host:
                progress_text = st.empty()
                progress_bar = st.progress(0)
                status_text = st.empty()

            for i, seg in enumerate(segments):
                filename = f"ugoku_telop_{seg.index:03d}.mp4"
                out_path = tmp_path / filename
                progress_text.markdown(f"**セグメント生成中：{i + 1} / {total}**")
                status_text.markdown(f"現在：{seg.text}  \nファイル：`{filename}`")
                progress_bar.progress(i / total)

                try:
                    generate_segment_mp4(seg, out_path, tmp_path, style_settings=style_settings)

                    if has_any_sound:
                        sound_path = emphasis_sound_paths.get(seg.emphasis)
                        with_sound_path = tmp_path / f"ugoku_telop_{seg.index:03d}_with_sound.mp4"
                        attach_sound_to_mp4(
                            video_path=out_path,
                            output_path=with_sound_path,
                            sound_path=sound_path,
                            video_duration=seg.duration,
                            add_silent_track=(sound_path is None),
                        )
                        with_sound_path.replace(out_path)

                    mp4_paths.append(out_path)
                except Exception as e:
                    errors.append((seg.index, str(e)))
                    mp4_paths.append(out_path)

            progress_bar.progress(1.0)
            now = datetime.now().strftime("%Y%m%d_%H%M")
            result_payload = {
                "stamp": now,
                "errors": errors,
                "zip_bytes": None,
                "zip_name": None,
                "mp4_bytes": None,
                "mp4_name": None,
                "success_message": f"{len(segments) - len(errors)} / {len(segments)} セグメントの書き出しが完了しました。",
            }

            if export_mode in ("セグメントMP4をZIPでダウンロード", "両方生成する"):
                zip_name = f"ugoku_telop_script_{now}.zip"
                zip_path = tmp_path / zip_name
                progress_text.markdown("**ZIPファイルを作成中...**")
                status_text.markdown("編集用のZIPを書き出しています。")
                build_zip(segments, mp4_paths, script_input, zip_path, style_settings=style_settings)
                result_payload["zip_name"] = zip_name
                result_payload["zip_bytes"] = zip_path.read_bytes()

            if export_mode in ("1本のMP4動画としてダウンロード", "両方生成する"):
                mp4_name = f"ugoku_telop_script_{now}.mp4"
                progress_text.markdown("**1本MP4を結合中...**")
                status_text.markdown("確認用の1本MP4を生成しています。")
                merged_path = merge_segments_to_single_mp4(mp4_paths, tmp_path)
                final_path = tmp_path / mp4_name
                merged_path.replace(final_path)
                result_payload["mp4_name"] = mp4_name
                result_payload["mp4_bytes"] = final_path.read_bytes()

            progress_text.markdown("**✅ 書き出し完了**")
            status_text.markdown("ダウンロードの準備ができました。")
            if export_mode == "両方生成する":
                result_payload["success_message"] = f"{len(segments) - len(errors)} / {len(segments)} セグメントを生成し、ZIPと1本MP4の両方を用意しました。"
            elif export_mode == "1本のMP4動画としてダウンロード":
                result_payload["success_message"] = f"{len(segments) - len(errors)} / {len(segments)} セグメントを結合し、1本のMP4を生成しました。"

            st.session_state["export_result"] = result_payload
            st.rerun()

    st.markdown(
        """
        <div class="footer-note">
            生成した素材は、購入者本人のSNS投稿、YouTube、店舗動画、クライアントワークに利用できます。<br>
            ただし、生成素材を素材集として再販売することは禁止します。
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# tab2: アニメーション一覧
# ─────────────────────────────────────────────
with tab2:
    st.markdown(
        f"""
        <div class="list-hero">
            <div class="card-kicker">Animation Library</div>
            <div class="list-hero-title">アニメーション一覧</div>
            <div class="list-hero-text">
                現在実装されているテキストアニメーションを一覧で比較できます。<br>
                サンプルMP4をその場で生成して、動き・テンポ・雰囲気の違いを確認してください。
            </div>
            <div class="list-metrics">
                <span class="list-metric">{len(ANIMATION_PRESETS)} アニメーション</span>
                <span class="list-metric">MP4サンプル生成</span>
                <span class="list-metric">比較しやすいカード表示</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "animation_samples_zip" not in st.session_state:
        st.session_state["animation_samples_zip"] = None

    st.markdown(
        """
        <div class="action-card">
            <div class="action-card-title">一括サンプル生成</div>
            <div class="action-card-text">全アニメーションの比較用サンプルをまとめてZIPにできます。動きを一気に見比べたい時に便利です。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 全サンプル一括ZIP生成 ──
    if st.button("📦 全アニメーションのサンプルをZIPで生成", width="stretch"):
        import zipfile
        all_errors: list[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            zip_path = tmp_path / "animation_samples.zip"
            prog = st.progress(0)
            stat = st.empty()
            presets_list = list(ANIMATION_PRESETS.items())
            with zipfile.ZipFile(zip_path, "w") as zf:
                for idx, (key, preset) in enumerate(presets_list):
                    stat.markdown(f"🎞️ **{preset['label']}** を生成中...")
                    prog.progress(idx / len(presets_list))
                    out_mp4 = tmp_path / f"animation_sample_{key}.mp4"
                    try:
                        seg = parse_script(
                            preset["sample_text"],
                            animation_mode=key,
                        )[0]
                        generate_segment_mp4(seg, out_mp4, tmp_path)
                        if out_mp4.exists() and out_mp4.stat().st_size > 0:
                            zf.write(out_mp4, f"animation_sample_{key}.mp4")
                        else:
                            all_errors.append(preset["label"])
                    except Exception:
                        all_errors.append(preset["label"])
            prog.progress(1.0)
            stat.empty()
            if all_errors:
                st.warning(f"以下のアニメーションの生成に失敗しました：{', '.join(all_errors)}")
            zip_bytes = zip_path.read_bytes()
            st.session_state["animation_samples_zip"] = zip_bytes
            st.success("✅ 全サンプルのZIPが完成しました！")

    if st.session_state.get("animation_samples_zip"):
        st.download_button(
            label="📥 animation_samples.zip をダウンロード",
            data=st.session_state["animation_samples_zip"],
            file_name="animation_samples.zip",
            mime="application/zip",
            width="stretch",
        )

    if "animation_sample_bytes" not in st.session_state:
        st.session_state["animation_sample_bytes"] = {}

    # ── カード一覧（2カラム） ──
    preset_items = list(ANIMATION_PRESETS.items())
    for row_start in range(0, len(preset_items), 2):
        cols = st.columns(2)
        for col_idx, (key, preset) in enumerate(preset_items[row_start:row_start + 2]):
            with cols[col_idx]:
                # カードHTML
                tags_html = "".join(
                    f'<span class="anim-tag">{t.strip()}</span>'
                    for t in preset["recommended_use"].split("/")
                )
                st.markdown(
                    f"""
                    <div class="anim-card">
                        <div class="anim-label">{preset['label']}</div>
                        <div class="anim-internal">{key}</div>
                        <div class="anim-desc">{preset['description']}</div>
                        <div class="anim-meta-label">おすすめ用途</div>
                        <div class="anim-tags">{tags_html}</div>
                        <div class="anim-sample">サンプル：{preset['sample_text']}</div>
                        <div class="anim-meta-label">おすすめ強調：{preset['recommended_emphasis']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.button(
                    "このアニメーションでMP4を生成",
                    key=f"gen_{key}",
                    width="stretch",
                ):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        tmp_path = Path(tmpdir)
                        out_mp4 = tmp_path / f"animation_sample_{key}.mp4"
                        try:
                            seg = parse_script(
                                preset["sample_text"],
                                animation_mode=key,
                            )[0]
                            generate_segment_mp4(seg, out_mp4, tmp_path)
                            if not out_mp4.exists() or out_mp4.stat().st_size == 0:
                                raise RuntimeError("生成されたファイルが空です")
                            mp4_bytes = out_mp4.read_bytes()
                            st.session_state["animation_sample_bytes"][key] = mp4_bytes
                            st.success(f"✅ {preset['label']} のサンプルを生成しました！")
                        except Exception as e:
                            st.error(f"{preset['label']} の生成に失敗しました。\n{e}")

                saved_mp4 = st.session_state["animation_sample_bytes"].get(key)
                if saved_mp4:
                    st.markdown("<div class='anim-result'>", unsafe_allow_html=True)
                    st.video(saved_mp4)
                    st.download_button(
                        label=f"📥 animation_sample_{key}.mp4 をダウンロード",
                        data=saved_mp4,
                        file_name=f"animation_sample_{key}.mp4",
                        mime="video/mp4",
                        key=f"dl_{key}",
                        width="stretch",
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
