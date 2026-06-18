#!/usr/bin/env bash
# 各モデル3回計測して中央値傾向を見る。プロンプト処理速度も長文で測る。
set -euo pipefail
API=http://localhost:11434/api/generate
MODELS=("gemma4:31b-mlx" "gemma4:26b-mlx" "gemma4:31b")
NUM_PREDICT=400
REPEAT=3

# pp計測用に長めのプロンプト（約500語）
LONG=$(python3 -c 'print(("The quick brown fox jumps over the lazy dog. " * 80).strip())')
PROMPT="Summarize the following text in one sentence: $LONG"

tps() { awk "BEGIN{printf \"%.1f\", $1/($2/1000000000)}"; }

printf "%-18s %6s %10s %10s\n" "MODEL" "run" "pp tok/s" "gen tok/s"
printf "%s\n" "------------------------------------------------"
for m in "${MODELS[@]}"; do
  curl -s "$API" -d "{\"model\":\"$m\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":1}}" >/dev/null
  for i in $(seq 1 $REPEAT); do
    resp=$(curl -s "$API" --data @<(python3 -c "import json,sys;print(json.dumps({'model':'$m','prompt':'''$PROMPT''','stream':False,'options':{'num_predict':$NUM_PREDICT,'temperature':0}}))"))
    pp_n=$(echo "$resp"  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("prompt_eval_count",0))')
    pp_d=$(echo "$resp"  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("prompt_eval_duration",1))')
    g_n=$(echo "$resp"   | python3 -c 'import sys,json;print(json.load(sys.stdin).get("eval_count",0))')
    g_d=$(echo "$resp"   | python3 -c 'import sys,json;print(json.load(sys.stdin).get("eval_duration",1))')
    printf "%-18s %6s %10s %10s\n" "$m" "$i" "$(tps "$pp_n" "$pp_d")" "$(tps "$g_n" "$g_d")"
  done
done
