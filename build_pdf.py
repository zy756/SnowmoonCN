"""zh/chapter-XX.md → book.html → Snowmoon-中文版.pdf（无头 Chrome 打印，自动生成书签）"""
import html, json, re, subprocess, sys, glob, os
from pathlib import Path

H = Path(__file__).parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", s)
    return s.replace("\n", "<br>")


def extra_html(e: dict) -> str:
    lines = e.get("lines_zh") or e["lines"]
    if e["kind"] == "dateline":
        return f'<div class="dateline">{inline(" ".join(lines))}</div>'
    if e["kind"] == "dz":
        return '<div class="dz">' + "<br>".join(inline(l) for l in lines) + "</div>"
    if any("｜" in l for l in lines):
        rows = []
        for l in lines:
            cells = [c.strip() for c in l.split("｜")]
            rows.append("<tr>" + "".join(f'<td class="{"msg" if len(c) > 10 else "s"}">{inline(c)}</td>' for c in cells) + "</tr>")
        return f'<div class="device"><table>{"".join(rows)}</table></div>'
    return '<div class="device">' + "".join(f"<div>{inline(l)}</div>" for l in lines) + "</div>"


def md_to_html(md: str, anchor: str, extras: list | None = None) -> tuple[str, str]:
    blocks = [b.strip() for b in md.strip().split("\n\n") if b.strip()]
    ins = {}
    for e in extras or []:
        ins.setdefault(e["before"], []).append(e)
    out, title = [], ""
    for k, b in enumerate(blocks):
        pre = [extra_html(e) for e in ins.get(k, [])]
        if not b.startswith("# "):
            out.extend(pre)
        if b.startswith("# "):
            title = b[2:].strip()
            out.append(f'<h1 id="{anchor}">{inline(title)}</h1>')
            out.extend(pre)
        elif b.startswith("## "):
            out.append(f"<h2>{inline(b[3:])}</h2>")
        elif b.startswith("### "):
            out.append(f"<h3>{inline(b[4:])}</h3>")
        elif b.startswith(">"):
            body = "\n".join(l.lstrip("> ").rstrip() for l in b.splitlines())
            out.append(f"<blockquote>{inline(body)}</blockquote>")
        else:
            out.append(f"<p>{inline(b)}</p>")
    for e in ins.get(len(blocks), []):
        out.append(extra_html(e))
    return title, "\n".join(out)


CSS = """
@page { size: A5; margin: 18mm 15mm 20mm 15mm;
  @bottom-center { content: counter(page); font: 9pt "Songti SC"; color: #666; } }
@page :first { @bottom-center { content: none; } }
html { font-family: "Songti SC", "STSong", serif; font-size: 10.5pt; line-height: 1.85; color: #111; }
p { margin: 0 0 0.5em; text-indent: 2em; text-align: justify; }
h1 { font-family: "Songti SC"; font-weight: 700; font-size: 17pt; text-align: center; margin: 2.2em 0 1.6em; break-before: page; }
h2, h3 { font-size: 12pt; margin: 1.4em 0 0.6em; }
blockquote { margin: 0.8em 1.5em; color: #333; font-family: "Kaiti SC", "STKaiti", serif; }
.cover { height: 170mm; display: flex; flex-direction: column; justify-content: center; text-align: center; }
.cover .t { font-size: 34pt; font-weight: 700; letter-spacing: 0.08em; }
.cover .s { font-size: 13pt; margin-top: 1.2em; color: #444; }
.cover .a { font-size: 12pt; margin-top: 3em; }
.cover .n { font-size: 9pt; margin-top: 4em; color: #777; line-height: 1.6; }
.front { break-before: page; }
.front p { text-indent: 0; font-size: 9.5pt; }
.toc { break-before: page; }
.toc h1 { break-before: auto; }
.toc ol { list-style: none; padding: 0; columns: 2; column-gap: 8mm; }
.toc li { margin: 0.25em 0; }
.toc a { color: #111; text-decoration: none; }
.dateline { text-align: center; font-size: 9pt; color: #555; letter-spacing: 0.05em; margin: -1.2em 0 1.6em; }
.dz { text-align: center; font-family: "Kaiti SC", "STKaiti", serif; font-style: italic; margin: 0.9em 0; color: #333; }
.device { border: 0.6pt solid #999; border-radius: 3pt; padding: 0.45em 0.7em; margin: 0.8em 0.3em; font-family: "PingFang SC", "Heiti SC", sans-serif; font-size: 8.8pt; line-height: 1.55; background: #f6f6f6; break-inside: avoid; }
.device table { border-collapse: collapse; width: 100%; }
.device td { padding: 0.15em 0.35em; vertical-align: top; }
.device td.s { white-space: nowrap; }
.gpl { break-before: page; font-family: Menlo, monospace; font-size: 6.5pt; line-height: 1.35; white-space: pre-wrap; }
"""


def build(out_pdf: Path):
    files = sorted(glob.glob(str(H / "zh" / "chapter-*.md")))
    if not files:
        sys.exit("zh/ 下没有译稿")
    chapters = []
    for f in files:
        n = int(re.search(r"chapter-(\d+)", f).group(1))
        xf = H / "extras_zh" / f"chapter-{n:02d}.json"
        extras = json.loads(xf.read_text(encoding="utf-8")) if xf.exists() else []
        title, body = md_to_html(Path(f).read_text(encoding="utf-8"), f"ch{n}", extras)
        chapters.append((n, title or f"第 {n} 章", body))
    gpl = html.escape((H / "src" / "gpl-3.0.txt").read_text(encoding="utf-8"))
    toc = "\n".join(f'<li><a href="#ch{n}">{html.escape(t)}</a></li>' for n, t, _ in chapters)
    doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>Snowmoon（中文版）</title><style>{CSS}</style></head><body>
<div class="cover"><div class="t">Snowmoon</div><div class="s">雪月 · 中文译本</div>
<div class="a">Vitalik Buterin　著</div>
<div class="n">原文：https://vitalik.eth.limo/snowmoon/ （2026-09-27 获取）<br>本译本依 GNU GPL v3 发布</div></div>
<div class="front"><p><strong>版权与许可</strong></p>
<p>原作《Snowmoon》© Vitalik Buterin，以 GNU 通用公共许可证第 3 版（GPL v3）发布。本中文译本是原作的衍生作品，同样以 GPL v3 发布：你可以自由复制、分发和修改本译本，但再分发时必须保持同一许可证、保留本声明，并提供可编辑的源文本。</p>
<p>原作者附加要求：若将作品改编为影视或动画，需一并开源改编流程（包括 AI 提示词、脚本等非通用材料）。</p>
<p>本译本由 AI 辅助翻译，译名经统一校订；如与英文原文有出入，以原文为准。许可证全文附于书末。</p></div>
<div class="toc"><h1>目录</h1><ol>{toc}</ol></div>
{''.join(body for _, _, body in chapters)}
<h1 id="gpl">附录：GNU 通用公共许可证 第 3 版（英文原文）</h1><div class="gpl">{gpl}</div>
</body></html>"""
    book = H / "book.html"
    book.write_text(doc, encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--generate-pdf-document-outline",
                    f"--print-to-pdf={out_pdf}", book.as_uri()], check=True, capture_output=True, timeout=600)
    print(f"{len(chapters)} 章 → {out_pdf}（{out_pdf.stat().st_size/1e6:.1f} MB）")


if __name__ == "__main__":
    build(H / (sys.argv[1] if len(sys.argv) > 1 else "Snowmoon-中文版.pdf"))
