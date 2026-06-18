#!/usr/bin/env bash
# Gemma系モデルの速度ベンチ。Ollama API を直接叩いて精密なメトリクスを取る。
set -euo pipefail

API=http://localhost:11434/api/generate
MODELS=("gemma4:31b-mlx" "gemma4:26b-mlx" "gemma4:31b")

# 生成量を揃えるため num_predict を固定。temperature 0 で再現性確保。
PROMPT="Explain how a transformer neural network works, step by step, in detail."
NUM_PREDICT=300

ns_to_s() { awk "BEGIN{printf \"%.2f\", $1/1000000000}"; }
tps()    { awk "BEGIN{printf \"%.1f\", $1/($2/1000000000)}"; }

printf "%-18s %8s %8s %10s %10s %8s\n" "MODEL" "load(s)" "ppTok" "pp tok/s" "gen tok/s" "genTok"
printf "%s\n" "--------------------------------------------------------------------------"

for m in "${MODELS[@]}"; do
  # ウォームアップ（モデルをメモリにロード）
  curl -s "$API" -d "{\"model\":\"$m\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":1}}" >/dev/null

  # 本計測
  resp=$(curl -s "$API" -d "{\"model\":\"$m\",\"prompt\":\"$PROMPT\",\"stream\":false,\"options\":{\"num_predict\":$NUM_PREDICT,\"temperature\":0}}")

  load=$(echo "$resp"      | python3 -c 'import sys,json;print(json.load(sys.stdin).get("load_duration",0))')
  pp_n=$(echo "$resp"      | python3 -c 'import sys,json;print(json.load(sys.stdin).get("prompt_eval_count",0))')
  pp_d=$(echo "$resp"      | python3 -c 'import sys,json;print(json.load(sys.stdin).get("prompt_eval_duration",1))')
  gen_n=$(echo "$resp"     | python3 -c 'import sys,json;print(json.load(sys.stdin).get("eval_count",0))')
  gen_d=$(echo "$resp"     | python3 -c 'import sys,json;print(json.load(sys.stdin).get("eval_duration",1))')

  printf "%-18s %8s %8s %10s %10s %8s\n" \
    "$m" "$(ns_to_s "$load")" "$pp_n" "$(tps "$pp_n" "$pp_d")" "$(tps "$gen_n" "$gen_d")" "$gen_n"
done
