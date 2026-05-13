# animations.py — アニメーション定義一覧
# engine.py の描画処理と app.py の UI で共通利用する

from __future__ import annotations

ANIMATION_PRESETS: dict[str, dict] = {
    "no_effect": {
        "label": "No Effect",
        "internal": "no_effect",
        "description": "動かさず、そのまま表示するシンプルなエフェクトです。",
        "recommended_use": "美容リール / 上品な見せ方 / 静かな見出し / 比較用",
        "recommended_emphasis": "マークなし（通常）",
        "sample_text": "そのまま見せる",
    },
    "fade_up": {
        "label": "Fade Up",
        "internal": "fade_up",
        "description": "下からふわっと表示される、通常文向けの自然なアニメーション。",
        "recommended_use": "通常文 / おしゃれリール / 店舗紹介",
        "recommended_emphasis": "マークなし（通常）",
        "sample_text": "今日は少しだけ",
    },
    "soft_pop": {
        "label": "Soft Pop",
        "internal": "soft_pop",
        "description": "少しだけ拡大しながら表示される、軽い強調向けのアニメーション。",
        "recommended_use": "軽い強調 / 美容 / Vlog",
        "recommended_emphasis": "*軽く強調*",
        "sample_text": "やさしく言葉を添える",
    },
    "pop_in": {
        "label": "Pop In",
        "internal": "pop_in",
        "description": "ポンッと表示される、強調文向けのアニメーション。",
        "recommended_use": "強い強調 / ショート動画 / 見出し",
        "recommended_emphasis": "**強く強調**",
        "sample_text": "保存版",
    },
    "zoom_punch": {
        "label": "Zoom Punch",
        "internal": "zoom_punch",
        "description": "中央に強く表示される、大きな強調向けのアニメーション。",
        "recommended_use": "超強調 / フック / 保存訴求",
        "recommended_emphasis": "!!大きく強調!!",
        "sample_text": "知らなきゃ損",
    },
    "block_reveal": {
        "label": "Block Reveal",
        "internal": "block_reveal",
        "description": "四角いブロックが文字を隠しながら通過し、テキストが現れる演出。",
        "recommended_use": "見出し / 保存版 / 重要ワード / 店舗紹介",
        "recommended_emphasis": "強く強調 / 大きく強調",
        "sample_text": "保存版",
    },
    "terminal_type": {
        "label": "Terminal Type",
        "internal": "terminal_type",
        "description": "ターミナル入力のように一文字ずつ表示される、デジタル風の演出。",
        "recommended_use": "AI動画 / 解説動画 / テック系 / 伏線風テロップ",
        "recommended_emphasis": "通常文 / 軽く強調",
        "sample_text": "AI動画の弱点",
    },
    "color_shift": {
        "label": "Color Shift",
        "internal": "color_shift",
        "description": "文字色が時間とともに変化する、ポップで目を引く演出。",
        "recommended_use": "ショート動画 / ポップ系 / バズ系 / 強調テロップ",
        "recommended_emphasis": "強く強調 / 大きく強調",
        "sample_text": "一味違うリールに",
    },
    "focus_in": {
        "label": "Focus In",
        "internal": "focus_in",
        "description": "ぼけた文字にピントが合うように表示される、上品で使いやすい演出。",
        "recommended_use": "Vlog / 美容 / ドキュメンタリー / 余韻のある字幕",
        "recommended_emphasis": "通常文 / 軽く強調",
        "sample_text": "少しずつ形になる",
    },
    "huge_impact": {
        "label": "Huge Impact",
        "internal": "huge_impact",
        "description": "画面いっぱいに大きく表示する、インパクト重視のアニメーション。",
        "recommended_use": "ショート動画冒頭 / 決め台詞 / インパクト",
        "recommended_emphasis": "!!大きく強調!!",
        "sample_text": "一味違う動画に",
    },
    "stretch_in": {
        "label": "Stretch In",
        "internal": "stretch_in",
        "description": "文字が横に伸びながら登場する、力強い見出し向けのアニメーション。",
        "recommended_use": "見出し / スピード感 / 強い言葉",
        "recommended_emphasis": "**強く強調**",
        "sample_text": "編集時間を短縮",
    },
    "label_reveal": {
        "label": "Label Reveal",
        "internal": "label_reveal",
        "description": "背景ラベル付きで文字が出る、おしゃれな強調向けアニメーション。",
        "recommended_use": "美容 / おしゃれ / ラベル風テロップ",
        "recommended_emphasis": "*軽く強調*",
        "sample_text": "大人っぽく",
    },
    "letter_fade": {
        "label": "Letter Fade",
        "internal": "letter_fade",
        "description": "一文字ずつふわっと表示される、上品で読みやすいアニメーション。",
        "recommended_use": "通常文 / 上品 / 余白のある動画",
        "recommended_emphasis": "マークなし（通常）",
        "sample_text": "余白のあるリール",
    },
    "shake_accent": {
        "label": "Shake Accent",
        "internal": "shake_accent",
        "description": "一瞬だけ震えて強調する、驚きや注意喚起向けのアニメーション。",
        "recommended_use": "注意喚起 / 驚き / 知らなきゃ損系",
        "recommended_emphasis": "**強く強調**",
        "sample_text": "本当に大事",
    },
    "typewriter": {
        "label": "Typewriter",
        "internal": "typewriter",
        "description": "一文字ずつタイプされるように表示する、説明文やナレーション風のアニメーション。",
        "recommended_use": "説明文 / ナレーション / AI動画",
        "recommended_emphasis": "マークなし（通常）",
        "sample_text": "文字が動くだけで変わる",
    },
    "letter_drop": {
        "label": "Letter Drop",
        "internal": "letter_drop",
        "description": "一文字ずつ上から落下して表示される、ポップなアニメーション。",
        "recommended_use": "ポップ / 元気 / ショート動画",
        "recommended_emphasis": "**強く強調**",
        "sample_text": "ポップに登場",
    },
    "letter_rise": {
        "label": "Letter Rise",
        "internal": "letter_rise",
        "description": "一文字ずつ下から上昇して表示される、やわらかく上品なアニメーション。",
        "recommended_use": "美容 / Vlog / やわらかい雰囲気",
        "recommended_emphasis": "*軽く強調*",
        "sample_text": "ふわっと上がる",
    },
    "hacker_text": {
        "label": "Hacker Text",
        "internal": "hacker_text",
        "description": "ランダムな文字列から正しい文字へ変換される、AI・サイバー系アニメーション。",
        "recommended_use": "AI動画 / サイバー / 文字変換",
        "recommended_emphasis": "!!大きく強調!!",
        "sample_text": "AI動画の弱点",
    },
    "neon_flicker": {
        "label": "Neon Flicker",
        "internal": "neon_flicker",
        "description": "ネオンのように文字が一瞬チカチカ光る、夜・サイバー系のアニメーション。",
        "recommended_use": "夜 / サイバー / タイトル",
        "recommended_emphasis": "!!大きく強調!!",
        "sample_text": "夜に光る言葉",
    },
}

# 表示名 → 内部名 マッピング（selectbox 用）
LABEL_TO_INTERNAL: dict[str, str] = {
    v["label"]: k for k, v in ANIMATION_PRESETS.items()
}

PRESET_ANIMATION_MAP: dict[str, dict[str, str]] = {
    "スタイリッシュリール": {
        "normal": "focus_in",
        "light": "block_reveal",
        "strong": "letter_rise",
        "impact": "color_shift",
    },
    "美容リール": {
        "normal": "focus_in",
        "light": "letter_fade",
        "strong": "block_reveal",
        "impact": "soft_pop",
    },
    "ショート動画リール": {
        "normal": "fade_up",
        "light": "terminal_type",
        "strong": "block_reveal",
        "impact": "color_shift",
    },
}

PRESET_DESCRIPTIONS: dict[str, str] = {
    "スタイリッシュリール": "上品で余白のある、おしゃれな動きに最適",
    "美容リール": "やわらかく上品で、垢抜けた印象に最適",
    "ショート動画リール": "テンポ感と訴求力を重視した、強い動きに最適",
}

EMPHASIS_UI_ROWS: list[dict[str, str]] = [
    {
        "key": "normal",
        "title": "通常文",
        "notation": "マークなし",
        "sample": "今日は少しだけ",
    },
    {
        "key": "light",
        "title": "軽く強調",
        "notation": "*テキスト*",
        "sample": "*やさしく言葉を添える*",
    },
    {
        "key": "strong",
        "title": "強く強調",
        "notation": "**テキスト**",
        "sample": "**余白のあるテロップ**",
    },
    {
        "key": "impact",
        "title": "大きく強調",
        "notation": "!!テキスト!!",
        "sample": "!!一味違うリールに!!",
    },
]

ANIMATION_OPTIONS: dict[str, str] = {
    "no_effect": "No Effect｜エフェクトなし",
    "fade_up": "Fade Up｜下からふわっと表示",
    "soft_pop": "Soft Pop｜やわらかく拡大",
    "pop_in": "Pop In｜ポンッと表示",
    "zoom_punch": "Zoom Punch｜強くズーム",
    "block_reveal": "Block Reveal｜ブロック通過で表示",
    "terminal_type": "Terminal Type｜ターミナル風に入力",
    "color_shift": "Color Shift｜色が滑らかに変化",
    "focus_in": "Focus In｜ぼけからピントが合う",
    "huge_impact": "Huge Impact｜画面いっぱいに強調",
    "stretch_in": "Stretch In｜横に伸びて登場",
    "label_reveal": "Label Reveal｜背景ラベル付き",
    "letter_fade": "Letter Fade｜一文字ずつふわっと",
    "shake_accent": "Shake Accent｜一瞬だけ震える",
    "typewriter": "Typewriter｜一文字ずつ表示",
    "letter_drop": "Letter Drop｜上から落ちる",
    "letter_rise": "Letter Rise｜下から上がる",
    "hacker_text": "Hacker Text｜ランダム文字から変換",
    "neon_flicker": "Neon Flicker｜ネオンのように光る",
}

EMPHASIS_FALLBACK_MAP: dict[str, str] = {
    "normal": "fade_up",
    "light": "soft_pop",
    "strong": "pop_in",
    "impact": "zoom_punch",
}
