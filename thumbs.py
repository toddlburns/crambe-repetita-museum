#!/usr/bin/env python3
"""A small grid image for every item — and the first frame, for the animated ones.

Todd, 2026-08-28. Two problems, one fix:
  * a tag page holding the 26 reaction GIFs pulled 101 MB, every one animating at thumbnail size;
  * every other tag page shipped the full 1600px display copies and rendered them at ~92-200px
    wide, roughly eight times the pixels the grid actually shows. /tag/color/orange/ was 39 MB
    of ordinary JPEGs.

⚠️ 600px, not 200px, because the grid's hover-to-enlarge scales a tile 3x. A thumbnail sized for
the resting state turns to mush the moment it is hovered, which is the one moment the picture is
being looked at properly.

⚠️ For an animated item this is the FIRST FRAME. The grid shows it as a still and only fetches
the GIF when hovered — the saving there comes from not setting src at all, not from pausing.
"""
import json, os, subprocess, sys, tempfile
from PIL import Image

HERE = os.path.dirname(os.path.realpath(__file__))
OUT = os.path.join(HERE, "thumbs")
MAX = 600


def main(force=False):
    os.makedirs(OUT, exist_ok=True)
    d = json.load(open(os.path.join(HERE, "crvi.json")))
    made = skipped = 0
    before = after = 0
    for it in d["items"]:
        src = os.path.join(HERE, it.get("image") or "")
        dst = os.path.join(OUT, it["id"] + ".jpg")
        if not os.path.exists(src):
            continue
        if os.path.exists(dst) and not force:
            skipped += 1
        else:
            # ⚠️ A VIDEO ITEM HAS NO FRAME PIL CAN READ. Pull the first one with ffmpeg and carry
            # on through the same sizing path, so a held MP4 gets a grid still exactly like a GIF.
            tmp = None
            if src.lower().endswith((".mp4", ".webm")):
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src,
                                "-frames:v", "1", tmp], check=True)
                im = Image.open(tmp)
            else:
                im = Image.open(src)
            if getattr(im, "n_frames", 1) > 1:
                im.seek(0)                       # animated: the still is frame one
            im = im.convert("RGB")
            im.thumbnail((MAX, MAX), Image.LANCZOS)
            im.save(dst, "JPEG", quality=86, optimize=True)
            if tmp:
                os.unlink(tmp)
            made += 1
        before += os.path.getsize(src)
        after += os.path.getsize(dst)
    print(f"{made} thumbs written, {skipped} already present")
    print(f"  grids: {before/1024/1024:.0f} MB of full images -> {after/1024/1024:.1f} MB of thumbs")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
