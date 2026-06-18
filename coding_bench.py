#!/usr/bin/env python3
"""gemma4各モデルのコーディング能力を自動採点。
生成されたPythonコードを実際に実行し、テストケースの通過数で評価する。
速度(gen tok/s)も同時計測。thinkは有効化して品質を引き出す。"""
import json, re, time, urllib.request, sys

API = "http://localhost:11434/api/generate"

MODELS = [
    "gemma4:31b-mlx", "gemma4:31b", "gemma4:31b-mxfp8",
    "gemma4:26b-mlx", "gemma4:26b-mxfp8",
    "gemma4:12b-mxfp8", "gemma4:31b-coding-mtp-bf16",
]

# (関数名, 問題文, テストケース[(引数tuple, 期待値)])
TASKS = [
    ("is_valid", "Write a Python function `is_valid(s)` that returns True if the string of brackets '()[]{}' is valid (properly nested and matched), else False. Return only a ```python code block.",
     [(("()",), True), (("()[]{}",), True), (("(]",), False), (("([)]",), False), (("{[]}",), True), (("",), True), (("(",), False)]),
    ("merge_intervals", "Write a Python function `merge_intervals(intervals)` that merges all overlapping intervals (list of [start,end]) and returns the merged list sorted by start. Return only a ```python code block.",
     [(([[1,3],[2,6],[8,10],[15,18]],), [[1,6],[8,10],[15,18]]), (([[1,4],[4,5]],), [[1,5]]), (([[1,4],[2,3]],), [[1,4]]), (([],), [])]),
    ("lengthOfLIS", "Write a Python function `lengthOfLIS(nums)` returning the length of the longest strictly increasing subsequence. Return only a ```python code block.",
     [(([10,9,2,5,3,7,101,18],), 4), (([0,1,0,3,2,3],), 4), (([7,7,7,7],), 1), (([],), 0)]),
    ("word_break", "Write a Python function `word_break(s, words)` that returns True if s can be segmented into a space-separated sequence of one or more words from the list `words`. Return only a ```python code block.",
     [(("leetcode",["leet","code"]), True), (("applepenapple",["apple","pen"]), True), (("catsandog",["cats","dog","sand","and","cat"]), False)]),
]

def call(model, prompt, num_predict=2048):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "think": True, "options": {"num_predict": num_predict, "temperature": 0}}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)

def extract_code(text):
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return blocks[-1] if blocks else text

def grade(code, fname, cases):
    ns = {}
    try:
        exec(code, ns)
    except Exception as e:
        return 0, len(cases), f"exec error: {e}"
    fn = ns.get(fname)
    if not callable(fn):
        return 0, len(cases), f"no func {fname}"
    passed = 0
    for args, expected in cases:
        try:
            got = fn(*args)
            if got == expected:
                passed += 1
        except Exception:
            pass
    return passed, len(cases), "ok"

def installed(model):
    import subprocess
    out = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout
    return any(line.split() and line.split()[0] == model for line in out.splitlines())

def main():
    print(f"{'MODEL':<30}{'pass':>8}{'gen tok/s':>11}{'time(s)':>9}")
    print("-" * 58)
    for m in MODELS:
        if not installed(m):
            print(f"{m:<30}{'(未pull)':>8}")
            continue
        try:
            call(m, "hi", 1)  # warmup
        except Exception as e:
            print(f"{m:<30} warmup失敗: {e}"); continue
        total_pass = total_cases = 0
        gen_tok = gen_dur = 0
        t0 = time.time()
        details = []
        for fname, prompt, cases in TASKS:
            try:
                resp = call(m, prompt)
            except Exception as e:
                details.append(f"{fname}:ERR"); total_cases += len(cases); continue
            code = extract_code(resp.get("response", ""))
            p, n, _ = grade(code, fname, cases)
            total_pass += p; total_cases += n
            gen_tok += resp.get("eval_count", 0); gen_dur += resp.get("eval_duration", 0)
            details.append(f"{fname}:{p}/{n}")
        elapsed = time.time() - t0
        tps = gen_tok / (gen_dur / 1e9) if gen_dur else 0
        print(f"{m:<30}{f'{total_pass}/{total_cases}':>8}{tps:>11.1f}{elapsed:>9.1f}   " + "  ".join(details))
    print("\n(注: thinking有効・各タスクnum_predict=2048。pass=実行して通過したテスト数)")

if __name__ == "__main__":
    main()
