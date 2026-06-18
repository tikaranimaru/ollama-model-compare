#!/usr/bin/env bash
# Ollama各モデルの純粋な速度ベンチ。API直叩きで生成tok/s・プロンプト処理tok/sを測る。
# ウォームアップ後に計測（ロード時間は除外）。同一プロンプト2回目以降はKVキャッシュで
# pp tok/s が跳ねるため、pp は冷値（初回）のみ信頼できる。
#
# 使い方: bash bench.sh gemma4:26b-mxfp8 gemma4:12b-mxfp8 ...
set -euo pipefail
API=http://localhost:11434/api/generate
MODELS=("$@")
[ ${#MODELS[@]} -eq 0 ] && { echo "usage: bash bench.sh <model> [<model>...]"; exit 1; }

PROMPT="Explain how a transformer neural network works, step by step, in detail."
NUM_PREDICT=300

tps() { awk "BEGIN{if($2>0)printf \"%.1f\", $1/($2/1000000000); else print \"NA\"}"; }

printf "%-28s %10s %10s %8s\n" "MODEL" "pp tok/s" "gen tok/s" "genTok"
printf "%s\n" "------------------------------------------------------------"
for m in "${MODELS[@]}"; do
  curl -s "$API" -d "{\"model\":\"$m\",\"prompt\":\"hi\",\"stream\":false,\"think\":false,\"options\":{\"num_predict\":1}}" >/dev/null
  resp=$(python3 -c "import json;print(json.dumps({'model':'$m','prompt':'''$PROMPT''','stream':False,'think':False,'options':{'num_predict':$NUM_PREDICT,'temperature':0}}))" | curl -s "$API" --data @-)
  pp_n=$(echo "$resp" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("prompt_eval_count",0))')
  pp_d=$(echo "$resp" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("prompt_eval_duration",0))')
  g_n=$(echo "$resp"  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("eval_count",0))')
  g_d=$(echo "$resp"  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("eval_duration",0))')
  printf "%-28s %10s %10s %8s\n" "$m" "$(tps "$pp_n" "$pp_d")" "$(tps "$g_n" "$g_d")" "$g_n"
done
