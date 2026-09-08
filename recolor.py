#!/usr/bin/env python3
"""Recompute every item's `colors` from the measure that actually works.

Todd, 2026-09-07, on a muted Fantin-Latour portrait tagged orange+yellow: *"in what world does
this have orange or yellow as a dominant hue"* — then on a black-and-white Penguin cover, a pale
GRM sleeve and a third: *"all examples... that hopefully help you realize and fix what's
happened."*

What had happened: `palette()` in crvi_add.py and `hue_key()` in crvi_hue.py measured colour by
two different methods, and only one of them was any good.

  `hue_key()` (2026-09-04) weights saturation DOWN toward white and black — `punch` — because
  Todd said *"you're overrating the color sometimes, when actually the true color of note on
  something is actually just white."* It refuses a hue outright when too few pixels qualify.

  `palette()` never got that fix. It counted EVERY pixel above 13% saturation, flat and equal,
  and named the two biggest buckets. Aged paper, warm greys, skin and sepia all land in the
  orange bucket at 13%, and a vast pale ground outvotes a small area of real colour.

The result was that **ORANGE was on 1,322 of 2,495 items** — more than half the archive — and
1,246 items carried a hue name while sitting below the archive's own 0.20 colour gate. The
Penguin paperback is the clearest proof: `hue` was already None, correctly, while `colors` said
orange and yellow.

This rewrites `colors` with the same rules `hue_key()` uses:
  * near-black (l<0.10) and near-white (l>0.94) carry no usable hue
  * below 18% saturation is too grey to have one
  * qualifying pixels are WEIGHTED by s*(1-|l-0.5|), not counted flat
  * a hue must hold 22% of the weighted colour, and at least 10% of pixels must qualify at all
  * ⚠️ and the whole item must clear PUNCH 0.20 — THE SAME BAR the grid ordering uses. One
    threshold, one meaning: if the archive will not group an item by colour, it will not claim
    the item has one either.
  * whatever is left is named honestly: white, black or neutral.

    python3 recolor.py --report
    python3 recolor.py --apply
"""
import collections
import colorsys
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "crvi_registry.json")
PUNCH_BAR = 0.20          # identical to build.py's; do not let the two drift apart
HUES = [(345, 15, "red"), (15, 45, "orange"), (45, 70, "yellow"), (70, 165, "green"),
        (165, 200, "cyan"), (200, 255, "blue"), (255, 290, "purple"), (290, 345, "pink")]


def hue_name(deg):
    for lo, hi, nm in HUES:
        if (lo <= deg < hi) or (lo > hi and (deg >= lo or deg < hi)):
            return nm
    return None


def palette(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((120, 120))
    px = list(im.getdata())
    n = max(1, len(px))
    weight = collections.Counter()
    total = light_sum = punch_sum = 0.0
    dark = pale = chroma = 0
    for r, g, b in px:
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        light_sum += l
        punch_sum += s * (1.0 - abs(2.0 * l - 1.0))
        if l < 0.10:
            dark += 1
        if l > 0.90 and s < 0.12:
            pale += 1
        if l < 0.10 or l > 0.94 or s < 0.18:
            continue
        w = s * (1.0 - abs(l - 0.5))
        weight[hue_name(h * 360)] += w
        total += w
        chroma += 1
    punch = punch_sum / n
    light = light_sum / n
    out = []
    if punch >= PUNCH_BAR and chroma / n >= 0.10 and total > 0:
        for nm, wt in weight.most_common(2):
            if wt / total >= 0.22:
                out.append(nm)
    if dark > n * 0.55:
        out.append("black")
    if pale > n * 0.55:
        out.append("white")
    if not out:
        out = ["white" if light > 0.62 else ("black" if light < 0.30 else "neutral")]
    return out


def main():
    apply = "--apply" in sys.argv
    reg = json.load(open(REG))
    live = [v for v in reg["items"].values() if not v.get("deleted")]
    before = collections.Counter()
    after = collections.Counter()
    changed = 0
    for v in live:
        for c in (v.get("colors") or []):
            before[c] += 1
        p = os.path.join(HERE, "images", v["id"] + ".jpg")
        if not os.path.exists(p):
            after.update(v.get("colors") or [])
            continue
        new = palette(p)
        if new != (v.get("colors") or []):
            changed += 1
        after.update(new)
        if apply:
            v["colors"] = new
    print("items: %d   colour tags changed: %d" % (len(live), changed))
    print("\nBEFORE:", before.most_common())
    print("\nAFTER :", after.most_common())
    if apply:
        json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)
        print("\nwritten. rebuild: payload -> crvi_hue.py --write -> build.py")
    else:
        print("\n(report only — re-run with --apply)")


if __name__ == "__main__":
    main()
