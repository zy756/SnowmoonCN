"""生成 book.routex.one 静态站 → site/
index.html（封面 + 许可 + 目录 + 下载）、chapter-N.html、license.html、style.css、源文本 zip、PDF"""
import html, json, re, shutil, zipfile, datetime
from pathlib import Path

H = Path(__file__).parent
OUT = H / "site"
TODAY = datetime.date.today().isoformat()
COLORS = json.loads((H / "para_colors.json").read_text())


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", s)
    return s.replace("\n", "<br>")


def hue(c):  # oklch(0.7 0.15 346.6) → 346.6
    m = re.search(r"oklch\(\s*[\d.]+\s+[\d.]+\s+([\d.]+)", c or "")
    return float(m.group(1)) if m else None


def colorize(text_html: str, c) -> str:
    """把段落里「“…”」对话部分染成说话人的颜色（按原书该段主色）"""
    h = hue(c)
    if h is None:
        return text_html
    return re.sub(r"(“[^”]*”)", lambda m: f'<span class="say" style="--h:{h:.0f}">{m.group(1)}</span>', text_html)


def extra_html(e: dict) -> str:
    lines = e.get("lines_zh") or e["lines"]
    if e["kind"] == "dateline":
        return f'<div class="dateline">{inline(" ".join(lines))}</div>'
    if e["kind"] == "dz":
        return '<div class="dz">' + "<br>".join(inline(l) for l in lines) + "</div>"
    if any("｜" in l for l in lines):
        rows = "".join("<tr>" + "".join(f'<td class="{"msg" if len(c.strip()) > 10 else "s"}">{inline(c.strip())}</td>' for c in l.split("｜")) + "</tr>" for l in lines)
        return f'<div class="device"><table>{rows}</table></div>'
    return '<div class="device">' + "".join(f"<div>{inline(l)}</div>" for l in lines) + "</div>"


def chapter_html(n: int) -> tuple[str, str]:
    blocks = [b.strip() for b in (H / "zh" / f"chapter-{n:02d}.md").read_text(encoding="utf-8").strip().split("\n\n") if b.strip()]
    cols = COLORS[str(n)]
    assert len(cols) == len(blocks), (n, len(cols), len(blocks))
    xf = H / "extras_zh" / f"chapter-{n:02d}.json"
    ins = {}
    for e in (json.loads(xf.read_text(encoding="utf-8")) if xf.exists() else []):
        ins.setdefault(e["before"], []).append(e)
    out, title = [], f"第 {n} 章"
    for k, b in enumerate(blocks):
        pre = [extra_html(e) for e in ins.get(k, [])]
        if b.startswith("# "):
            title = b[2:].strip()
            out.append(f"<h1>{inline(title)}</h1>")
            out.extend(pre)
            continue
        out.extend(pre)
        if b.startswith("## "):
            out.append(f"<h2>{inline(b[3:])}</h2>")
        elif b.startswith("### "):
            out.append(f"<h3>{inline(b[4:])}</h3>")
        elif b.startswith(">"):
            out.append(f"<blockquote>{colorize(inline(chr(10).join(l.lstrip('> ') for l in b.splitlines())), cols[k])}</blockquote>")
        else:
            out.append(f"<p>{colorize(inline(b), cols[k])}</p>")
    for e in ins.get(len(blocks), []):
        out.append(extra_html(e))
    return title, "\n".join(out)


HEAD = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><meta name="description" content="Vitalik Buterin 科幻小说《Snowmoon》简体中文译本（GPL v3）">
<link rel="stylesheet" href="style.css">
<meta property="og:type" content="book"><meta property="og:site_name" content="Snowmoon 中文版"><meta property="og:title" content="{title}"><meta property="og:description" content="Vitalik Buterin 科幻小说《Snowmoon》简体中文译本：二次方投票、零知识证明、抽签选举与虚构城邦维里迪亚。">
<meta property="og:image" content="https://book.routex.one/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="https://book.routex.one/og.png">
<script>try{{var t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head><body>
<header class="bar"><a href="index.html" class="home">Snowmoon · 雪月</a><a href="https://t.me/SnowmoonCN" class="tg" target="_blank" rel="noopener">电报群</a>
<button class="theme" onclick="var d=document.documentElement,n=(d.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'))==='dark'?'light':'dark';d.dataset.theme=n;try{{localStorage.setItem('theme',n)}}catch(e){{}}" aria-label="切换深浅色">◐</button></header>
<main>"""
FOOT = """</main><footer>原作 © Vitalik Buterin · 中文译本以 <a href="license.html">GPL v3</a> 发布 · AI 辅助翻译，修改于 {today} · <a href="https://vitalik.eth.limo/snowmoon/">英文原文</a> · <a href="https://github.com/zy756/SnowmoonCN">源文本（GitHub）</a> · <a href="https://t.me/SnowmoonCN">电报读者群</a></footer></body></html>"""

CSS = """
:root { --bg:#fbfaf7; --fg:#1b1b1b; --mute:#6b6b6b; --line:#e3e0d8; --box:#f1efe9; --L:0.48; --C:0.14; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#16161a; --fg:#e6e4df; --mute:#9a988f; --line:#2c2c33; --box:#1f1f25; --L:0.78; --C:0.12; } }
:root[data-theme="dark"] { --bg:#16161a; --fg:#e6e4df; --mute:#9a988f; --line:#2c2c33; --box:#1f1f25; --L:0.78; --C:0.12; }
* { box-sizing: border-box; }
html { background: var(--bg); color: var(--fg); -webkit-text-size-adjust: 100%; }
body { margin: 0; font: 18px/1.9 "Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", "STSong", "SimSun", serif; }
a { color: inherit; }
.bar { position: sticky; top: 0; display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: var(--bg); border-bottom: 1px solid var(--line); font-size: 15px; z-index: 2; }
.bar .home { text-decoration: none; font-weight: 600; letter-spacing: .03em; }
.bar .theme { background: none; border: 1px solid var(--line); color: var(--fg); border-radius: 6px; padding: 2px 10px; font-size: 15px; cursor: pointer; }
main { max-width: 680px; margin: 0 auto; padding: 8px 16px 40px; }
h1 { text-align: center; font-size: 28px; margin: 40px 0 6px; }
h2, h3 { font-size: 20px; margin: 1.6em 0 .6em; }
p { margin: 0 0 .7em; text-indent: 2em; text-align: justify; }
blockquote { margin: 1em 1.2em; color: var(--mute); font-family: "Kaiti SC", "STKaiti", "KaiTi", serif; }
.say { color: oklch(var(--L) var(--C) var(--h)); }
.dateline { text-align: center; color: var(--mute); font-size: 14px; letter-spacing: .06em; margin: 0 0 32px; }
.dz { text-align: center; font-style: italic; color: var(--mute); margin: 1em 0; }
.device { border: 1px solid var(--line); background: var(--box); border-radius: 8px; padding: 8px 12px; margin: 1em 0; font: 15px/1.6 -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; overflow-x: auto; }
.device table { border-collapse: collapse; width: 100%; }
.device td { padding: 2px 6px; vertical-align: top; }
.device td.s { white-space: nowrap; }
.nav { display: flex; justify-content: space-between; gap: 12px; margin: 48px 0 8px; font-size: 16px; }
.nav a { text-decoration: none; border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; }
.cover { text-align: center; padding: 48px 0 16px; }
.cover .t { font-size: 44px; font-weight: 700; letter-spacing: .06em; }
.cover .s { color: var(--mute); margin-top: 4px; }
.cover .a { margin-top: 20px; }
.note { font-size: 15px; line-height: 1.75; color: var(--mute); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: 14px 0; margin: 24px 0; }
.note p { text-indent: 0; }
.toc { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; }
.toc a { display: block; text-decoration: none; border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; text-align: center; }
.bar .tg { margin-left: auto; margin-right: 10px; font-size: 14px; text-decoration: none; border: 1px solid var(--line); border-radius: 6px; padding: 2px 10px; }
.join { margin: 16px 0 28px; }
.join a { display: block; text-align: center; text-decoration: none; font-size: 17px; padding: 12px 16px; border-radius: 10px; background: #2a9fd6; color: #fff; }
.cta { text-indent: 0; text-align: center; color: var(--mute); font-size: 15px; margin-top: 40px; }
.dl { display: flex; gap: 10px; flex-wrap: wrap; margin: 12px 0 24px; }
.dl a { border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; text-decoration: none; font-size: 16px; }
footer { max-width: 680px; margin: 0 auto; padding: 24px 16px 40px; color: var(--mute); font-size: 13px; line-height: 1.7; border-top: 1px solid var(--line); }
pre.gpl { white-space: pre-wrap; font-size: 12px; line-height: 1.5; }
@media (max-width: 480px) { body { font-size: 17px; } h1 { font-size: 24px; } .cover .t { font-size: 36px; } }
"""


def page(title, body):
    return HEAD.format(title=html.escape(title)) + body + FOOT.format(today=TODAY)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    titles = {}
    for n in range(1, 33):
        t, body = chapter_html(n)
        titles[n] = t
        prev = f'<a href="chapter-{n-1}.html">← 第 {n-1} 章</a>' if n > 1 else '<a href="index.html">← 目录</a>'
        nxt = f'<a href="chapter-{n+1}.html">第 {n+1} 章 →</a>' if n < 32 else '<a href="index.html">回到目录</a>'
        cta = '<p class="cta">读到这里有想法？来 <a href="https://t.me/SnowmoonCN" target="_blank" rel="noopener">电报读者群</a> 聊聊，勘误也欢迎。</p>'
        (OUT / f"chapter-{n}.html").write_text(page(f"{t} · Snowmoon 中文版", body + cta + f'<nav class="nav">{prev}{nxt}</nav>'), encoding="utf-8")
    toc = "".join(f'<li><a href="chapter-{n}.html">{html.escape(titles[n])}</a></li>' for n in range(1, 33))
    idx = f"""<div class="cover"><div class="t">Snowmoon</div><div class="s">雪月 · 中文译本</div><div class="a">Vitalik Buterin 著</div></div>
<div class="note"><p>这是以太坊创始人 Vitalik Buterin 的长篇科幻小说《Snowmoon》的简体中文译本。故事设定在虚构城邦维里迪亚，涉及二次方投票、二次方资助、密码学抽签选举、零知识隐私认证等治理与技术设想。书名 Snowmoon 是书中的一个月份名（雪月）。</p>
<p><strong>许可：</strong>原作 © Vitalik Buterin，以 GNU GPL v3 发布；本译本是原作的修改版本（翻译），同样以 GPL v3 发布，修改日期 {TODAY}。你可以自由复制、分发、修改，再分发须保持同一许可并提供可编辑源文本。</p>
<p><strong>说明：</strong>本译本由 AI 辅助翻译，译名经统一校订，未经人工逐句审校；如与英文原文有出入，以<a href="https://vitalik.eth.limo/snowmoon/">原文</a>为准。原书中的图表以文字形式呈现；对话按角色着色，沿用原书配色。可编辑源文本见 <a href="https://github.com/zy756/SnowmoonCN">GitHub</a>。</p></div>
<div class="join"><a href="https://t.me/SnowmoonCN" target="_blank" rel="noopener">💬 加入电报读者群 · 讨论剧情、提交勘误</a></div>
<h2>目录</h2><ul class="toc">{toc}</ul>"""
    (OUT / "index.html").write_text(page("Snowmoon · 雪月 中文版", idx), encoding="utf-8")
    gpl = html.escape((H / "src" / "gpl-3.0.txt").read_text(encoding="utf-8"))
    (OUT / "license.html").write_text(page("GPL v3 · Snowmoon 中文版", f"<h1>GNU GPL v3</h1><pre class='gpl'>{gpl}</pre>"), encoding="utf-8")
    with zipfile.ZipFile(OUT / "snowmoon-zh-source.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted((H / "zh").glob("*.md")): z.write(f, f"zh/{f.name}")
        for f in sorted((H / "extras_zh").glob("*.json")): z.write(f, f"extras_zh/{f.name}")
        for name in ["glossary.md", "para_colors.json", "build_site.py", "build_pdf.py", "fix_tounicode.py"]:
            z.write(H / name, name)
        z.write(H / "src" / "gpl-3.0.txt", "LICENSE")
        z.writestr("README.md", f"# Snowmoon 中文译本 · 源文本\n\n原作：Vitalik Buterin，https://vitalik.eth.limo/snowmoon/ ，GPL v3。\n本译本为修改版本（翻译），修改日期 {TODAY}，同样以 GPL v3 发布。\n\n- zh/：各章中文 markdown（段落与英文原文一一对应）\n- extras_zh/：聊天记录、设备屏幕、章首日期等特殊块（before = 插在第几段之前）\n- build_site.py / build_pdf.py：生成网页版 / PDF\n")
    shutil.copy(H / "assets" / "og.png", OUT / "og.png")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"site/ 生成完毕：{len(list(OUT.glob('*.html')))} 个页面，{size/1e6:.1f} MB")


if __name__ == "__main__":
    build()
