---
name: ollama-model-compare
description: Ollamaのローカルモデル複数を、同一のプロンプト集（フロントエンド課題やコード生成など）で解かせて成果物を生成し、iframeで並べて挙動を比較しつつ生成速度(tok/s)も計測するワークフロー。「Ollamaのモデルを比較したい」「複数モデルで同じお題を生成して見比べたい」「ローカルLLMの速度とコーディング能力を測りたい」「gemma/qwen等のモデル比較」のときに使う。HTML/canvasアプリの生成比較に最適。
---

# Ollama モデル比較ワークフロー

複数のローカルモデル（Ollama）に**同一のプロンプト集**を解かせ、生成物を `out/<model>/<task>.<ext>` に保存し、`compare.html` で**課題ごとに全モデルを横並び**にして比較する。生成速度（tok/s・秒/課題）も `out/metrics.json` に記録する。HTML/canvasアプリの生成（ランディングページ・3D・物理シミュ等）で特に有効。

## 前提

- Ollama が起動していること（`curl -s http://localhost:11434/api/version`）。
- 比較対象モデルが pull 済みであること（`ollama list` で確認、無ければ `ollama pull <model>`）。
- スクリプトは Python3 標準ライブラリのみで動く（追加依存なし）。
- `scripts/` のパスはこのSKILLディレクトリ基準。作業ディレクトリへコピーして使ってもよい。

## 手順

### 1. お題（プロンプト集）を用意

`prompts/` ディレクトリを作り、**1課題 = 1ファイル `<task>.txt`** として置く。ファイル名（拡張子なし）が課題名になる。
各プロンプトには「単一の自己完結HTMLを ```html ブロックで出力。説明文不要」のような**出力形式の指定**を必ず入れる（抽出が安定する）。`prompts.example/` にサンプルあり。

### 2. 生成

```bash
python3 scripts/generate.py \
  --models gemma4:26b-mxfp8 gemma4:12b-mxfp8 gemma4:e2b-nvfp4 \
  --prompts-dir prompts --out-dir out --ext html
```

- 既存ファイルはスキップ（冪等）。中断しても再実行で続きから。
- thinkingモデル対応：出力切れ(length)時は think 無効で自動再生成。
- bf16/コード特化など暴走・超低速モデルは `--no-think-substr coding` 等で think無効＆上限を絞る（既定で `coding` を含む）。
- **長時間になる**ため、原則 background 実行＋ログを Monitor で追う。`out/metrics.json` に速度が貯まる。

### 3. 比較ページを生成して開く

```bash
python3 scripts/build_compare.py --out-dir out --ext html --title "モデル比較"
open compare.html   # 各セルをクリックで実寸フルページへ遷移して操作確認
```

生成中に進捗を見たい場合は、20秒ごとに `build_compare.py` を回す簡易ループを background で走らせる（未完成の間は自動リロードが入る）。

### 4. 速度ベンチ（任意・純粋なtok/s）

```bash
bash scripts/bench.sh gemma4:26b-mxfp8 gemma4:12b-mxfp8
```

実アプリ生成の実効tok/sは `out/metrics.json` に、短文ピークtok/sは `bench.sh` に出る（両者は乖離する＝[後述](reference.md)）。

### 5. まとめ

`out/metrics.json` をモデル別に集計し、速度表＋各課題の所感（挙動の正しさは目視）を出す。集計例:

```bash
python3 - <<'PY'
import json,collections
d=json.load(open('out/metrics.json')); a=collections.defaultdict(list)
for r in d: a[r['model']].append(r)
for m,rs in a.items():
    print(f"{m:<28}{sum(x['gen_tps'] for x in rs)/len(rs):6.1f} tok/s  {sum(x['wall_s'] for x in rs)/len(rs):6.0f} s/課題")
PY
```

## 重要な落とし穴（必ず `reference.md` を読む）

- MoEモデルはタグの総パラメータ数と実速度が乖離する（活性パラメータで決まる）
- thinkingモデルは num_predict 不足だと可視応答が空になる
- ウォームアップを num_predict 大のままにすると暴走する（本スクリプトは1に固定済み）
- 新しい量子化（qat等）は古いOllamaで pull 不可（412）
- bf16の大型モデルは実用外の遅さ＋`ollama ps`の"Stopping..."ハング表示

詳細と対処は [reference.md](reference.md) を参照。

## 出力物

```
prompts/         お題（1課題=1.txt）
out/<model>/<task>.<ext>   生成物
out/metrics.json           速度メトリクス
compare.html               iframe比較ページ
```
