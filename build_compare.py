#!/usr/bin/env python3
"""out/ を走査して compare.html を生成。課題ごとに全モデルのiframeをグリッド表示。"""
import os, json

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")

MODELS = [
    "gemma4:e2b-nvfp4",
    "gemma4:12b-mxfp8", "gemma4:26b-mlx", "gemma4:26b-mxfp8",
    "gemma4:31b-mlx", "gemma4:31b", "gemma4:31b-mxfp8",
]
TASKS = [
    ("lv1_landing", "Lv1 ランディングページ"),
    ("lv2_spiro",   "Lv2 スピログラフ(媒介変数)"),
    ("lv3_cube",    "Lv3 立方体(3D陰面処理)"),
    ("lv4_gantt",   "Lv4 ガントチャート"),
    ("lv5_cloth",   "Lv5 布シミュ(Verlet)"),
]
def safe(m): return m.replace(":", "_").replace("/", "_")

SCALE = 0.5
W, H = 900, 600
CW, CH = int(W*SCALE), int(H*SCALE)

def metrics_map():
    p = os.path.join(OUT, "metrics.json")
    if not os.path.exists(p): return {}
    try: data = json.load(open(p))
    except Exception: return {}
    return {(r["model"], r["task"]): r for r in data}

def main():
    mm = metrics_map()
    # 完成セル数を数え、未完成なら自動リロードを入れる
    total = filled = 0
    for task, _ in TASKS:
        for m in MODELS:
            total += 1
            f = os.path.join(OUT, safe(m), f"{task}.html")
            if os.path.exists(f) and os.path.getsize(f) > 500:
                filled += 1
    refresh = '<meta http-equiv="refresh" content="25">' if filled < total else ''
    parts = ["""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
%s
<title>gemma4 コーディング比較</title>""" % refresh + """
<style>
 body{margin:0;background:#1b1b1f;color:#ddd;font-family:system-ui,sans-serif}
 h1{font-size:18px;padding:12px 16px;margin:0;background:#111}
 h2{font-size:16px;margin:24px 16px 8px;border-left:4px solid #5b8;padding-left:8px}
 .grid{display:flex;flex-wrap:wrap;gap:14px;padding:0 16px}
 a.panel{text-decoration:none;color:inherit;display:block}
 .panel{background:#26262b;border:1px solid #333;border-radius:6px;overflow:hidden;transition:border-color .15s,box-shadow .15s}
 a.panel:hover{border-color:#5b8;box-shadow:0 0 0 2px rgba(90,187,136,.4)}
 .cap{font-size:12px;padding:5px 8px;display:flex;justify-content:space-between;gap:8px;white-space:nowrap}
 .cap b{color:#7dd}
 .cap .m{color:#999}
 .frame{width:%dpx;height:%dpx;overflow:hidden;position:relative;background:#111}
 .frame iframe{width:%dpx;height:%dpx;border:0;transform:scale(%s);transform-origin:top left}
 .ov{position:absolute;inset:0;z-index:2;cursor:pointer;display:flex;align-items:center;justify-content:center}
 .ov span{opacity:0;color:#fff;background:rgba(20,40,30,.72);padding:6px 12px;border-radius:20px;font-size:13px;transition:opacity .15s}
 a.panel:hover .ov span{opacity:1}
 .empty{width:%dpx;height:%dpx;display:flex;align-items:center;justify-content:center;color:#666;font-size:13px;background:#222}
</style></head><body>
<h1>gemma4 各モデル × コーディング課題 比較（iframeは900×600を0.5倍表示）</h1>
""" % (CW, CH, W, H, SCALE, CW, CH)]

    for task, tlabel in TASKS:
        parts.append(f'<h2>{tlabel}</h2><div class="grid">')
        for m in MODELS:
            f = os.path.join(OUT, safe(m), f"{task}.html")
            rel = f"out/{safe(m)}/{task}.html"
            rec = mm.get((m, task))
            meta = ""
            if rec:
                meta = f'{rec.get("gen_tps","?")}t/s · {rec.get("wall_s","?")}s'
            if os.path.exists(f) and os.path.getsize(f) > 500:
                parts.append(
                    f'<a class="panel" href="{rel}">'
                    f'<div class="cap"><b>{m}</b><span class="m">{meta} ⤢</span></div>'
                    f'<div class="frame"><iframe src="{rel}" loading="lazy" sandbox="allow-scripts"></iframe>'
                    f'<span class="ov"><span>⤢ フル画面で開く</span></span></div></a>')
            else:
                parts.append(
                    f'<div class="panel"><div class="cap"><b>{m}</b><span class="m">{meta}</span></div>'
                    f'<div class="empty">未生成</div></div>')
        parts.append('</div>')
    parts.append("</body></html>")
    open(os.path.join(ROOT, "compare.html"), "w").write("\n".join(parts))
    print("wrote compare.html")

if __name__ == "__main__":
    main()
