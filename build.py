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

# `medium` was folded into `type` on 2026-08-28 — of 29 medium tags, 28 restated the type
# beside them. One facet, not two that mostly agree.
FACET_ORDER = ["designer", "artist", "label", "decade", "color", "type",
               "photographer", "illustrator", "art director", "typographer"]

ORDER_JS = r"""(function(){
var c=document.getElementById("bycolor"), r=document.getElementById("byrecent");
var cs=[].slice.call(document.querySelectorAll("#allgrid .cell"));
var KEY="crviAllOrder";
function apply(){
  var mode = c.checked ? "color" : (r.checked ? "recent" : "");
  cs.forEach(function(el){
    el.style.order = mode==="color" ? el.dataset.c : (mode==="recent" ? el.dataset.r : "");
  });
  try{ localStorage.setItem(KEY, mode); }catch(e){}
}
c.addEventListener("change",function(){ if(c.checked) r.checked=false; apply(); });
r.addEventListener("change",function(){ if(r.checked) c.checked=false; apply(); });
try{
  var m=localStorage.getItem(KEY);
  if(m==="color") c.checked=true;
  else if(m==="recent") r.checked=true;
  else if(localStorage.getItem("crviAllByColor")) c.checked=true;
}catch(e){}
apply();
})();"""

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
.bar{position:relative;display:flex;align-items:center;gap:14px;height:38px;padding:0 18px;
 border-bottom:1px solid var(--rule);font-size:12px;white-space:nowrap;overflow:hidden}
.bar .id{font:700 12px/1 var(--mono);letter-spacing:.06em;color:#000}
.bar .work{font-size:12px;overflow:hidden;text-overflow:ellipsis}
.bar .sep{color:var(--mute);letter-spacing:.12em}
.bar .rest{color:var(--mute);font-size:12px;overflow:hidden;text-overflow:ellipsis}
.bar .srcline{color:var(--mute);font-size:12px;white-space:nowrap;text-decoration:underline}
.bar a.srcline:hover{color:var(--ink)}
.bar .srcline.nourl{text-decoration:none;border-bottom:1px dotted var(--rule);cursor:help}
.bar .nav{margin-left:auto;display:flex;gap:4px}
.bar .nav a,.bar .nav span{display:flex;align-items:center;justify-content:center;
 width:26px;height:22px;border:1px solid var(--rule);font-size:12px;color:var(--ink)}
.bar .nav a:hover{border-color:var(--ink)}
.bar .nav span{opacity:0;pointer-events:none}
.infotoggle{position:absolute;opacity:0;width:1px;height:1px;pointer-events:none}
.infobtn{display:none}

/* ---- item ---- */
.item{height:100%;display:flex;flex-direction:column}
.stage{flex:1;display:flex;align-items:center;justify-content:center;padding:24px;min-height:0;
 position:relative}
/* ⚠️ DO NOT WRAP THE IMAGE IN AN ANCHOR. The anchor has no definite height, so the image's
   max-height:100% resolves against `auto` and it renders at natural size — which blew every
   picture past the viewport. The link to the original lives in the corner instead. */
.stage img,.stage video{max-width:100%;max-height:100%;object-fit:contain;display:block}
.tags{flex:0 0 auto;display:flex;flex-wrap:wrap;gap:5px 13px;padding:11px 18px 15px;
 border-top:1px solid var(--rule);font-size:11.5px}
.tags a{color:var(--mute)}
.tags a:hover{color:var(--ink)}
/* the rights link sits hard right on the bottom row — margin-left:auto on the last flex item
   pushes it to the end of its line, and .tags wraps, so on a narrow screen it right-aligns on
   whatever line it lands on rather than jamming against the last tag */
.tags .src.rights{margin-left:14px;color:#a8a8a8;font-size:11px;text-decoration:underline}
.tags .src.rights:hover{color:var(--ink)}
.tags .src.allbtn{margin-left:auto;color:#a8a8a8;font-size:11px;text-decoration:underline}
.tags .src.allbtn:hover{color:var(--ink)}
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
.crumb{display:flex;align-items:center;gap:14px;height:38px;padding:0 18px;
 border-bottom:1px solid var(--rule);font-size:12px}
.crumb .t{font:600 12px/1 var(--mono);letter-spacing:.06em}
.crumb .c{color:var(--mute);font:11px var(--mono)}
.crumb a{margin-left:auto;color:var(--mute);font-size:11.5px}
.crumb a:hover{color:var(--ink)}
.crumb .ord{margin-left:16px;color:var(--mute);font:11px var(--mono);cursor:pointer;
 display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.crumb .ord input{accent-color:#111;cursor:pointer}

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
 /* Todd, 2026-08-27: the work and the rest fold into a box called "info", so the bar is one
    row and the picture gets the two lines back. Tap targets are 46x40 rather than 26x22 —
    "a bit bigger for my fat thumbs". Checkbox again, so it needs no script. */
 .bar{align-items:center;padding:6px 12px}
 .bar .work,.bar .rest,.bar .sep,.bar .srcline{display:none}
 .infotoggle:checked ~ .work{display:block;order:4;flex:1 1 100%;font-weight:600;
  overflow:visible;text-overflow:clip;padding-top:2px}
 .infotoggle:checked ~ .rest{display:block;order:5;flex:1 1 100%;
  overflow:visible;text-overflow:clip}
 /* Todd, 2026-08-28: on mobile the source belongs inside the info box, not on the bar */
 .infotoggle:checked ~ .srcline{display:block;order:6;flex:1 1 100%;padding-bottom:2px}
 .infobtn{display:flex;align-items:center;justify-content:center;order:2;margin-left:auto;
  min-width:46px;height:40px;border:1px solid var(--rule);cursor:pointer;
  font:11px/1 var(--mono);letter-spacing:.08em;color:var(--ink);
  -webkit-tap-highlight-color:transparent}
 .infobtn .b{display:none}
 .infotoggle:checked ~ .infobtn .a{display:none}
 .infotoggle:checked ~ .infobtn .b{display:inline}
 .bar .nav{order:3;margin-left:8px;gap:6px}
 .bar .nav a,.bar .nav span{min-width:46px;height:40px;font-size:15px}

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
 /* ⚠️ These only work because the base .crumb rules now sit ABOVE this media query. They
    used to sit below it, so `height:38px` beat `height:auto` on equal specificity and the bar
    stayed locked at one row's height — invisible until a second toggle made it wrap, at which
    point the content overflowed and the bottom border cut straight through row two. */
 .crumb{height:auto;min-height:38px;flex-wrap:wrap;padding:8px 14px;row-gap:9px}
 .crumb .t,.crumb .c,.crumb a{white-space:nowrap}
 /* the two order toggles ride together; only the back link is pushed away */
 .crumb .ord{margin-left:0}
 .crumb a{margin-left:auto}
}
.rights{max-width:660px}
.rights h2{font:600 10px/1.4 var(--mono);letter-spacing:.16em;text-transform:uppercase;
 margin:30px 0 8px;color:var(--ink)}
.rights h2:first-child{margin-top:0}
.rights p{font-size:13.5px;line-height:1.62;color:#333;margin-bottom:10px}
.rights a{text-decoration:underline}
.rights .contact{font:12px var(--mono)}

/* ---- tag page grid ---- */
.grid{padding:22px 18px 180px;display:grid;
 grid-template-columns:repeat(auto-fill,minmax(92px,1fr));gap:18px;align-items:start}
.grid.small{grid-template-columns:repeat(auto-fill,minmax(64px,1fr));gap:10px;padding:18px 18px 160px}
@media (max-width:700px){.grid.small{grid-template-columns:repeat(auto-fill,minmax(58px,1fr));gap:8px;padding:14px 14px 100px}}
.cell{position:relative;cursor:pointer}
.cell .inner{position:relative;transition:transform .22s cubic-bezier(.2,.7,.3,1);
 transform-origin:left top}
/* the hover video sits exactly over the still it replaces, inside .inner so it scales with
   the tile rather than staying put while the tile grows around it */
.cell video{position:absolute;inset:0;width:100%;height:100%;display:block;object-fit:cover}
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
// ⚠️ THE GIF IS FETCHED ON HOVER, NOT BEFORE. Setting src is what triggers the download, so a
// grid cell ships the still poster and only swaps in the animation when the pointer arrives.
// Pausing or hiding a GIF whose src is already set saves nothing — it is on the wire either way.
// The poster is kept in data-poster so leaving restores it without a second fetch of anything.
function playGif(c){
  var im=c.querySelector('img.anim');
  if(!im) return;
  var g=im.getAttribute('data-gif');
  if(!g||im.dataset.playing) return;
  im.dataset.poster=im.getAttribute('src');
  im.dataset.playing='1';
  im.setAttribute('src',g);
}
function stopGif(c){
  var im=c.querySelector('img.anim');
  if(!im||!im.dataset.playing) return;
  // back to the still, so a page full of gifs is not left all animating at once
  im.setAttribute('src',im.dataset.poster);
  delete im.dataset.playing;
}
// ⚠️ A VIDEO CANNOT BE SWAPPED INTO AN <img>. Where a gif item just changes src, a video item
// lays a <video> over its still on hover and takes it away again on leave — same bargain as the
// gif: nothing is on the wire until the pointer arrives, and a grid is never left all playing.
function playVid(c){
  var im=c.querySelector('img.anim'); if(!im) return;
  var u=im.getAttribute('data-video'); if(!u||c.querySelector('video')) return;
  var v=document.createElement('video');
  v.src=u; v.autoplay=true; v.loop=true; v.muted=true; v.playsInline=true;
  im.parentNode.appendChild(v);
}
function stopVid(c){ var v=c.querySelector('video'); if(v) v.parentNode.removeChild(v); }
document.querySelectorAll('.cell').forEach(function(c){
  c.addEventListener('mouseenter',function(){
    playGif(c); playVid(c);
    clearTimeout(t);
    t=setTimeout(function(){
      // transform does not change layout, so push the caption below the grown image
      var im=c.querySelector('img'),cap=c.querySelector('.cap');
      cap.style.transform='translateY('+im.getBoundingClientRect().height*(SCALE-1)+'px)';
      c.classList.add('big');
    },1000);
  });
  c.addEventListener('mouseleave',function(){
    stopGif(c); stopVid(c);
    clearTimeout(t);c.classList.remove('big');c.querySelector('.cap').style.transform='';
  });
});
"""


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def slug(s):
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", str(s).lower()))


# ── the gate ────────────────────────────────────────────────────────────────────────────────
# Todd, 2026-08-30: the museum comes off the front of the personal site and moves behind a
# password, reachable from the links page.
#
# ⚠️ THIS IS OBSCURITY, NOT PRIVACY, AND IT CANNOT BE MADE INTO PRIVACY HERE. The repository is
# public and GitHub Pages serves every file at a guessable URL, so the password below is readable
# in view-source and `images/CRVI000001.jpg` is fetchable without ever meeting the gate. It stops
# a casual visitor and it stops the site being browsable from the homepage; it stops nothing else.
# Real access control needs a host that can refuse the request — the Cloudflare Pages + Access
# move is the planned answer. Until then, do not put anything here that must not be seen.
#
# The `noindex` meta and robots.txt do more real work than the gate: they keep the archive out of
# search results, which is how a stranger would actually arrive.
#
# ⚠️ THE GATE IS AN OVERLAY. IT MUST NOT WRAP OR HIDE THE PAGE. The first attempt put the body in
# a `display:none` div and revealed it after login — which silently broke /all/ and every tag
# page: 692 cells laid out and not one thumbnail loaded, because Chrome will not start a
# `loading="lazy"` image that was parsed inside a hidden subtree. An opaque fixed overlay leaves
# layout, the html>body>.item height chain, and lazy loading completely untouched, and covers just
# as much as display:none did. Do not "simplify" this back into a wrapper.
GATE_PW = "racine456"

# Runs in <head>, before the body is parsed, so an already-authorised visitor never sees the gate
# paint at all and a stranger never sees the museum behind it.
GATE_HEAD_JS = ("try{if(localStorage.getItem('crvi_auth')==='1')"
                "document.documentElement.className+=' crvi-ok';}catch(e){}")

GATE_STYLE = """
html:not(.crvi-ok){overflow:hidden}
html.crvi-ok #crvi-gate{display:none}
#crvi-gate{position:fixed;inset:0;z-index:2147483647;background:var(--paper);
 display:flex;align-items:center;justify-content:center}
#crvi-gate form{display:flex;align-items:center;gap:6px}
#crvi-gate input{font:12px/1 var(--mono);letter-spacing:.06em;width:150px;padding:7px 8px;
 color:var(--ink);background:var(--paper);border:1px solid var(--rule);border-radius:0;outline:none}
#crvi-gate input:focus{border-color:var(--ink)}
#crvi-gate input::placeholder{color:var(--mute);letter-spacing:.06em}
#crvi-gate button{font:12px/1 var(--sans);padding:7px 12px;color:var(--ink);background:var(--paper);
 border:1px solid var(--rule);border-radius:0;cursor:pointer}
#crvi-gate button:hover{border-color:var(--ink)}
#crvi-gate.bad input,#crvi-gate.bad input::placeholder{border-color:var(--ink);color:var(--ink)}
"""

GATE_BODY = ('<div id="crvi-gate"><form id="crvi-form" autocomplete="off">'
             '<input type="password" id="crvi-pw" placeholder="password" '
             'autocomplete="off" spellcheck="false" autofocus>'
             '<button type="submit">enter</button></form></div>')

# localStorage, not sessionStorage: the archive is 700 pages and items open in new tabs.
# sessionStorage (what the links page uses) would re-prompt on every one of them.
GATE_JS = """
(function(){var K='crvi_auth',PW='%s',h=document.documentElement;
if(h.className.indexOf('crvi-ok')>-1)return;
var g=document.getElementById('crvi-gate'),i=document.getElementById('crvi-pw');
document.getElementById('crvi-form').addEventListener('submit',function(e){e.preventDefault();
if(i.value===PW){try{localStorage.setItem(K,'1');}catch(e){}h.className+=' crvi-ok';}
else{i.value='';g.classList.add('bad');i.focus();}});
i.focus();})();
""" % GATE_PW


def page(title, body, depth):
    up = "../" * depth
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="robots" content="noindex,nofollow">'
            f'<title>{esc(title)}</title>'
            f'<script>{GATE_HEAD_JS}</script>'
            f'<link rel="stylesheet" href="{up}style.css">'
            f'<style>{GATE_STYLE}</style></head>'
            f'<body>{GATE_BODY}{body}'
            f'<script>{GATE_JS}</script></body></html>')


def work_line(it, up):
    """`CRVI000042  Artist - Title ||| the rest` — a DASH between artist and title, and the
    ||| divides the work from everything said about it."""
    # The toggle leads so the CSS sibling selectors below it can reach the work and the rest.
    # It does nothing on desktop, where everything stays on the one line it always was.
    bits = ['<input type="checkbox" id="info" class="infotoggle">',
            f'<span class="id">{esc(it["id"])}</span>']
    work = " - ".join(filter(None, [esc(it.get("maker")), esc(it.get("title"))]))
    bits.append(f'<span class="work">{work}</span>')
    rest = " · ".join(filter(None, [it.get("subtitle"), it.get("year")]))
    if rest:
        bits.append('<span class="sep">|||</span>')
        bits.append(f'<span class="rest">{esc(rest)}</span>')
    # ⚠️ THE LINK SAYS ONLY "(Source)". Todd, 2026-08-28: "don't say what it is." So the host is
    # not printed — the destination is a surprise by design. Where there is no URL to link (75
    # items name their source in words instead), the same "(Source)" is rendered as plain text
    # with the named source in the title attribute, so hovering still tells you. It is never a
    # link to nowhere.
    src_url, src_lab = it.get("source_url") or "", it.get("source_label") or ""
    if src_url or src_lab:
        bits.append('<span class="sep srcsep">|||</span>')
        if src_url:
            bits.append(f'<a class="srcline" href="{esc(src_url)}" target="_blank" '
                        f'rel="noopener noreferrer">(Source)</a>')
        else:
            bits.append(f'<span class="srcline nourl" title="{esc(src_lab)}">(Source)</span>')
    # ⚠️ THE VECTOR LINK IS ALSO WHAT KEEPS THE FILE ON THE CDN. The Pages build prunes every
    # original no page points at, so this href is load-bearing, not decoration — see
    # `.github/prune_unserved_originals.py`. Only the traced-drawing items carry one.
    if it.get("vector"):
        bits.append('<span class="sep srcsep">|||</span>')
        bits.append(f'<a class="srcline" href="{up}{esc(it["vector"])}" '
                    f'title="Vector original (SVG)" download>(Vector)</a>')
    bits.append('<label class="infobtn" for="info">'
                '<span class="a">info</span><span class="b">close</span></label>')
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
        # source sits with the tags, at the end, quiet but always present
        # source moved to the top row (see work_line). The bottom right holds the two
        # whole-archive links: `all` takes the auto margin so both sit hard right together.
        tags += '<a class="src allbtn" href="../all/">all</a>'
        tags += '<a class="src rights" href="../rights/">rights &amp; use</a>'
        keys = ITEM_JS % (json.dumps(prev) if prev else "null",
                          json.dumps(nxt) if nxt else "null")
        # The museum still HOLDS the original in originals/ — it is simply not advertised
        # on the page. Todd: "i don't want this 1500x1500 - 0.4 mb thing in there."
        # A held video plays on the item page the way a GIF does — no controls, no chrome, just
        # the loop. muted+playsinline is what lets it autoplay at all on iOS and in Chrome.
        if it.get("video"):
            stage = (f'<video src="../{esc(it["image"])}" autoplay loop muted playsinline '
                     f'poster="../{esc(it["thumb"])}"></video>')
        else:
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
    # Todd, 2026-08-27: no stats line, and a short enough back link that the whole row fits on
    # one line on a phone. The per-facet counts sit next to each heading anyway, so a global
    # "429 across 15 categories" was saying nothing the page below does not already say.
    body = ('<div class="crumb"><span class="t">ALL TAGS</span>'
            f'<a href="../{items[0]["id"]}/">&#8592; museum</a></div>'
            f'<div class="wrap">{"".join(secs)}</div>')
    os.makedirs(os.path.join(HERE, "tags"), exist_ok=True)
    open(os.path.join(HERE, "tags", "index.html"), "w").write(
        page("All tags — Crambe Repetita Museum", body, 1))

    # ---- rights & use ----
    # ⚠️ A STATEMENT OF PRACTICE, NOT A LEGAL SHIELD, and it does not pretend to be one. It says
    # plainly what the archive is, that nothing in it is Todd's work, where each image came from,
    # and how to get something taken down — that last part is what actually resolves complaints.
    # Todd asked for something "very legalistic"; asserting a legal defence we cannot back would
    # be worse than useless, so this states facts and offers a fast, unconditional removal.
    rights = """<div class="crumb"><span class="t">RIGHTS &amp; USE</span>
<a href="../__F__/">&#8592; museum</a></div>
<div class="wrap rights">
<h2>What this is</h2>
<p>Crambe Repetita Visual Inspiration is a personal, non-commercial reference archive. It
collects graphic design and images its owner finds visually interesting &mdash; record sleeves,
posters, book jackets, photographs &mdash; so they can be looked at, compared and searched in one
place. Nothing is sold here. There is no advertising, no affiliate linking and no paid access.</p>
<h2>Nothing here is my work</h2>
<p>Every image in this archive was made by someone else. The archive makes <strong>no claim of
authorship and no claim of ownership</strong> over any image it displays. Copyright and all other
rights in each work remain with the artist, designer, photographer, publisher, estate or other
rights holder. Where a creator is known, the archive names them; where the creator is not
established, it says so rather than guessing.</p>
<h2>Every item names its source</h2>
<p>Each item records where its image came from. Where a public page for the object exists &mdash;
a museum record, a Discogs release, a gallery or seller listing, a published article &mdash; the
item links straight to it. Where no such page is available, the source is named in words. Where
the origin genuinely could not be established, the item says that too. <strong>Source links are
never invented to fill a gap.</strong></p>
<h2>Images are held at reference size</h2>
<p>Images are kept at the resolution needed to see a design clearly and no more. Many are small.
They are here as a record of what a thing looks like, with attribution and context &mdash; not as
a substitute for the original object, a print, or a licensed reproduction.</p>
<h2>If you hold rights in something here</h2>
<p>If you are a rights holder and would like an image removed, corrected or better credited,
please say so and it will be dealt with promptly and without argument. <strong>Removal requests
are honoured on request; no justification is required.</strong></p>
<p class="contact">Contact: <a href="mailto:todd.burns@gmail.com">todd.burns@gmail.com</a></p>
<h2>Corrections</h2>
<p>Attribution errors are taken seriously. If something is credited to the wrong person, or a work
is misidentified, please get in touch: it will be fixed and the correction noted on the item.</p>
</div>""".replace("__F__", items[0]["id"])
    os.makedirs(os.path.join(HERE, "rights"), exist_ok=True)
    open(os.path.join(HERE, "rights", "index.html"), "w").write(
        page("Rights & use — Crambe Repetita Museum", rights, 1))

    # ---- one page per tag ----
    # ⚠️ Todd, 2026-08-26: a tag page with MORE THAN 30 images groups itself by color, "so that
    # the green go next to the green, the red next to the red". Below that threshold the page
    # stays in item order — a short page reads fine and shuffling it only hides the sequence.
    # Chromatic items run round the hue wheel (red -> orange -> yellow -> green -> blue -> pink);
    # achromatic ones have no hue at all and are kept together at the end, ordered dark to light,
    # rather than being scattered through the colors.
    COLOUR_SORT_MIN = 30

    # ⚠️ HUE ALONE IS NOT ENOUGH, AND `chroma` IS THE WRONG GATE. Sorting by (hue, light) files a
    # solid orange, a black sleeve and a cream one side by side whenever they share a hue peak:
    # Galactic Melt, Hot Corner and Please Mr. Postman all sit at hue 5.0. And `chroma` counts any
    # pixel carrying a tint, so a pale wash scores 0.885 while reading as white. `punch` — mean
    # saturation weighted DOWN toward white and black, from crvi_hue.py — is what the eye grades on.
    # Todd chose the arrangement on 2026-09-04: whites first, then the colour wheel, then to black,
    # one continuous ramp, at the looser 0.20 bar so the coloured run stays long (about a third of
    # the archive rather than an eighth).
    # ⚠️ AND `punch` PENALISES DARKNESS ITSELF, so a deep saturated red scores ~0.15 and looks
    # neutral to the bar above. 279 dark items that carry real colour — Klarwein's Moses, the
    # Cieślewicz, the Awazu — were being filed into a grey ramp ordered by lightness alone. Todd,
    # 2026-09-04: *"still doesn't feel perfect. Especially on the darker side of things."*
    # So the dark end gets its OWN wheel, gated on `chroma` (which does not care how dark a pixel
    # is) and running the same direction, so the bright pinks roll straight on into the dark reds
    # and the ramp lands on dark blues before it reaches the greys.
    PUNCH_BAR = 0.20     # reads as coloured at all
    DARK_BAR  = 0.30     # dark, but carries enough colour to be worth grouping by hue
    PALE      = 0.62     # a neutral above this leads the ramp; below it, it trails
    def color_order(idxs):
        def key(i):
            it = items[i]
            h = it.get("hue")
            lt = it.get("light") if it.get("light") is not None else 0.5
            p = it.get("punch") or 0.0
            c = it.get("chroma") or 0.0
            if h is not None and p >= PUNCH_BAR:
                return (1, h, -lt)                    # the bright wheel, light to dark within a hue
            if lt >= PALE:
                return (0, -lt, 0.0)                  # whites lead
            if h is not None and c >= DARK_BAR:
                return (2, h, -lt)                    # the dark wheel
            return (3, -lt, 0.0)                      # true greys, down to black
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
                f'<div class="inner"><img src="../../../{esc(it["thumb"] or it["image"])}"'
                + (f' data-gif="../../../{esc(it["image"])}" class="anim"' if it.get("animated") else "")
                + (f' data-video="../../../{esc(it["image"])}" class="anim"' if it.get("video") else "")
                + ' loading="lazy" alt=""></div>'
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
        '<meta name="robots" content="noindex,nofollow">'
        f'<meta http-equiv="refresh" content="0; url={items[0]["id"]}/">'
        f'<link rel="canonical" href="{items[0]["id"]}/">'
        '<title>Crambe Repetita Museum</title></head>'
        f'<body><a href="{items[0]["id"]}/">Enter the museum</a></body></html>')

    # ---- /all/ — the whole museum as one contact sheet ----
    # Todd, 2026-08-28: "as though it's a tag page for simply everything". So it is literally
    # that: the same cell, the same hover-enlarge, the same colour grouping every tag page over
    # 30 items already uses — just smaller tiles, because 375 of them have to fit.
    # ⚠️ Todd, 2026-08-28: /all/ opens in CRVI ORDER, not colour order. Colour grouping is a
    # choice you make, not the state you arrive in — the number sequence is the archive's own
    # order and shows how it was built. Colour is still available as a toggle, applied with the
    # CSS `order` property so nothing is re-fetched or moved in the DOM when you switch.
    rank = {idx: n for n, idx in enumerate(color_order(list(range(len(items)))))}
    # ⚠️ RECENCY IS NOT CRVI ORDER. Retired numbers get reused, so a low number can hold a very
    # recent addition — CRVI000872 was minted in September between neighbours from August.
    # Sorting the grid by id would bury today's work in the middle of the archive, so this ranks
    # on the mint date, newest first, with the id only breaking ties within a single day.
    recent = sorted(range(len(items)),
                    key=lambda n: (items[n].get("minted") or "", items[n]["id"]), reverse=True)
    rrank = {idx: n for n, idx in enumerate(recent)}
    acells = []
    for i in range(len(items)):
        it = items[i]
        rest = " · ".join(filter(None, [it.get("subtitle"), it.get("year")]))
        acells.append(
            f'<a class="cell" href="../{it["id"]}/" data-c="{rank[i]}" data-r="{rrank[i]}">'
            f'<div class="inner"><img src="../{esc(it["thumb"] or it["image"])}"'
            + (f' data-gif="../{esc(it["image"])}" class="anim"' if it.get("animated") else "")
            + (f' data-video="../{esc(it["image"])}" class="anim"' if it.get("video") else "")
            + ' loading="lazy" alt=""></div>'
            f'<div class="cap"><span class="n">{esc(it["id"])}</span>'
            f'{esc(it.get("maker"))} - {esc(it.get("title"))}<br>{esc(rest)}</div></a>')
    # ⚠️ THE TWO ORDERS ARE ALTERNATIVES, NOT LAYERS. Ticking one unticks the other, because a
    # grid cannot be both grouped by colour and sorted by date. The choice persists, and the old
    # crviAllByColor key is migrated so anyone who had colour on keeps it.
    abody = ('<div class="crumb"><span class="t">ALL</span>'
             f'<span class="c">{len(items)} items</span>'
             '<label class="ord"><input type="checkbox" id="bycolor"> group by color</label>'
             '<label class="ord"><input type="checkbox" id="byrecent"> most recent</label>'
             f'<a href="../{items[0]["id"]}/">&#8592; museum</a></div>'
             f'<div class="grid small" id="allgrid">{"".join(acells)}</div>'
             '<script>' + ORDER_JS + '</script>'
             f'<script>{JS}</script>')
    os.makedirs(os.path.join(HERE, "all"), exist_ok=True)
    open(os.path.join(HERE, "all", "index.html"), "w").write(
        page("All — Crambe Repetita Museum", abody, 1))

    print(f'{len(items)} item pages · {len(by_tag)} tag pages · {len(order)} facets')
    if held:
        print(f'  {len(held)} HELD BACK, unverified: ' + ", ".join(h["id"] for h in held))
    print(f'  first {items[0]["id"]} · last {items[-1]["id"]}')


if __name__ == "__main__":
    main()
