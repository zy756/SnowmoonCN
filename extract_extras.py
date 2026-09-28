"""找出第一次提取漏掉的块（章首地点日期 / 泽戈语卡片 / 聊天与设备屏幕），记录它们插在第几个正文段落之后。
输出 extras/chapter-XX.json：[{after: 段落序号(0=章标题之前…), kind, lines:[...]}]
正文段落的计数口径与 en/*.md 完全一致（p/h1/h2/h3/blockquote/li），并逐章核对段数。"""
import json, re, html
from html.parser import HTMLParser
from pathlib import Path

H = Path(__file__).parent
PARA = {"p", "h1", "h2", "h3", "blockquote", "li"}
VOID = {"br", "img", "hr", "input", "meta", "link", "path", "rect", "circle", "line", "polyline", "polygon", "ellipse", "use"}


class Walker(HTMLParser):
    """在 div.document-page 内按文档顺序切块：正文段落计数；其他含文字的顶层元素作为 extra"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, classes)
        self.in_page = False
        self.page_depth = None
        self.npara = 0
        self.para_open = None    # 当前正文段落的 tag
        self.extra = None        # 当前 extra：dict(kind, lines, depth, cur)
        self.extras = []
        self.skip = 0
        self.inner = None        # 特殊块内的普通段落 (tag, depth)

    def classes(self, attrs):
        return dict(attrs).get("class", "") or ""

    def handle_starttag(self, tag, attrs):
        cls = self.classes(attrs)
        if tag in VOID:
            if tag == "br" and self.extra: self._newline()
            return
        self.stack.append((tag, cls))
        d = len(self.stack)
        if tag == "div" and "document-page" in cls and not self.in_page:
            self.in_page, self.page_depth = True, d
            return
        if not self.in_page: return
        if tag in ("nav", "script", "style", "button") or "wc-exclude" in cls:
            self.skip += 1; return
        if self.extra is None and self.para_open is None:
            if tag in PARA:
                self.para_open = tag
            elif d == self.page_depth + 1 or (tag in ("center", "table", "svg") and d == self.page_depth + 1):
                kind = "dateline" if "dateline" in cls else "dz" if ("dz-" in cls) else "device"
                self.extra = {"kind": kind, "lines": [], "depth": d, "cur": ""}
        if self.extra and tag in PARA and self.inner is None:
            # 特殊块里的普通段落：第一次提取已当正文抓过（已翻译），这里只计数、不重复收
            if self.extra["cur"].strip(): self._newline()
            self.inner = (tag, d); return
        if self.extra:
            if tag in ("tr", "div", "text") and self.extra["cur"].strip(): self._newline()
            if tag in ("td", "th") and self.extra["cur"].strip(): self.extra["cur"] += " ｜ "
            if tag == "button": pass

    def _newline(self):
        t = re.sub(r"\s+", " ", self.extra["cur"]).strip(" ｜")
        if t: self.extra["lines"].append(t)
        self.extra["cur"] = ""

    def handle_endtag(self, tag):
        if tag in VOID: return
        # 弹栈到匹配的 tag
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                d = i + 1
                popped = self.stack[i:]
                del self.stack[i:]
                break
        else:
            return
        if any(t in ("nav", "script", "style", "button") or "wc-exclude" in c for t, c in popped) and self.skip:
            self.skip -= sum(1 for t, c in popped if t in ("nav", "script", "style", "button") or "wc-exclude" in c)
            self.skip = max(self.skip, 0)
        if self.inner and d <= self.inner[1]:
            self.inner = None
            self.npara += 1
        if self.para_open and tag == self.para_open and self.extra is None:
            self.para_open = None
            self.npara += 1
        if self.extra and d <= self.extra["depth"]:
            self._newline()
            if self.extra["lines"]:
                self.extras.append({"after": self.npara, "kind": self.extra["kind"], "lines": self.extra["lines"]})
            self.extra = None
        if self.in_page and d <= self.page_depth:
            self.in_page = False

    def handle_data(self, data):
        if self.skip or not self.in_page: return
        if self.extra is not None and self.inner is None:
            self.extra["cur"] += data


def en_para_count(i):
    return len([b for b in (H / "en" / f"chapter-{i:02d}.md").read_text().split("\n\n") if b.strip()])


if __name__ == "__main__":
    (H / "extras").mkdir(exist_ok=True)
    tot_words = 0; bad = []
    for i in range(1, 33):
        w = Walker(); w.feed((H / "src" / f"chapter-{i}.html").read_text(encoding="utf-8"))
        n_en = en_para_count(i)
        if w.npara != n_en: bad.append((i, w.npara, n_en))
        (H / "extras" / f"chapter-{i:02d}.json").write_text(json.dumps(w.extras, ensure_ascii=False, indent=1))
        words = sum(len(" ".join(e["lines"]).split()) for e in w.extras); tot_words += words
        kinds = {}
        for e in w.extras: kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        print(f"ch{i:02d} 正文段 {w.npara}/{n_en} extras {len(w.extras)} {kinds} 词 {words}")
    print("extras 总词数", tot_words, "段数不一致:", bad)
