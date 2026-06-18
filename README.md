# ollama-model-compare

ローカルLLM（[Ollama](https://ollama.com/)）の**複数モデルを、同一のプロンプト集で解かせて見比べる**ための汎用ハーネス。
各モデルに同じお題（フロントエンド課題・コード生成など）を渡してHTML等を生成させ、`<iframe>` で並べて挙動を比較し、生成速度（tok/s）も計測する。

gemma4 に限らず、qwen など**任意のモデル群**を比較できる。比較セットは1ディレクトリ＝1比較として束ねる。

## 構成

```
scripts/            共有の汎用スクリプト（依存: Python3標準ライブラリ + Ollama のみ）
  generate.py         各モデル × 各プロンプトで生成し out/<model>/<task>.<ext> に保存＋速度記録
  build_compare.py    out/ を走査して compare.html（iframe比較ページ）を生成
  bench.sh            Ollama API直叩きの純粋な速度ベンチ
gemma4/             比較セット例：gemma4系7モデル × フロントエンド5課題
  prompts/            お題（1課題 = 1.txt）
  out/                生成物 + metrics.json
  compare.html        比較ページ
  README.md           この比較の結果と所感
```

## 既存の比較

- [**gemma4/**](gemma4/) — gemma4系7モデル（e2b〜31b、MoE/密、nvfp4/mxfp8/GGUF）× 5課題（LP・スピログラフ・3D立方体・ガント・布シミュ）。
  結論: **MoE(26b)が速度の勝者**、31B密は量子化を問わず低速。詳細は [gemma4/README.md](gemma4/README.md)。

## 新しい比較を追加する

```bash
# 1) 比較セットのディレクトリを作り、お題を置く（1課題 = 1.txt、出力形式を明記すること）
mkdir -p qwen3/prompts
$EDITOR qwen3/prompts/lv1_landing.txt   # 「```html ブロックで単一HTMLを出力。説明不要」等

# 2) 生成（要 Ollama・対象モデルは事前に ollama pull）
cd qwen3
python3 ../scripts/generate.py --models qwen3.5:27b qwen3.5:9b \
    --prompts-dir prompts --out-dir out --ext html

# 3) 比較ページを生成して開く
python3 ../scripts/build_compare.py --out-dir out --ext html --title "qwen3 比較"
open compare.html        # 各セルをクリックで実寸フルページへ遷移

# 4) （任意）純粋な速度ベンチ
bash ../scripts/bench.sh qwen3.5:27b qwen3.5:9b
```

`generate.py` は冪等（既存ファイルはスキップ）なので、中断しても再実行で続きから埋まる。
速度集計は `out/metrics.json` をモデル別に平均すればよい。

## 落とし穴（実運用の教訓）

- **MoEはタグの総パラメータ数と速度が乖離**する（速度は活性パラメータで決まる）。
- **thinkingモデル**は `num_predict` 不足で可視応答が空になる → 十分大きく取る or think無効。
- ウォームアップで `num_predict` を大きくすると暴走する（`generate.py` は1に固定済み）。
- 新しい量子化（`*-it-qat` 等）は**古いOllamaで pull 不可（412 / 要アップデート）**。
- **bf16の大型モデルは実用外の遅さ**＋`ollama ps` が "Stopping..." で固まる表示バグあり（小リクエストで新ランナー起動すると解消）。
- **単一GPUでは並行生成しても合計時間は不変**。逐次実行が基本。

> このワークフローは Claude Code の Skill `ollama-model-compare` としても利用可能（同等のスクリプトと教訓を同梱）。
