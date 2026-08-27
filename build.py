#!/usr/bin/env python3
"""Generate the Crambe Repetita Museum as flat static pages.

Todd, 2026-08-26: *"every museum entry should have its own url, so you can literally type it in
by ascending number if you want."* Hash routing cannot do that, so every item and every tag is a
real directory with a real index.html:

    /CRVI000001/          one per item, typeable, ascending
    /tags/                the index of tags
    /tag/designer/the-designers-republic/

⚠️ Static per-item pages, not one app — GitHub Pages serves no rewrites, so a typed URL has to
resolve to a file that exists. This also means the item view needs no JavaScript at all: the
picture is the page.

The only JS in the build is the hover-grow on tag pages, which is a real interaction.
"""
import json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "crvi.json")

FACET_ORDER = ["designer", "artist", "label", "decade", "colour", "type",
               "photographer", "illustrator", "art director", "typographer"]

CSS = """
:root{--ink:#111;--paper:#fff;--rule:#e8e8e8;--mute:#8c8c8c;
 --sans:"Helvetica Neue",Helvetica,Arial,sans-serif;
 --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%}
body{background:var(--paper);color:var(--ink);font:13px/1.5 var(--sans);
 -webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}

/* ---- top row: one thin line, one type size ---- */
.bar{display:flex;align-items:center;gap:14px;height:38px;padding:0 18px;
 border-bottom:1px solid var(--rule);font-size:12px;white-space:nowrap;overflow:hidden}
.bar .id{font:700 12px/1 var(--mono);letter-spacing:.06em;color:#000}
.bar .work{font-size:12px;overflow:hidden;text-overflow:ellipsis}
.bar .sep{color:var(--mute);letter-spacing:.12em}
.bar .rest{color:var(--mute);font-size:12px;overflow:hidden;text-overflow:ellipsis}
.bar .nav{margin-left:auto;display:flex;gap:4px}
.bar .nav a,.bar .nav span{display:flex;align-items:center;justify-content:center;
 width:26px;height:22px;border:1px solid var(--rule);font-size:12px;color:var(--ink)}
.bar .nav a:hover{border-color:var(--ink)}
.bar .nav span{opacity:0;pointer-events:none}

/* ---- item ---- */
.item{height:100%;display:flex;flex-direction:column}
.stage{flex:1;display:flex;align-items:center;justify-content:center;padding:24px;min-height:0;
 position:relative}
/* ⚠️ DO NOT WRAP THE IMAGE IN AN ANCHOR. The anchor has no definite height, so the image's
   max-height:100% resolves against `auto` and it renders at natural size — which blew every
   picture past the viewport. The link to the original lives in the corner instead. */
.stage img{max-width:100%;max-height:100%;object-fit:contain;display:block}
.tags{flex:0 0 auto;display:flex;flex-wrap:wrap;gap:5px 13px;padding:11px 18px 15px;
 border-top:1px solid var(--rule);font-size:11.5px}
.tags a{color:var(--mute)}
.tags a:hover{color:var(--ink)}
.tags a.all{color:var(--ink);font-weight:600}

/* ---- tag index ---- */
.wrap{max-width:1180px;margin:0 auto;padding:34px 18px 90px}
.facet{border-top:1px solid var(--rule);padding:16px 0 20px;display:grid;
 grid-template-columns:150px 1fr;gap:22px}
.facet:first-child{border-top:none}
.facet h2{font:600 10px/1.4 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--ink)}
.facet h2 .ct{display:block;font-weight:400;color:var(--mute);letter-spacing:.06em;margin-top:3px}
.facet .list{column-width:200px;column-gap:26px}
.facet .list a{display:flex;justify-content:space-between;gap:10px;font-size:12.5px;
 padding:2px 0;break-inside:avoid}
.facet .list a:hover{text-decoration:underline}
.facet .list .n{color:var(--mute);font:10px/1.7 var(--mono);flex:0 0 auto}
.crumb{display:flex;align-items:center;gap:14px;height:38px;padding:0 18px;
 border-bottom:1px solid var(--rule);font-size:12px}
.crumb .t{font:600 12px/1 var(--mono);letter-spacing:.06em}
.crumb .c{color:var(--mute);font:11px var(--mono)}
.crumb a{margin-left:auto;color:var(--mute);font-size:11.5px}
.crumb a:hover{color:var(--ink)}

/* ---- tag page grid ---- */
.grid{padding:22px 18px 180px;display:grid;
 grid-template-columns:repeat(auto-fill,minmax(92px,1fr));gap:18px;align-items:start}
.cell{position:relative;cursor:pointer}
.cell .inner{transition:transform .22s cubic-bezier(.2,.7,.3,1);transform-origin:left top}
.cell img{width:100%;display:block;background:#f5f5f5}
.cell .cap{opacity:0;font-size:11px;color:var(--mute);margin-top:6px;line-height:1.45;width:270px;
 transition:opacity .2s ease .05s,transform .22s cubic-bezier(.2,.7,.3,1);
 pointer-events:none;position:relative;z-index:1}
.cell .cap .n{font:700 10px/1.6 var(--mono);letter-spacing:.06em;color:var(--ink);display:block}
.cell.big{z-index:30}
.cell.big .inner{transform:scale(3)}
.cell.big .cap{opacity:1}
"""

# Arrow keys walk the exhibition. The item pages are otherwise script-free, so this is the
# only thing they carry — and it degrades to nothing if it fails, because the arrow LINKS in
# the top row are real anchors either way.
ITEM_JS = """
(function(){
 var p=%s,n=%s;
 addEventListener('keydown',function(e){
  if(e.metaKey||e.ctrlKey||e.altKey||e.shiftKey) return;
  if(e.key==='ArrowLeft'&&p){e.preventDefault();location.href='../'+p+'/';}
  if(e.key==='ArrowRight'&&n){e.preventDefault();location.href='../'+n+'/';}
 });
})();
"""

JS = """
var SCALE=3;var t=null;
document.querySelectorAll('.cell').forEach(function(c){
  c.addEventListener('mouseenter',function(){
    clearTimeout(t);
    t=setTimeout(function(){
      // transform does not change layout, so push the caption below the grown image
      var im=c.querySelector('img'),cap=c.querySelector('.cap');
      cap.style.transform='translateY('+im.getBoundingClientRect().height*(SCALE-1)+'px)';
      c.classList.add('big');
    },1000);
  });
  c.addEventListener('mouseleave',function(){
    clearTimeout(t);c.classList.remove('big');c.querySelector('.cap').style.transform='';
  });
});
"""


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def slug(s):
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", str(s).lower()))


def page(title, body, depth):
    up = "../" * depth
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title>'
            f'<link rel="stylesheet" href="{up}style.css"></head><body>{body}</body></html>')


def work_line(it, up):
    """`CRVI000042  Artist - Title ||| the rest` — a DASH between artist and title, and the
    ||| divides the work from everything said about it."""
    bits = [f'<span class="id">{esc(it["id"])}</span>']
    work = " - ".join(filter(None, [esc(it.get("maker")), esc(it.get("title"))]))
    bits.append(f'<span class="work">{work}</span>')
    rest = " · ".join(filter(None, [it.get("subtitle"), it.get("year")]))
    if rest:
        bits.append('<span class="sep">|||</span>')
        bits.append(f'<span class="rest">{esc(rest)}</span>')
    return "".join(bits)


def main():
    d = json.load(open(DATA))
    # ⚠️ NOTHING UNVERIFIED GOES LIVE. Todd, 2026-08-26, after I published an unattributed
    # poster to his public site: the museum publishes only items whose identity is established
    # by at least one credible source. A held item KEEPS its CRVI number — numbers are
    # permanent — it simply has no page until it is settled.
    items = [i for i in d["items"] if i.get("published", True)]
    held = [i for i in d["items"] if not i.get("published", True)]
    by_tag = {}
    for i, it in enumerate(items):
        for t in it.get("tags", []):
            by_tag.setdefault((t["k"], t["v"]), []).append(i)

    for old in ("tag", "tags"):
        p = os.path.join(HERE, old)
        if os.path.isdir(p): shutil.rmtree(p)
    for n in os.listdir(HERE):
        if re.fullmatch(r"CRVI\d{6}", n): shutil.rmtree(os.path.join(HERE, n))

    open(os.path.join(HERE, "style.css"), "w").write(CSS)

    # ---- one page per item, at its own typeable URL ----
    for i, it in enumerate(items):
        prev = items[i-1]["id"] if i > 0 else None
        nxt = items[i+1]["id"] if i < len(items)-1 else None
        nav = ""
        nav += f'<a href="../{prev}/" title="Previous">&#8592;</a>' if prev else '<span>&#8592;</span>'
        nav += f'<a href="../{nxt}/" title="Next">&#8594;</a>' if nxt else '<span>&#8594;</span>'
        tags = "".join(f'<a href="../tag/{slug(t["k"])}/{slug(t["v"])}/">#{esc(t["v"])}</a>'
                       for t in it.get("tags", []))
        tags += '<a class="all" href="../tags/">#alltags</a>'
        keys = ITEM_JS % (json.dumps(prev) if prev else "null",
                          json.dumps(nxt) if nxt else "null")
        # The museum still HOLDS the original in originals/ — it is simply not advertised
        # on the page. Todd: "i don't want this 1500x1500 - 0.4 mb thing in there."
        stage = f'<img src="../{esc(it["image"])}" alt="{esc(it.get("title"))}">' 
        body = (f'<div class="item"><div class="bar">{work_line(it,"../")}'
                f'<div class="nav">{nav}</div></div>'
                f'<div class="stage">{stage}</div>'
                f'<div class="tags">{tags}</div></div><script>{keys}</script>')
        od = os.path.join(HERE, it["id"]); os.makedirs(od, exist_ok=True)
        open(os.path.join(od, "index.html"), "w").write(
            page(f'{it["id"]} — Crambe Repetita Museum', body, 1))

    # ---- the tag index ----
    facets = {}
    for (k, v), idxs in by_tag.items():
        facets.setdefault(k, []).append((v, len(idxs)))
    order = [f for f in FACET_ORDER if f in facets] + sorted(set(facets) - set(FACET_ORDER))
    secs = []
    for k in order:
        vals = sorted(facets[k], key=lambda x: (-x[1], x[0].lower()))
        links = "".join(
            f'<a href="../tag/{slug(k)}/{slug(v)}/"><span>{esc(v)}</span>'
            f'<span class="n">{n}</span></a>' for v, n in vals)
        secs.append(f'<section class="facet"><h2>{esc(k)}'
                    f'<span class="ct">{len(vals)}</span></h2>'
                    f'<div class="list">{links}</div></section>')
    body = ('<div class="crumb"><span class="t">ALL TAGS</span>'
            f'<span class="c">{len(by_tag)} across {len(order)} categories</span>'
            f'<a href="../{items[0]["id"]}/">&#8592; back to the museum</a></div>'
            f'<div class="wrap">{"".join(secs)}</div>')
    os.makedirs(os.path.join(HERE, "tags"), exist_ok=True)
    open(os.path.join(HERE, "tags", "index.html"), "w").write(
        page("All tags — Crambe Repetita Museum", body, 1))

    # ---- one page per tag ----
    for (k, v), idxs in by_tag.items():
        cells = []
        for i in idxs:
            it = items[i]
            rest = " · ".join(filter(None, [it.get("subtitle"), it.get("year")]))
            cells.append(
                f'<a class="cell" href="../../../{it["id"]}/">'
                f'<div class="inner"><img src="../../../{esc(it["image"])}" alt=""></div>'
                f'<div class="cap"><span class="n">{esc(it["id"])}</span>'
                f'{esc(it.get("maker"))} - {esc(it.get("title"))}<br>{esc(rest)}</div></a>')
        body = ('<div class="crumb">'
                f'<span class="t">{esc(k.upper())}: {esc(v.upper())}</span>'
                f'<span class="c">{len(idxs)} items</span>'
                '<a href="../../../tags/">&#8592; all tags</a></div>'
                f'<div class="grid">{"".join(cells)}</div><script>{JS}</script>')
        od = os.path.join(HERE, "tag", slug(k), slug(v)); os.makedirs(od, exist_ok=True)
        open(os.path.join(od, "index.html"), "w").write(
            page(f'{k}: {v} — Crambe Repetita Museum', body, 3))

    # ---- the front door lands on the first item ----
    open(os.path.join(HERE, "index.html"), "w").write(
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url={items[0]["id"]}/">'
        f'<link rel="canonical" href="{items[0]["id"]}/">'
        '<title>Crambe Repetita Museum</title></head>'
        f'<body><a href="{items[0]["id"]}/">Enter the museum</a></body></html>')

    print(f'{len(items)} item pages · {len(by_tag)} tag pages · {len(order)} facets')
    if held:
        print(f'  {len(held)} HELD BACK, unverified: ' + ", ".join(h["id"] for h in held))
    print(f'  first {items[0]["id"]} · last {items[-1]["id"]}')


if __name__ == "__main__":
    main()
