# 動くテロップメーカー Pro

台本を貼り付けるだけで、リール・ショート動画用の **MP4テロップ素材を一括生成** できるローカルWebアプリです。

---

## 1. アプリ概要

- 台本を空行ごとにセグメントに分割し、各テロップをMP4動画として生成します
- 生成されたMP4はZIPファイルにまとめてダウンロードできます
- CapCut / Premiere Pro / DaVinci Resolve などの動画編集ソフトで使用できます
- 背景はグリーンバック（RGB 0,255,0）固定。クロマキーで緑を抜いて使用してください

### 強調マーク

| 記法 | 効果 |
|------|------|
| `*テキスト*` | 軽く強調（やわらかく大きめに表示） |
| `**テキスト**` | 強く強調（ポップに表示） |
| `!!テキスト!!` | 大きく強調（インパクトある表示） |
| マークなし | 通常テキスト（ふわっとフェードイン） |

---

## 2. 必要環境

- Python 3.10 以上
- FFmpeg（別途インストールが必要）
- 各種Pythonライブラリ（requirements.txt 参照）

---

## 3. FFmpegのインストール方法

### macOS（Homebrew）
```bash
brew install ffmpeg
```

### Windows
1. [FFmpeg公式サイト](https://ffmpeg.org/download.html) からWindows用バイナリをダウンロード
2. 解凍して `ffmpeg.exe` をPATHの通ったフォルダに配置
3. `ffmpeg -version` で確認

### Ubuntu / Debian
```bash
sudo apt update && sudo apt install ffmpeg
```

---

## 4. セットアップ手順

```bash
# 1. リポジトリのクローン（またはZIPを解凍）
cd ugoku_telop_pro

# 2. 仮想環境を作成
python3 -m venv venv

# 3. 仮想環境を有効化
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. 依存関係をインストール
pip install -r requirements.txt
```

---

## 5. 起動方法

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

---

## 6. 使い方

1. 台本をテキストエリアに貼り付けます（または「サンプル台本」ボタンを使用）
2. 強調したい言葉を `*テキスト*` / `**テキスト**` / `!!テキスト!!` で囲みます
3. 「MP4素材をZIPで生成」ボタンをクリックします
4. 生成完了後、「ZIPをダウンロード」ボタンでダウンロードします
5. ZIPを解凍し、`ugoku_telop_001.mp4` から順番に動画編集ソフトへ読み込みます

---

## 7. 注意点

- 最大 **30セグメント** まで対応しています（安定性のため）
- 30セグメントを超える場合は台本を分割してください
- 生成には1セグメントあたり数秒かかります
- フォント選択には `fonts` フォルダ内の実在フォントのみ表示されます
- FFmpegがインストールされていない場合はエラーになります

---

## フォント追加方法

`fonts` フォルダに `.ttf` / `.otf` フォントを配置すると、アプリ内で選択できるようになります。

初期対応フォント：
- Noto Serif JP
- M Plus 1p
- Zen Maru Gothic
- Dela Gothic One
- Rampart One
- Hachi Maru Pop
- Shippori Mincho B1
- Yusei Magic

### fonts フォルダへの配置例

```text
fonts/
├── NotoSerifJP-Bold.ttf
├── MPLUS1p-Bold.ttf
├── ZenMaruGothic-Bold.ttf
├── DelaGothicOne-Regular.ttf
├── RampartOne-Regular.ttf
├── HachiMaruPop-Regular.ttf
├── ShipporiMinchoB1-Regular.ttf
└── YuseiMagic-Regular.ttf
```

> 注意: アプリ上には、`fonts` フォルダ内に実在するフォントだけが表示されます。

---

## 縦書きについて

縦書きは短い言葉向けです。  
長い文章では横書きを推奨します。

---

## 文字の縦横比

文字の横幅・縦幅を調整できます。  
ただし、極端な設定では文字が読みにくくなる可能性があります。

---

## 8. ディレクトリ構成

```
ugoku_telop_pro/
├── app.py                  ← Streamlit メインアプリ
├── engine.py               ← 台本パーサー・アニメーション・MP4生成ロジック
├── requirements.txt        ← Pythonライブラリ一覧
├── README.md               ← このファイル
├── fonts/
│   ├── NotoSerifJP-Bold.ttf
│   ├── MPLUS1p-Bold.ttf
│   ├── ZenMaruGothic-Bold.ttf
│   ├── DelaGothicOne-Regular.ttf
│   ├── RampartOne-Regular.ttf
│   ├── HachiMaruPop-Regular.ttf
│   ├── ShipporiMinchoB1-Regular.ttf
│   └── YuseiMagic-Regular.ttf
├── outputs/                ← 出力先（自動作成）
├── temp/                   ← 一時ファイル（自動作成・自動削除）
└── sample_scripts/
    ├── oshare.txt          ← おしゃれリール用サンプル
    ├── beauty.txt          ← 美容リール用サンプル
    └── shorts.txt          ← ショート動画用サンプル
```

---

## 9. 今後の拡張案

- [ ] フォントサイズ・表示時間をUI上で調整できるようにする
- [ ] 背景色の選択（グリーンバック以外）
- [ ] 縦書きテキスト対応
- [ ] 16:9 / 1:1 など複数アスペクト比対応
- [ ] アニメーション種類をセグメントごとに選択できるようにする
- [ ] プレビュー機能（生成前に各セグメントの静止画確認）
- [ ] FastAPI版への移行（より高速な非同期処理）

---

## 商用利用について

このツールで生成した素材は、購入者本人のSNS投稿、YouTube動画、店舗SNS、クライアントワークなどに利用できます。  
ただし、生成した素材を素材集として再販売することは禁止します。

---

## パスワード認証について

このアプリはBOOTH購入者向けの簡易パスワード認証に対応しています。

ローカル開発時は、デフォルトで以下のパスワードを使用します。

TelopPro_2026_B7Q

本番環境では、Streamlit CloudのSecretsにAPP_PASSWORDを設定してください。

例：

APP_PASSWORD = "TelopPro_2026_B7Q"

本番パスワードはGitHub上のコードに直接書かないでください。

## Streamlit CloudでのSecrets設定

1. Streamlit Cloudでアプリを開く
2. App settingsを開く
3. Secretsに以下を追加する

APP_PASSWORD = "TelopPro_2026_B7Q"

4. アプリを再起動する
