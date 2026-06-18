# gemma4 ローカルモデル比較（速度 × コーディング能力）

Apple M5 Max / 128GB・Ollama 上で **gemma4 系の各モデル**を、速度と実コーディング能力の両面で比較したワーク一式。
各モデルに同一のフロントエンド課題（5種）を生成させ、`<iframe>` で並べて挙動を見比べられる。

## 比較したモデル（7）

| モデル | 種別 | 量子化 | 備考 |
|---|---|---|---|
| `e2b-nvfp4` | edge 2B | nvfp4(4bit) | エッジ最小級 |
| `12b-mxfp8` | 12B 密 | mxfp8(8bit) | |
| `26b-mlx` | 26B **MoE**(活性≈4B) | nvfp4(4bit) | |
| `26b-mxfp8` | 26B **MoE**(活性≈4B) | mxfp8(8bit) | 実用本命 |
| `31b-mlx` | 31B 密 | nvfp4(4bit) | |
| `31b` | 31B 密 | Q4_K_M(GGUF) | |
| `31b-mxfp8` | 31B 密 | mxfp8(8bit) | |

> `31b-coding-mtp-bf16`(64GB bf16) は ~7 tok/s・1課題20分級で実用外のため除外。
> `e2b-it-qat` は Ollama 0.30.3 で pull 不可（412・要アップデート）のため除外。

## 課題（5）

- **Lv1 ランディングページ** … 逐語コピーのSaaS LP（構成・視覚階層）
- **Lv2 スピログラフ** … 媒介変数によるハイポトロコイド漸進描画（canvas）
- **Lv3 立方体** … 手書き3D数学＋陰面処理（canvas）
- **Lv4 ガントチャート** … 日付軸スケーリング・依存線・バーのドラッグ
- **Lv5 布シミュ** … Verlet積分＋距離拘束（canvas）

各課題の仕様は `prompts/` にある（モデルへ渡したプロンプトそのもの）。

## 速度結果（実アプリ生成・thinking有効時の実効 gen tok/s）

| モデル | 生成tok/s | 平均秒/課題 |
|---|---:|---:|
| e2b-nvfp4 | 59.1 | 62s |
| 26b-mlx (MoE) | 54.0 | 167s |
| 26b-mxfp8 (MoE) | 47.0 | 122s |
| 12b-mxfp8 | 19.1 | 239s |
| 31b (GGUF) | 9.4 | 406s |
| 31b-mlx | 9.2 | 417s |
| 31b-mxfp8 | 7.5 | 532s |

### 要点
- **MoE（`26b`系）が速度の勝者**。「26B級の容量 × 活性4B」で ~50 tok/s。密な `12b`(19) や `31b`(7〜9) を圧倒。
- **31B 密は量子化を問わず遅い**（7〜9 tok/s）。8bit(mxfp8)が最遅で、4bit比 約2割減＝品質とのトレードオフ。
- 同31Bで `mlx(nvfp4)` は `GGUF(Q4)` と同等〜やや速。
- **推奨**: 実用本命 `26b-mxfp8`／速度優先 `26b-mlx`・`e2b`。31B密はコスパ悪。

## 使い方

共有スクリプトはリポジトリ直下の `../scripts/` にある。このディレクトリ(`gemma4/`)内で実行する。

```bash
# 1) 比較ページを開く（生成済み成果物がそのまま見られる）
open compare.html        # 各セルをクリックで実寸フル操作の実ページへ遷移

# 2) 自分で生成し直す（要 Ollama + 対象モデルの pull）
python3 ../scripts/generate.py --models gemma4:26b-mxfp8 gemma4:12b-mxfp8 \
    --prompts-dir prompts --out-dir out --ext html
python3 ../scripts/build_compare.py --out-dir out --ext html \
    --title "gemma4 比較" --output compare.html

# 3) 速度ベンチ（純粋な tok/s 計測）
bash ../scripts/bench.sh gemma4:26b-mxfp8 gemma4:12b-mxfp8

# 4) 生成コードを実行して自動採点（参考・このディレクトリ固有の別ベンチ）
python3 coding_bench.py
```

## ファイル構成

```
prompts/        5課題のプロンプト（モデルへの入力そのもの）
out/            生成結果のHTML群 + metrics.json（速度メトリクス）
compare.html    生成済みの比較ページ
coding_bench.py 生成コードを実行して自動採点する別ベンチ（参考）
```

生成・比較・ベンチの共有スクリプトはリポジトリ直下の `scripts/` を参照。

計測環境: Apple M5 Max / 128GB unified memory / Ollama 0.30.3 / 2026-06。
