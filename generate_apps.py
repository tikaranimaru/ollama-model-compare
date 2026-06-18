#!/usr/bin/env python3
"""各gemma4モデルに4課題のHTMLを生成させ out/<model>/<task>.html に保存。
- thinking有効で生成。done_reason=='length'(出力切れ)ならthink無効で1回リトライ。
- 速度メトリクス(gen tok/s等)を out/metrics.json に追記保存。
使い方: python3 generate_apps.py <model1> <model2> ...
        引数なしなら既定の全7モデルを対象。
"""
import json, os, re, sys, time, urllib.request, subprocess

API = "http://localhost:11434/api/generate"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
PROMPTS = os.path.join(ROOT, "prompts")

DEFAULT_MODELS = [
    "gemma4:31b-mlx", "gemma4:31b", "gemma4:31b-mxfp8",
    "gemma4:26b-mlx", "gemma4:26b-mxfp8",
    "gemma4:12b-mxfp8", "gemma4:31b-coding-mtp-bf16",
]
TASKS = [
    ("lv1_landing", "lv1_landing.txt"),
    ("lv2_spiro",   "lv2_spiro.txt"),
    ("lv3_cube",    "lv3_cube.txt"),
    ("lv4_gantt",   "lv4_gantt.txt"),
    ("lv5_cloth",   "lv5_cloth.txt"),
]
NUM_PREDICT = 16000

def safe(m): return m.replace(":", "_").replace("/", "_")

def installed(model):
    out = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout
    return any(l.split() and l.split()[0] == model for l in out.splitlines())

def call(model, prompt, think, num_predict=NUM_PREDICT):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "think": think,
                       "options": {"num_predict": num_predict, "temperature": 0}}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3300) as r:
        return json.load(r)

def extract_html(text):
    blocks = re.findall(r"```(?:html)?\s*(.*?)```", text, re.DOTALL)
    if blocks:
        return blocks[-1].strip()
    i = text.lower().find("<!doctype")
    if i < 0: i = text.lower().find("<html")
    return text[i:].strip() if i >= 0 else text.strip()

def log_metric(rec):
    path = os.path.join(OUT, "metrics.json")
    data = []
    if os.path.exists(path):
        try: data = json.load(open(path))
        except Exception: data = []
    data.append(rec)
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)

def main():
    models = sys.argv[1:] or DEFAULT_MODELS
    for m in models:
        if not installed(m):
            print(f"[skip] {m} 未pull", flush=True); continue
        d = os.path.join(OUT, safe(m)); os.makedirs(d, exist_ok=True)
        try: call(m, "hi", False, num_predict=1)  # warmup（1トークンのみ）
        except Exception as e: print(f"[warn] {m} warmup: {e}", flush=True)
        for task, pf in TASKS:
            dst = os.path.join(d, f"{task}.html")
            if os.path.exists(dst) and os.path.getsize(dst) > 500:
                print(f"[have] {m} {task}", flush=True); continue
            prompt = open(os.path.join(PROMPTS, pf)).read()
            # codingモデルはbf16で低速＆コード特化のため思考無効（自然終了で高速化）＆上限を絞る
            want_think = "coding" not in m
            npred = 9000 if "coding" in m else NUM_PREDICT
            t0 = time.time(); think = want_think
            try:
                resp = call(m, prompt, think=want_think, num_predict=npred)
                if want_think and resp.get("done_reason") == "length":  # 出力切れ→思考なしで再生成
                    print(f"[retry] {m} {task} (length, think off)", flush=True)
                    think = False; resp = call(m, prompt, think=False, num_predict=npred)
            except Exception as e:
                print(f"[ERR] {m} {task}: {e}", flush=True); continue
            html = extract_html(resp.get("response", ""))
            open(dst, "w").write(html)
            dur = time.time() - t0
            gt, gd = resp.get("eval_count", 0), resp.get("eval_duration", 0)
            tps = gt/(gd/1e9) if gd else 0
            log_metric({"model": m, "task": task, "think": think,
                        "gen_tokens": gt, "gen_tps": round(tps, 1),
                        "wall_s": round(dur, 1), "bytes": len(html),
                        "done": resp.get("done_reason")})
            print(f"[ok]   {m} {task}: {tps:.1f} tok/s, {dur:.0f}s, {len(html)}B, {resp.get('done_reason')}", flush=True)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
