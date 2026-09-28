"""修 Chrome 生成 PDF 的 ToUnicode：康熙部首（U+2F00–2FD5）/ 部首补充（U+2E80–2EFF）→ 正常汉字，
否则阅读器里搜「一」搜不到、复制出来是 ⼀。只改文字映射，不动排版。"""
import re, sys, unicodedata
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, StreamObject

SUPP = {'⺀':'冫','⺁':'厂','⺇':'几','⺈':'刀','⺊':'卜','⺌':'小','⺍':'小','⺎':'兀','⺏':'尢','⺐':'尢','⺑':'尢','⺒':'巳','⺓':'幺','⺔':'彐','⺕':'彐','⺖':'心','⺗':'心','⺘':'手','⺙':'攴','⺛':'无','⺜':'日','⺝':'月','⺞':'歹','⺟':'母','⺠':'民','⺡':'水','⺢':'水','⺣':'火','⺤':'爪','⺥':'爪','⺦':'丬','⺧':'牛','⺨':'犬','⺩':'王','⺪':'疋','⺫':'目','⺬':'示','⺭':'示','⺮':'竹','⺯':'糸','⺰':'纟','⺱':'网','⺲':'网','⺳':'网','⺴':'网','⺵':'网','⺶':'羊','⺷':'羊','⺸':'羊','⺹':'老','⺺':'聿','⺻':'聿','⺼':'肉','⺽':'臼','⺾':'艸','⺿':'艸','⻀':'艸','⻁':'虎','⻂':'衣','⻃':'西','⻄':'西','⻅':'见','⻆':'角','⻇':'角','⻈':'讠','⻉':'贝','⻊':'足','⻋':'车','⻌':'辶','⻍':'辶','⻎':'辶','⻏':'阝','⻐':'钅','⻑':'長','⻒':'長','⻓':'长','⻔':'门','⻕':'阜','⻖':'阝','⻗':'雨','⻘':'青','⻙':'韦','⻚':'页','⻛':'风','⻜':'飞','⻝':'食','⻞':'食','⻟':'食','⻠':'饣','⻡':'首','⻢':'马','⻣':'骨','⻤':'鬼','⻥':'鱼','⻦':'鸟','⻧':'卤','⻨':'麦','⻩':'黄','⻪':'黾','⻫':'斉','⻬':'齐','⻭':'歯','⻮':'齿','⻯':'竜','⻰':'龙','⻱':'龜','⻲':'亀','⻳':'龟'}

def fix_char(u: str) -> str:
    o = ord(u)
    if 0x2F00 <= o <= 0x2FD5: return unicodedata.normalize('NFKC', u)
    return SUPP.get(u, u)

def fix_cmap(data: bytes) -> tuple[bytes, int]:
    s = data.decode('latin1'); n = 0
    def rep(m):
        nonlocal n
        hexs = m.group(1)
        if len(hexs) % 4: return m.group(0)
        chars = ''.join(chr(int(hexs[i:i+4], 16)) for i in range(0, len(hexs), 4))
        try: chars = chars.encode('utf-16-be', 'surrogatepass').decode('utf-16-be')
        except Exception: return m.group(0)
        new = ''.join(fix_char(c) for c in chars)
        if new == chars: return m.group(0)
        n += 1
        return '<' + new.encode('utf-16-be').hex().upper() + '>'
    # 只替换每行最后一个 <> 目标值（bfchar / 单目标 bfrange），不碰源码
    out = re.sub(r'(?m)(?<=\s)<([0-9A-Fa-f]{4,})>(?=\s*$)', rep, s)
    return out.encode('latin1'), n

def main(src, dst):
    r = PdfReader(src); w = PdfWriter(clone_from=r); total = 0; seen = set()
    for page in w.pages:
        fonts = (page.get('/Resources') or {}).get('/Font') or {}
        for fref in fonts.values():
            f = fref.get_object(); tu = f.get('/ToUnicode')
            if tu is None: continue
            obj = tu.get_object()
            if id(obj) in seen: continue
            seen.add(id(obj))
            data, n = fix_cmap(obj.get_data())
            if n: obj.set_data(data); total += n
    w.write(dst)
    print(f'修正映射 {total} 处 → {dst}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
