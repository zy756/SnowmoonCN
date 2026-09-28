"""把 walker 的 extras 换算成 en/zh 段落坐标，并去掉正文里已有（已翻译）的行 → extras_final/chapter-XX.json"""
import re, json, difflib, importlib.util
from pathlib import Path
H = Path(__file__).parent
spec = importlib.util.spec_from_file_location('ex', H / 'extract_extras.py'); ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)

class W(ex.Walker):
    def __init__(s): super().__init__(); s.pt = []; s.cur_p = ''
    def handle_data(s, d):
        super().handle_data(d)
        if (s.para_open or s.inner) and not s.skip: s.cur_p += d
    def handle_endtag(s, t):
        before = s.npara; super().handle_endtag(t)
        if s.npara > before: s.pt.append(re.sub(r'\s+', ' ', s.cur_p).strip()); s.cur_p = ''

norm = lambda x: re.sub(r'[^0-9a-z]', '', x.lower())
(H / 'extras_final').mkdir(exist_ok=True)
tot = 0
for i in range(1, 33):
    w = W(); w.feed((H / 'src' / f'chapter-{i}.html').read_text(encoding='utf-8'))
    en = [re.sub(r'^(#+ |> )', '', b.strip()) for b in (H / 'en' / f'chapter-{i:02d}.md').read_text().split('\n\n') if b.strip()]
    sm = difflib.SequenceMatcher(a=[norm(x)[:40] for x in w.pt], b=[norm(x)[:40] for x in en], autojunk=False)
    m = {}
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(a2 - a1): m[a1 + k] = b1 + k
    en_norm = [norm(x) for x in en]
    out = []
    for e in w.extras:
        a = e['after']
        after = 0 if a == 0 else m.get(a - 1, None)
        if after is None:  # 找最近的已对齐段
            back = [m[k] for k in range(a - 1, -1, -1) if k in m]
            after = back[0] if back else -1
        after += 1   # 插在这一段之后 = 第 after 段之前（0 基）
        lines = []
        for ln in e['lines']:
            n = norm(ln.replace('｜', ' '))
            if len(n) > 12 and any(n[:60] in p or p[:60] in n for p in en_norm if len(p) > 12): continue  # 正文已有
            lines.append(ln)
        if lines: out.append({'before': after, 'kind': e['kind'], 'lines': lines})
    (H / 'extras_final' / f'chapter-{i:02d}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    words = sum(len(' '.join(e['lines']).split()) for e in out); tot += words
    print(f'ch{i:02d} 块 {len(out)} 词 {words}')
print('合计词数', tot)
