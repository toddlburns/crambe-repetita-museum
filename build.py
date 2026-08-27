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

FACET_ORDER = ["designer", "artist", "label", "decade", "color", "type",
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
.facet{position:relative;border-top:1px solid var(--rule);padding:16px 0 20px;display:grid;
 grid-template-columns:150px 1fr;gap:22px}
.facet:first-child{border-top:none}
.facet h2{font:600 10px/1.4 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--ink)}
.facet h2 .ct{display:block;font-weight:400;color:var(--mute);letter-spacing:.06em;margin-top:3px}
.facet .list{column-width:200px;column-gap:26px}
.facet .list a{display:flex;justify-content:space-between;gap:10px;font-size:12.5px;
 padding:2px 0;break-inside:avoid}
.facet .list a:hover{text-decoration:underline}
.facet .list .n{color:var(--mute);font:10px/1.7 var(--mono);flex:0 0 auto}
.facet .col{min-width:0}
/* ⚠️ Todd, 2026-08-27, MOBILE ONLY: a tag with more than ten things shows immediately, the rest
   sit behind "see more". Desktop is untouched — .more stays hidden and every tag renders, so the
   wide layout is exactly what it was. Done with a checkbox rather than JS so it survives with
   scripting off, and the toggle is visually hidden rather than display:none so it stays
   focusable. */
.moretoggle{position:absolute;opacity:0;width:1px;height:1px;pointer-events:none}
.more{display:none}
@media (max-width:700px){
 .facet .list a.small{display:none}
 .moretoggle:checked ~ .col .list a.small{display:flex}
 .more{display:inline-block;margin-top:10px;font:11px/1.6 var(--mono);letter-spacing:.05em;
  color:var(--mute);border-bottom:1px solid var(--rule);cursor:pointer;
  -webkit-tap-highlight-color:transparent}
 .more .b{display:none}
 .moretoggle:checked ~ .col .more .a{display:none}
 .moretoggle:checked ~ .col .more .b{display:inline}

 /* ---- item top row: two readable lines, not one truncated one ----
    At 390px the single nowrap row cut the work to "Youngbl…" and the subtitle to
    "Illustration by …", so a phone could not tell you what it was looking at. The number and
    the arrows keep the first line; the work and the rest each take a full line below.
    The ||| separator is hidden here — the line break does that job, and left in it dangles. */
 .bar{height:auto;min-height:38px;flex-wrap:wrap;white-space:normal;padding:8px 14px;
  gap:0 10px;row-gap:3px;align-items:baseline}
 .bar .id{order:1}
 .bar .nav{order:2;margin-left:auto;align-self:center}
 .bar .work{order:3;flex:1 1 100%;overflow:visible;text-overflow:clip}
 .bar .sep{display:none}
 .bar .rest{order:4;flex:1 1 100%;overflow:visible;text-overflow:clip}

 /* ---- grid captions are desktop-only ----
    ⚠️ The caption is revealed by a mouseenter handler with a 1s delay, so touch never shows it
    at all — but at a fixed width:270px inside ~100px tracks it was the ENTIRE cause of tag
    pages scrolling sideways on a phone (536px of content in a 390px viewport, 214 offending
    elements). Hiding it on mobile costs nothing and removes the horizontal scroll. */
 .cell .cap{display:none}
 .grid{padding:16px 14px 120px;gap:14px}

 /* ---- tag index: heading above its list, both using the full width ----
    The 150px heading column was eating 40% of a 390px screen and squeezing names into
    two and three lines. */
 .wrap{padding:22px 14px 80px}
 .facet{grid-template-columns:1fr;gap:6px;padding:14px 0 16px}
 .facet h2 .ct{display:inline;margin:0 0 0 8px}
 .facet .list{column-width:auto;columns:1}

 /* ---- header rows break BETWEEN elements, never inside them ----
    "ALL TAGS" was splitting to "ALL / TAGS" and the back link to "back to the / museum". */
 .crumb{height:auto;min-height:38px;flex-wrap:wrap;padding:8px 14px;row-gap:2px}
 .crumb .t,.crumb .c,.crumb a{white-space:nowrap}
 .crumb a{margin-left:auto}
}
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
.cell img{width:100%;display:block;background:var(--paper)}
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
    # ⚠️ MOBILE ONLY. Tags with MORE THAN ten items show straight away; the rest wait behind a
    # "see more". The split is by item count per tag, not per facet, so eight of the fifteen
    # facets — artist, subject, photographer, client, art director, illustrator, typographer,
    # typography — currently have nothing above the line and open empty on a phone. The link
    # names the hidden count for exactly that reason: "see 122 more" reads as a choice, an
    # unexplained blank does not. Desktop renders every tag as before.
    MOBILE_SHOW_MIN = 10
    secs = []
    for k in order:
        vals = sorted(facets[k], key=lambda x: (-x[1], x[0].lower()))
        # vals is already ordered by descending count, so the big ones lead and this split
        # preserves the existing order rather than reshuffling it
        big = [t for t in vals if t[1] > MOBILE_SHOW_MIN]
        small = [t for t in vals if t[1] <= MOBILE_SHOW_MIN]

        def lnk(v, n, cls):
            return (f'<a class="{cls}" href="../tag/{slug(k)}/{slug(v)}/"><span>{esc(v)}</span>'
                    f'<span class="n">{n}</span></a>')
        links = ("".join(lnk(v, n, "big") for v, n in big)
                 + "".join(lnk(v, n, "small") for v, n in small))
        tid = "m-" + slug(k)
        more = (f'<label class="more" for="{tid}">'
                f'<span class="a">see {len(small)} more</span>'
                f'<span class="b">show fewer</span></label>') if small else ""
        secs.append(f'<section class="facet">'
                    f'<input type="checkbox" id="{tid}" class="moretoggle">'
                    f'<h2>{esc(k)}<span class="ct">{len(vals)}</span></h2>'
                    f'<div class="col"><div class="list">{links}</div>{more}</div>'
                    f'</section>')
    body = ('<div class="crumb"><span class="t">ALL TAGS</span>'
            f'<span class="c">{len(by_tag)} across {len(order)} categories</span>'
            f'<a href="../{items[0]["id"]}/">&#8592; back to the museum</a></div>'
            f'<div class="wrap">{"".join(secs)}</div>')
    os.makedirs(os.path.join(HERE, "tags"), exist_ok=True)
    open(os.path.join(HERE, "tags", "index.html"), "w").write(
        page("All tags — Crambe Repetita Museum", body, 1))

    # ---- one page per tag ----
    # ⚠️ Todd, 2026-08-26: a tag page with MORE THAN 30 images groups itself by color, "so that
    # the green go next to the green, the red next to the red". Below that threshold the page
    # stays in item order — a short page reads fine and shuffling it only hides the sequence.
    # Chromatic items run round the hue wheel (red -> orange -> yellow -> green -> blue -> pink);
    # achromatic ones have no hue at all and are kept together at the end, ordered dark to light,
    # rather than being scattered through the colors.
    COLOUR_SORT_MIN = 30

    def color_order(idxs):
        def key(i):
            it = items[i]
            h = it.get("hue")
            lt = it.get("light") if it.get("light") is not None else 0.5
            if h is None:
                return (1, 0.0, lt)
            return (0, h, lt)
        return sorted(idxs, key=key)

    for (k, v), idxs in by_tag.items():
        grouped = len(idxs) > COLOUR_SORT_MIN
        if grouped:
            idxs = color_order(idxs)
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
