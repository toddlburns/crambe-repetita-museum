#!/usr/bin/env python3
"""Mint a CRVI number for a single item and put it in the museum.

Todd's rule: *"Each item that I finalize as hi-res and say 'give it an item number,' it should
go in as a new CRVI entry."* `crvi.py` does the IDM book in bulk; this does one thing at a time
from anywhere — a museum record, a scan, a photograph.

⚠️ The registry is the source of truth and numbers are permanent. This APPENDS: it reads
`crvi_registry.json`, mints the next number, writes the item, and never touches an existing one.
An item's `identity` is what makes a re-run idempotent — pass the same identity twice and it
updates that record instead of minting a second number for the same object.

Usage:
    python3 crvi_add.py item.json
where item.json carries at least: identity, image (path or url), maker, title, and tags.
"""
import json, os, re, shutil, sys, urllib.request, collections
import labels

BASE = os.path.dirname(os.path.realpath(__file__))   # realpath: symlinks still resolve here
ROOT = os.path.dirname(BASE)
REG = os.path.join(BASE, "crvi_registry.json")
SITE = BASE
UA = "TasteProfile/1.0 (personal research)"

HUES = [(345, 15, "red"), (15, 45, "orange"), (45, 70, "yellow"), (70, 165, "green"),
        (165, 200, "cyan"), (200, 255, "blue"), (255, 290, "purple"), (290, 345, "pink")]


def palette(path):
    try:
        from PIL import Image
        import colorsys
        im = Image.open(path).convert("RGB"); im.thumbnail((80, 80))
        b = collections.Counter(); dark = light = 0
        for r, g, bl in im.getdata():
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, bl/255)
            if l < 0.14: dark += 1; continue
            if l > 0.90 and s < 0.12: light += 1; continue
            if s < 0.13: continue
            deg = h*360
            for lo, hi, nm in HUES:
                if (lo <= deg < hi) or (lo > hi and (deg >= lo or deg < hi)):
                    b[nm] += 1; break
        n = im.size[0]*im.size[1]
        out = [c for c, k in b.most_common(2) if k > n*0.06]
        if dark > n*0.55: out.append("black")
        if light > n*0.55: out.append("white")
        return out or ["neutral"]
    except Exception:
        return []


def fetch(src, dest):
    if re.match(r"^https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as r:
            open(dest, "wb").write(r.read())
    else:
        shutil.copy2(os.path.expanduser(src), dest)


def main(spec_path):
    spec = json.load(open(spec_path))
    reg = json.load(open(REG)) if os.path.exists(REG) else {"next": 1, "items": {}}
    ident = spec["identity"]
    existing = reg["items"].get(ident)
    if existing:
        it = existing
        print(f'{ident} already holds {it["id"]} — updating it, not minting a second number')
    else:
        it = {"id": f'CRVI{reg["next"]:06d}', "minted": spec.get("minted", "2026-08-26")}
        reg["next"] += 1
        reg["items"][ident] = it
        print(f'minted {it["id"]} for {ident}')

    # ⚠️ THE MUSEUM HOLDS THE ORIGINAL. Keep the fetched file byte-for-byte in `originals/`
    # and derive a display copy — the first version of this discarded the source after
    # resizing, which meant the archive held a reproduction and had thrown the object away.
    os.makedirs(os.path.join(SITE, "images"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "originals"), exist_ok=True)
    # ⚠️ Do not assume the object is a still JPEG. An animated GIF pushed through the resize
    # below comes out as frame 1 — the archive would hold a single frozen frame of a thing whose
    # whole content is the movement, and nothing would report an error.
    from PIL import Image
    src_ext = os.path.splitext(spec["image"].split("?")[0])[1].lower()
    if src_ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        src_ext = ".jpg"
    orig_path = os.path.join(SITE, "originals", it["id"] + src_ext)
    fetch(spec["image"], orig_path)
    with Image.open(orig_path) as im0:
        orig = im0.size
        animated = getattr(im0, "n_frames", 1) > 1
    it["original_file"] = "originals/" + it["id"] + src_ext
    if animated:
        # The object IS the loop: hold it whole and show it whole, no derivative. The display
        # file is the original file — re-encoding only degrades a GIF, and a byte-identical
        # second copy would double the published site for nothing. GitHub Pages caps a site
        # at 1 GB and this archive is already a few hundred MB of held originals.
        dest = orig_path
        it["display"] = it["original_file"]
        with Image.open(orig_path) as im1:
            it["frames"] = getattr(im1, "n_frames", 1)
    else:
        dest = os.path.join(SITE, "images", it["id"] + ".jpg")
        im = Image.open(orig_path).convert("RGB")
        im.thumbnail((1600, 1600), Image.LANCZOS)
        im.save(dest, "JPEG", quality=88, optimize=True)
    it["original_px"] = list(orig)
    it["original_bytes"] = os.path.getsize(orig_path)

    it.update({k: v for k, v in spec.items() if k not in ("image", "tags")})
    it["identity"] = ident
    it["label"], _cat = labels.canon(it.get("label"))   # same canon as the bulk builder
    if _cat: it["catalogue"] = _cat
    it["source_image"] = spec["image"]
    it["source_px"] = list(orig)
    if not it.get("colors"):
        it["colors"] = palette(dest)
    it["tags"] = spec.get("tags", [])
    # ⚠️ THE PUBLISHING GATE. An item goes live only when its identity is established by at
    # least ONE credible source (Todd's bar: "just one credible enough source is fine" — not
    # two). Anything else keeps its permanent number and waits without a page.
    v = (spec.get("verified_against") or "").strip()
    established = bool(v) and not v.lower().startswith("nothing")
    it["identity_established"] = established
    it["published"] = established
    it["verification"] = v
    print(f'  {"PUBLISHED" if established else "HELD — no credible source yet"}')
    json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)
    shown = f'{it["frames"]} frames held whole' if animated else \
        f'{orig[0]}x{orig[1]} -> ' + "x".join(str(v) for v in Image.open(dest).size)
    print(f'  image {orig[0]}x{orig[1]} · {shown}  colors {it["colors"]}')

    # ---- rewrite the museum payload from the registry ----
    # ⚠️ A DELETED item stays in the registry so its number stays provably retired and the
    # history is kept, but it must not reach the public payload, the site, or the files.
    items = [i for i in sorted(reg["items"].values(), key=lambda x: x["id"])
             if not i.get("deleted")]
    out = []
    for i in items:
        tags = list(i.get("tags") or [])
        if not tags:                       # the IDM items carry structured fields, not tags
            for d in i.get("designers", []): tags.append({"k": "designer", "v": d})
            if i.get("artist"): tags.append({"k": "artist", "v": i["artist"]})
            if i.get("label"): tags.append({"k": "label", "v": i["label"]})
            y = i.get("year")
            if y and y.isdigit(): tags.append({"k": "decade", "v": f"{int(y)//10*10}s"})
            tags.append({"k": "type", "v": "album cover"})
            for t, kk in (("photo", "photographer"), ("illus", "illustrator"),
                          ("art dir", "art director"), ("type", "typographer")):
                for n in (i.get("credits") or {}).get(t, []): tags.append({"k": kk, "v": n})
        for c in i.get("colors", []): tags.append({"k": "color", "v": c})
        seen, uniq = set(), []
        for t in tags:
            k = (t["k"], t["v"])
            if k in seen or not t["v"]: continue
            seen.add(k); uniq.append(t)
        if i.get("maker") is not None:                       # explicitly-specified item
            maker, title, sub = i.get("maker", ""), i.get("title", ""), i.get("subtitle", "")
        else:                                                # IDM album shape
            maker, title = i.get("artist", ""), i.get("title", "")
            ds = i.get("designers") or []
            sub = (("Designed by " if (i.get("designer_source") or "").startswith("design")
                    else "Artwork by ") + ", ".join(ds)) if ds else "Designer unknown"
            if i.get("label"): sub += f' · {i["label"]}'
        out.append({"id": i["id"], "image": i.get("display") or ("images/" + i["id"] + ".jpg"),
                    "original": i.get("original_file") or ("originals/" + i["id"] + ".jpg"),
                    "original_px": i.get("original_px"),
                    "original_bytes": i.get("original_bytes"),
                    "maker": maker, "title": title, "subtitle": sub,
                    "year": str(i.get("year") or ""), "tags": uniq})
    json.dump({"archive": "Crambe Repetita Visual Inspiration",
               "items": out}, open(os.path.join(SITE, "crvi.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f'  archive now {len(out)} items · next number CRVI{reg["next"]:06d}')


if __name__ == "__main__":
    main(sys.argv[1])
