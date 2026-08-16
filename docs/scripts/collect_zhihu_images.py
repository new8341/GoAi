"""Collect article screenshots into docs/images/zhihu/."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"e:\cursor\AI_kaiyuan")
OUT = ROOT / "docs" / "images" / "zhihu"
AGENT = ROOT / "tracks" / "algorithm" / "materials_agent"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def ensure_dir() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dest.write_bytes(r.read())
        print("downloaded", dest.name, dest.stat().st_size)
        return True
    except Exception as e:
        print("download_fail", dest.name, e)
        return False


def font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for ch in para:
            test = cur + ch
            if draw.textlength(test, font=fnt) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def card_verify() -> Path:
    path = AGENT / "outputs" / "production" / "production_verification.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    w, h = 1100, 620
    img = Image.new("RGB", (w, h), "#0f172a")
    d = ImageDraw.Draw(img)
    # accent bar
    d.rectangle((0, 0, 12, h), fill="#22c55e")
    title_f = font(36, True)
    body_f = font(22)
    mono_f = font(20)
    d.text((40, 36), "正式验收 · production_verification.json", fill="#e2e8f0", font=title_f)
    status = data.get("status", "?")
    color = "#22c55e" if status == "PASS" else "#ef4444"
    d.rounded_rectangle((40, 100, 220, 160), radius=12, fill=color)
    d.text((70, 112), status, fill="#052e16", font=title_f)
    d.text((250, 118), f"profile = {data.get('profile')}", fill="#94a3b8", font=body_f)

    y = 200
    for c in data.get("checks", []):
        ok = "✓" if c.get("pass") else "✗"
        oc = "#22c55e" if c.get("pass") else "#ef4444"
        line = f"{ok}  {c.get('name')}"
        d.text((40, y), line, fill=oc, font=body_f)
        detail = str(c.get("detail") or "")
        if detail:
            d.text((60, y + 32), detail, fill="#64748b", font=mono_f)
            y += 78
        else:
            y += 48

    dest = OUT / "03_production_verify_pass.png"
    img.save(dest)
    print("wrote", dest.name)
    return dest


def card_gap() -> Path:
    path = AGENT / "outputs" / "production" / "gaps.json"
    gaps = json.loads(path.read_text(encoding="utf-8"))
    # Prefer a gap with fulltext evidence and shorter quote
    gap = None
    for g in gaps:
        chain = g.get("evidence_chain") or []
        if chain and chain[0].get("location") == "fulltext":
            gap = g
            break
    gap = gap or gaps[0]
    ev = (gap.get("evidence_chain") or [{}])[0]
    quote = str(ev.get("quote_or_basis") or "")[:280].replace("\n", " ")
    prov = ev.get("provenance") or {}

    w, h = 1100, 720
    img = Image.new("RGB", (w, h), "#fffaf5")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 8), fill="#c2410c")
    title_f = font(32, True)
    body_f = font(20)
    small_f = font(17)
    d.text((36, 28), "研究缺口示例（带来源）", fill="#7c2d12", font=title_f)
    d.text((36, 80), f"类型：{gap.get('gap_type')}    id：{gap.get('id')}", fill="#9a3412", font=body_f)

    title_lines = wrap(d, str(gap.get("title") or ""), font(24, True), 1020)
    y = 130
    for line in title_lines[:3]:
        d.text((36, y), line, fill="#1c1917", font=font(24, True))
        y += 36

    d.text((36, y + 10), "证据摘录（fulltext）", fill="#57534e", font=body_f)
    y += 50
    q_lines = wrap(d, "「" + quote + "…」", small_f, 1020)
    for line in q_lines[:8]:
        d.text((36, y), line, fill="#44403c", font=small_f)
        y += 28

    y += 16
    meta = [
        f"paper_id: {ev.get('paper_id')}",
        f"parser: {prov.get('parser')}",
        f"pdf_hash: {str(prov.get('pdf_hash') or '')[:16]}…",
        f"source: {str(prov.get('source_url') or '')[:90]}",
    ]
    for m in meta:
        d.text((36, y), m, fill="#78716c", font=small_f)
        y += 28

    next_step = str(gap.get("next_step") or gap.get("description") or "")[:180]
    d.text((36, y + 12), "下一步 / 说明", fill="#57534e", font=body_f)
    y += 48
    for line in wrap(d, next_step, small_f, 1020)[:5]:
        d.text((36, y), line, fill="#292524", font=small_f)
        y += 28

    dest = OUT / "04_gap_with_evidence.png"
    img.save(dest)
    print("wrote", dest.name)
    return dest


def card_pipeline() -> Path:
    w, h = 1100, 520
    img = Image.new("RGB", (w, h), "#f8fafc")
    d = ImageDraw.Draw(img)
    title_f = font(30, True)
    body_f = font(18)
    d.text((36, 28), "材料文献 Agent · 主流程（示意）", fill="#0f172a", font=title_f)
    steps = [
        "输入主题",
        "检索文献",
        "下载 OA PDF",
        "解析全文",
        "找研究缺口",
        "写报告",
        "构效假说\n+ 数据库核验",
    ]
    box_w, box_h = 120, 88
    gap = 18
    x0 = 36
    y0 = 140
    for i, s in enumerate(steps):
        x = x0 + i * (box_w + gap)
        d.rounded_rectangle((x, y0, x + box_w, y0 + box_h), radius=14, fill="#e2e8f0", outline="#334155", width=2)
        lines = s.split("\n")
        ty = y0 + 22 if len(lines) == 1 else y0 + 16
        for line in lines:
            tw = d.textlength(line, font=body_f)
            d.text((x + (box_w - tw) / 2, ty), line, fill="#0f172a", font=body_f)
            ty += 26
        if i < len(steps) - 1:
            ax = x + box_w + 2
            d.polygon([(ax, y0 + 40), (ax + 12, y0 + 44), (ax, y0 + 48)], fill="#64748b")
    d.text((36, 280), "正式链路只认开放获取全文 + 可回源引用；本地演示通过 ≠ 正式验收通过。", fill="#475569", font=body_f)
    d.text((36, 330), "用户页：输入主题看结果　　调试页：查验收细节与证据出处", fill="#64748b", font=body_f)
    dest = OUT / "01_pipeline_overview.png"
    img.save(dest)
    print("wrote", dest.name)
    return dest


def chrome_shot(url: str, dest: Path, w: int = 1440, h: int = 1000) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Chrome writes relative to cwd; use absolute path
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={w},{h}",
        f"--screenshot={dest}",
        url,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=60, capture_output=True)
        ok = dest.exists() and dest.stat().st_size > 1000
        print("shot", dest.name, "ok" if ok else "empty", dest.stat().st_size if dest.exists() else 0)
        return ok
    except Exception as e:
        print("shot_fail", dest.name, e)
        return False


def wait_http(url: str, tries: int = 30) -> bool:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def card_user_summary() -> Path | None:
    """Render a results-summary card from the live public API (or local JSON)."""
    data = None
    for url in (
        "http://127.0.0.1:8765/api/runs/production/public",
        "http://127.0.0.1:8765/api/runs/production_sciverse/public",
    ):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))
                break
        except Exception:
            continue
    if data is None:
        # fallback: build minimal from files
        gaps = json.loads((AGENT / "outputs/production/gaps.json").read_text(encoding="utf-8"))
        papers = json.loads((AGENT / "outputs/production/papers.json").read_text(encoding="utf-8"))
        data = {
            "topic": "production run",
            "summary": {
                "papers": len(papers),
                "gaps": len(gaps),
                "fulltext_papers": sum(1 for p in papers if p.get("full_text") or p.get("fulltext_source")),
                "consistency_ok": True,
            },
            "gaps": gaps[:3],
        }

    summary = data.get("summary") or {}
    w, h = 1100, 640
    img = Image.new("RGB", (w, h), "#0b1220")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 8), fill="#38bdf8")
    d.text((36, 28), "用户端结果摘要（production）", fill="#e2e8f0", font=font(32, True))
    topic = str(data.get("topic") or "")[:80]
    d.text((36, 84), f"主题：{topic}", fill="#94a3b8", font=font(18))

    metrics = [
        ("文献", str(summary.get("papers", "?"))),
        ("研究空白", str(summary.get("gaps", "?"))),
        ("含全文", str(summary.get("fulltext_papers", "?"))),
        ("一致性", "通过" if summary.get("consistency_ok") else "待查"),
    ]
    x = 36
    for label, val in metrics:
        d.rounded_rectangle((x, 140, x + 230, 240), radius=16, fill="#1e293b")
        d.text((x + 24, 158), label, fill="#94a3b8", font=font(18))
        d.text((x + 24, 190), val, fill="#f8fafc", font=font(34, True))
        x += 250

    d.text((36, 280), "研究空白预览", fill="#cbd5e1", font=font(22, True))
    y = 320
    for g in (data.get("gaps") or [])[:3]:
        title = str(g.get("title") or g.get("id") or "")[:70]
        gtype = str(g.get("gap_type") or "")
        d.rounded_rectangle((36, y, w - 36, y + 78), radius=12, fill="#111827")
        d.text((56, y + 14), f"[{gtype}]", fill="#38bdf8", font=font(16))
        for line in wrap(d, title, font(18), 980)[:2]:
            d.text((56, y + 40), line, fill="#e2e8f0", font=font(18))
            break
        y += 92

    dest = OUT / "02b_user_result_summary.png"
    img.save(dest)
    print("wrote", dest.name)
    return dest


def write_results_html_snap() -> Path | None:
    """Static HTML mimicking user results, then Chrome-screenshot it via file URL."""
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:8765/api/runs/production/public", timeout=15
        ) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("public_api_fail", e)
        return None

    summary = data.get("summary") or {}
    gaps_html = ""
    for g in (data.get("gaps") or [])[:4]:
        ev = (g.get("evidence_chain") or [{}])[0]
        quote = str(ev.get("quote_or_basis") or "")[:220].replace("<", "&lt;")
        gaps_html += f"""
        <article class="card">
          <div class="tag">{g.get('gap_type')}</div>
          <h3>{str(g.get('title') or '').replace('<','&lt;')}</h3>
          <p class="quote">{quote}…</p>
          <p class="meta">paper: {ev.get('paper_id')} · loc: {ev.get('location')}</p>
        </article>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>Materials Agent 结果快照</title>
<style>
body{{margin:0;font-family:Segoe UI,Microsoft YaHei,sans-serif;background:#0b1220;color:#e2e8f0}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px}}
.brand{{color:#38bdf8;font-weight:700;letter-spacing:.04em}}
h1{{font-size:28px;margin:8px 0 6px}}
.sub{{color:#94a3b8}}
.metrics{{display:flex;gap:14px;margin:22px 0}}
.m{{flex:1;background:#1e293b;border-radius:14px;padding:16px}}
.m b{{display:block;font-size:28px;margin-top:6px}}
.card{{background:#111827;border-radius:14px;padding:16px 18px;margin:12px 0}}
.tag{{display:inline-block;background:#0ea5e9;color:#082f49;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700}}
.quote{{color:#cbd5e1;line-height:1.5}}
.meta{{color:#64748b;font-size:13px}}
</style></head><body><div class="wrap">
<div class="brand">Materials Agent · 用户结果快照</div>
<h1>{str(data.get('topic') or 'production').replace('<','&lt;')}</h1>
<p class="sub">从已有 outputs/production 打开 · 用于文章配图</p>
<div class="metrics">
  <div class="m">文献<b>{summary.get('papers','?')}</b></div>
  <div class="m">研究空白<b>{summary.get('gaps','?')}</b></div>
  <div class="m">含全文<b>{summary.get('fulltext_papers','?')}</b></div>
  <div class="m">一致性<b>{'通过' if summary.get('consistency_ok') else '待查'}</b></div>
</div>
{gaps_html}
</div></body></html>"""
    html_path = OUT / "_snap_user_results.html"
    html_path.write_text(html, encoding="utf-8")
    dest = OUT / "02c_user_results_page.png"
    chrome_shot(html_path.resolve().as_uri(), dest, 1200, 1100)
    return dest


def main() -> None:
    ensure_dir()
    card_pipeline()
    card_verify()
    card_gap()
    card_user_summary()

    # external photos / logos
    downloads = {
        "00_goai_launch_1.jpg": "https://nginx-hzwcm.hangzhou.com.cn/photolibrary/hzwcm/202607/22/046b91a2-5ab4-46de-80ef-967cacc3987a_m.jpg",
        "00_goai_launch_2.jpg": "https://nginx-hzwcm.hangzhou.com.cn/photolibrary/hzwcm/202607/22/1e525bfd-e631-4936-9fd5-52eb93d7f66c_m.jpg",
        "logo_datawhale.png": "https://avatars.githubusercontent.com/u/40556725?s=400&v=4",
        "logo_openalex.png": "https://opengraph.githubassets.com/1/ourresearch/openalex-guts",
        "logo_mineru.png": "https://opengraph.githubassets.com/1/opendatalab/MinerU",
        "logo_materials_project.png": "https://opengraph.githubassets.com/1/materialsproject/mapcore",
        "logo_docker.png": "https://www.docker.com/wp-content/uploads/2022/03/vertical-logo-monochromatic.png",
    }
    for name, url in downloads.items():
        download(url, OUT / name)

    if not wait_http("http://127.0.0.1:8765/"):
        print("WARN: viewer not up yet")
    else:
        chrome_shot("http://127.0.0.1:8765/", OUT / "02_user_ui.png", 1440, 1200)
        chrome_shot(
            "http://127.0.0.1:8765/debug/?run=production",
            OUT / "05_debug_ui_production.png",
            1440,
            1200,
        )
        write_results_html_snap()

    # cleanup helper html (keep pngs)
    helper = OUT / "_snap_user_results.html"
    if helper.exists():
        helper.unlink()

    print("done", OUT)
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name:40s} {p.stat().st_size:8d}")


if __name__ == "__main__":
    main()
