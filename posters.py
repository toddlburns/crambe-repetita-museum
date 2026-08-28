#!/usr/bin/env python3
"""First frame of every animated item, as a still, for the grids.

Todd, 2026-08-28: a tag page holding the reaction GIFs was pulling **101 MB** — all 26 GIFs at
full size, every one of them animating, just to show a wall of thumbnails. So the grids load a
still and fetch the GIF only when the pointer is actually on it.

⚠️ The saving comes from NOT SETTING src, not from CSS. A hidden or paused <img> whose src is
the GIF has already been downloaded; the browser fetches on src assignment. So the grid ships
`src=poster` with the GIF in a data attribute, and the swap happens on hover.
"""
import json, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.realpath(__file__))
OUT = os.path.join(HERE, "posters")


def main():
    os.makedirs(OUT, exist_ok=True)
    d = json.load(open(os.path.join(HERE, "crvi.json")))
    made = skipped = 0
    saved = 0
    for it in d["items"]:
        img = it.get("image") or ""
        if not img.lower().endswith(".gif"):
            continue
        src = os.path.join(HERE, img)
        dst = os.path.join(OUT, it["id"] + ".jpg")
        if not os.path.exists(src):
            continue
        if os.path.exists(dst):
            skipped += 1
        else:
            im = Image.open(src)
            im.seek(0)
            im = im.convert("RGB")
            im.thumbnail((600, 600), Image.LANCZOS)
            im.save(dst, "JPEG", quality=86, optimize=True)
            made += 1
        saved += os.path.getsize(src) - os.path.getsize(dst)
    print(f"{made} posters written, {skipped} already there · "
          f"grids now defer {saved/1024/1024:.1f} MB until hover")


if __name__ == "__main__":
    main()
