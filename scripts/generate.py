#!/usr/bin/env python3
"""Ollamaの複数モデルに同一プロンプト集を解かせ、生成物を out/<model>/<task>.<ext> に保存。
速度メトリクスを out/metrics.json に追記する。

使い方:
  python3 generate.py --models gemma4:26b-mxfp8 gemma4:12b-mxfp8 \
      --prompts-dir prompts --out-dir out --ext html

特徴/教訓を反映:
  - ウォームアップは num_predict=1（"hi"に延々応答する暴走を防ぐ）
  - thinkingモデルは num_predict 不足だと可視応答が空になるため、出力切れ(length)時は think 無効で再生成
  - --no-think-substr に一致するモデル(例: coding)は最初から think 無効＆上限を絞る（bf16の暴走/超低速対策）
  - 既存ファイルはスキップ（冪等）。中断後の再実行で続きから埋まる
"""
import argparse, json, os, re, sys, time, urllib.request, subprocess


def installed(model):
    out = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout
    return any(l.split() and l.split()[0] == model for l in out.splitlines())


def call(api, model, prompt, think, num_predict, timeout):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "think": think,
                       "options": {"num_predict": num_predict, "temperature": 0}}).encode()
    req = urllib.request.Request(api, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def extract(text, ext):
    """```lang ...``` の最後のブロックを抽出。無ければHTMLは<!doctype/<html以降、他は全文。"""
    blocks = re.findall(r"```(?:[a-zA-Z0-9]+)?\s*(.*?)```", text, re.DOTALL)
    if blocks:
        return blocks[-1].strip()
    if ext == "html":
        i = text.lower().find("<!doctype")
        if i < 0:
            i = text.lower().find("<html")
        if i >= 0:
            return text[i:].strip()
    return text.strip()


def safe(m):
    return m.replace(":", "_").replace("/", "_")


def log_metric(out_dir, rec):
    path = os.path.join(out_dir, "metrics.json")
    data = []
    if os.path.exists(path):
        try:
            data = json.load(open(path))
        except Exception:
            data = []
    data.append(rec)
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--prompts-dir", default="prompts")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--ext", default="html")
    ap.add_argument("--api", default="http://localhost:11434/api/generate")
    ap.add_argument("--num-predict", type=int, default=16000)
    ap.add_argument("--no-think", action="store_true", help="全モデルで思考無効")
    ap.add_argument("--no-think-substr", nargs="*", default=["coding"],
                    help="この部分文字列を含むモデルは思考無効＆上限を絞る")
    ap.add_argument("--capped-num-predict", type=int, default=9000,
                    help="no-think-substr一致モデルの上限")
    ap.add_argument("--timeout", type=int, default=3300)
    args = ap.parse_args()

    tasks = sorted(f for f in os.listdir(args.prompts_dir) if f.endswith(".txt"))
    if not tasks:
        print(f"プロンプトが {args.prompts_dir}/*.txt に見つかりません", file=sys.stderr)
        sys.exit(1)

    for m in args.models:
        if not installed(m):
            print(f"[skip] {m} 未pull", flush=True)
            continue
        d = os.path.join(args.out_dir, safe(m))
        os.makedirs(d, exist_ok=True)
        try:
            call(args.api, m, "hi", False, 1, 120)  # warmup（1トークン）
        except Exception as e:
            print(f"[warn] {m} warmup: {e}", flush=True)

        capped = any(s and s in m for s in args.no_think_substr)
        want_think = not (args.no_think or capped)
        npred = args.capped_num_predict if capped else args.num_predict

        for tf in tasks:
            task = tf[:-4]
            dst = os.path.join(d, f"{task}.{args.ext}")
            if os.path.exists(dst) and os.path.getsize(dst) > 200:
                print(f"[have] {m} {task}", flush=True)
                continue
            prompt = open(os.path.join(args.prompts_dir, tf)).read()
            t0 = time.time()
            think = want_think
            try:
                resp = call(args.api, m, prompt, want_think, npred, args.timeout)
                if want_think and resp.get("done_reason") == "length":
                    print(f"[retry] {m} {task} (length, think off)", flush=True)
                    think = False
                    resp = call(args.api, m, prompt, False, npred, args.timeout)
            except Exception as e:
                print(f"[ERR] {m} {task}: {e}", flush=True)
                continue
            content = extract(resp.get("response", ""), args.ext)
            open(dst, "w").write(content)
            dur = time.time() - t0
            gt, gd = resp.get("eval_count", 0), resp.get("eval_duration", 0)
            tps = gt / (gd / 1e9) if gd else 0
            log_metric(args.out_dir, {"model": m, "task": task, "think": think,
                                      "gen_tokens": gt, "gen_tps": round(tps, 1),
                                      "wall_s": round(dur, 1), "bytes": len(content),
                                      "done": resp.get("done_reason")})
            print(f"[ok]   {m} {task}: {tps:.1f} tok/s, {dur:.0f}s, {len(content)}B, {resp.get('done_reason')}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
