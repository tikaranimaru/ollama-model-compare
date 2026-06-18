#!/usr/bin/env python3
"""out/ を走査して compare.html を生成。課題ごとに全モデルの生成物をグリッド表示。
HTML成果物は iframe(900x600を縮小)で、クリックすると実寸フルページへ遷移する。

使い方:
  python3 build_compare.py --out-dir out --ext html --title "gemma4 比較"
  # 未完成セルがある間は自動リロード(meta refresh)を入れる。全部揃うと外す。
"""
import argparse, os, json


def safe(m):
    return m.replace(":", "_").replace("/", "_")


def metrics_map(out_dir):
    p = os.path.join(out_dir, "metrics.json")
    if not os.path.exists(p):
        return {}
    try:
        data = json.load(open(p))
    except Exception:
        return {}
    return {(r["model"], r["task"]): r for r in data}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--ext", default="html")
    ap.add_argument("--title", default="Ollama モデル比較")
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--w", type=int, default=900)
    ap.add_argument("--h", type=int, default=600)
    ap.add_argument("--output", default="compare.html")
    args = ap.parse_args()

    W, H, S = args.w, args.h, args.scale
    CW, CH = int(W * S), int(H * S)
    mm = metrics_map(args.out_dir)

    # モデル = out/ 直下のディレクトリ、課題 = その中の *.ext のstem（和集合）
    models = sorted(d for d in os.listdir(args.out_dir)
                    if os.path.isdir(os.path.join(args.out_dir, d)))
    tasks = set()
    for d in models:
        for f in os.listdir(os.path.join(args.out_dir, d)):
            if f.endswith("." + args.ext):
                tasks.add(f[:-(len(args.ext) + 1)])
    tasks = sorted(tasks)

    total = filled = 0
    for t in tasks:
        for d in models:
            total += 1
            f = os.path.join(args.out_dir, d, f"{t}.{args.ext}")
            if os.path.exists(f) and os.path.getsize(f) > 200:
                filled += 1
    refresh = '<meta http-equiv="refresh" content="25">' if filled < total else ''

    # safe()名 -> 元モデル名の逆引き（metrics照合用）
    inv = {}
    for (mdl, _t) in mm:
        inv[safe(mdl)] = mdl

    head = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
{refresh}
<title>{args.title}</title>
<style>
 body{{margin:0;background:#1b1b1f;color:#ddd;font-family:system-ui,sans-serif}}
 h1{{font-size:18px;padding:12px 16px;margin:0;background:#111}}
 h2{{font-size:16px;margin:24px 16px 8px;border-left:4px solid #5b8;padding-left:8px}}
 .grid{{display:flex;flex-wrap:wrap;gap:14px;padding:0 16px}}
 a.panel{{text-decoration:none;color:inherit;display:block}}
 .panel{{background:#26262b;border:1px solid #333;border-radius:6px;overflow:hidden;transition:border-color .15s,box-shadow .15s}}
 a.panel:hover{{border-color:#5b8;box-shadow:0 0 0 2px rgba(90,187,136,.4)}}
 .cap{{font-size:12px;padding:5px 8px;display:flex;justify-content:space-between;gap:8px;white-space:nowrap}}
 .cap b{{color:#7dd}} .cap .m{{color:#999}}
 .frame{{width:{CW}px;height:{CH}px;overflow:hidden;position:relative;background:#111}}
 .frame iframe{{width:{W}px;height:{H}px;border:0;transform:scale({S});transform-origin:top left}}
 .ov{{position:absolute;inset:0;z-index:2;cursor:pointer;display:flex;align-items:center;justify-content:center}}
 .ov span{{opacity:0;color:#fff;background:rgba(20,40,30,.72);padding:6px 12px;border-radius:20px;font-size:13px;transition:opacity .15s}}
 a.panel:hover .ov span{{opacity:1}}
 .empty{{width:{CW}px;height:{CH}px;display:flex;align-items:center;justify-content:center;color:#666;background:#222}}
</style></head><body>
<h1>{args.title}（iframeは{W}x{H}を{S}倍表示・クリックで実寸フルページへ）</h1>
"""
    parts = [head]
    for t in tasks:
        parts.append(f'<h2>{t}</h2><div class="grid">')
        for d in models:
            mdl = inv.get(d, d)
            rel = f"{args.out_dir}/{d}/{t}.{args.ext}"
            f = os.path.join(args.out_dir, d, f"{t}.{args.ext}")
            rec = mm.get((mdl, t))
            meta = f'{rec.get("gen_tps","?")}t/s · {rec.get("wall_s","?")}s' if rec else ""
            if os.path.exists(f) and os.path.getsize(f) > 200 and args.ext == "html":
                parts.append(
                    f'<a class="panel" href="{rel}">'
                    f'<div class="cap"><b>{mdl}</b><span class="m">{meta} ⤢</span></div>'
                    f'<div class="frame"><iframe src="{rel}" loading="lazy" sandbox="allow-scripts"></iframe>'
                    f'<span class="ov"><span>⤢ フル画面で開く</span></span></div></a>')
            elif os.path.exists(f) and os.path.getsize(f) > 200:
                parts.append(
                    f'<a class="panel" href="{rel}"><div class="cap"><b>{mdl}</b>'
                    f'<span class="m">{meta}</span></div>'
                    f'<div class="empty">クリックで開く ({args.ext})</div></a>')
            else:
                parts.append(
                    f'<div class="panel"><div class="cap"><b>{mdl}</b></div>'
                    f'<div class="empty">未生成</div></div>')
        parts.append('</div>')
    parts.append("</body></html>")
    open(args.output, "w").write("\n".join(parts))
    print(f"wrote {args.output} ({filled}/{total} filled)")


if __name__ == "__main__":
    main()
