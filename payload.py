#!/usr/bin/env python3
"""The one place `crvi.json` is built from the registry.

This logic used to exist twice — as `payload()` in `crvi.py` on Todd's Mac and inline in
`crvi_add.py` here — which meant two copies to keep in step and, worse, that the only way to
regenerate the payload from a machine without the Mac's IDM source files was to run an *add*.
Deleting an item therefore could not be completed from a phone session at all.

⚠️ The payload is DERIVED. The registry is the source of truth; this file can always be
rebuilt from it and should never be hand-edited.

⚠️ Deleted items are excluded here, at the one chokepoint every writer passes through. A
deleted record stays in the registry so its CRVI number is provably retired and never
reissued, but it must not reach the public payload, the site, or the files.
"""
import json, os

ARCHIVE = "Crambe Repetita Visual Inspiration"


def decade(y):
    try:
        return f"{int(y) // 10 * 10}s"
    except Exception:
        return None          # e.g. "1966/2021" — a real date, just not one decade


def build(reg):
    """Registry dict -> the list of payload items, in CRVI order, deleted ones dropped."""
    items = [i for i in sorted(reg["items"].values(), key=lambda x: x["id"])
             if not i.get("deleted")]
    out = []
    for i in items:
        tags = list(i.get("tags") or [])
        if not tags:
            # The IDM book items carry structured fields rather than tags, so their tags are
            # derived. Anything added by hand supplies its own and is left alone.
            for d in i.get("designers", []):
                tags.append({"k": "designer", "v": d})
            if i.get("artist"):
                tags.append({"k": "artist", "v": i["artist"]})
            if i.get("label"):
                tags.append({"k": "label", "v": i["label"]})
            d = decade(i.get("year"))
            if d:
                tags.append({"k": "decade", "v": d})
            tags.append({"k": "type", "v": "album cover"})
            for t, kk in (("photo", "photographer"), ("illus", "illustrator"),
                          ("art dir", "art director"), ("type", "typographer")):
                for n in (i.get("credits") or {}).get(t, []):
                    tags.append({"k": kk, "v": n})
        for c in i.get("colors", []):
            tags.append({"k": "color", "v": c})
        seen, uniq = set(), []
        for t in tags:
            k = (t["k"], t["v"])
            if k in seen or not t["v"]:
                continue
            seen.add(k)
            uniq.append(t)
        if i.get("maker") is not None:                    # explicitly-specified item
            maker, title, sub = i.get("maker", ""), i.get("title", ""), i.get("subtitle", "")
        else:                                             # IDM album shape
            maker, title = i.get("artist", ""), i.get("title", "")
            ds = i.get("designers") or []
            sub = (("Designed by " if (i.get("designer_source") or "").startswith("design")
                    else "Artwork by ") + ", ".join(ds)) if ds else "Designer unknown"
            if i.get("label"):
                sub += f' · {i["label"]}'
        # ⚠️ EVERY ITEM CARRIES ITS SOURCE. Todd, 2026-08-27: he wants it visible on the item so
        # nobody reads the archive as a claim of authorship. A URL where one exists; otherwise
        # the source NAMED in plain words. Never a fabricated link — a wrong URL would look
        # like provenance and be false, which is worse than saying the origin is unrecorded.
        src_url = ""
        for k in ("source_page", "source_url"):
            if (i.get(k) or "").startswith("http"):
                src_url = i[k]; break
        if not src_url and i.get("discogs_release"):
            src_url = f'https://www.discogs.com/release/{i["discogs_release"]}'
        out.append({"id": i["id"],
                    "source_url": src_url,
                    "source_label": i.get("source_label", ""),
                    "image": i.get("display") or ("images/" + i["id"] + ".jpg"),
                    "original": i.get("original_file") or ("originals/" + i["id"] + ".jpg"),
                    "original_px": i.get("original_px"),
                    "original_bytes": i.get("original_bytes"),
                    "maker": maker, "title": title, "subtitle": sub,
                    "year": str(i.get("year") or ""), "tags": uniq})
    return out


def write(reg, site):
    """Build and write `crvi.json`. Returns the item list."""
    out = build(reg)
    json.dump({"archive": ARCHIVE, "items": out},
              open(os.path.join(site, "crvi.json"), "w"), ensure_ascii=False, indent=1)
    return out
