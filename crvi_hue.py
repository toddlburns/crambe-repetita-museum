#!/usr/bin/env python3
"""Give every CRVI item a dominant-hue sort key, so big tag pages can group by color.

Todd, 2026-08-26: *"any tag page in the museum that has more than 30 images to automatically
begin to group them by the dominant color from the image, so that the green go next to the
green, the red next to the red."*

The existing `colors` tags are coarse buckets (red/green/blue…) — fine for filtering, useless
for ORDERING, because everything called "red" lands in one heap with no sense of where it sits
between orange and pink. So each item also gets a hue ANGLE and a lightness, and the museum
sorts the grid by them.

How the hue is chosen:
  * skip near-black and near-white pixels, and anything too desaturated to have a hue at all;
  * weight what remains by saturation, so a small vivid area beats a large muddy one;
  * histogram into 10-degree buckets and take the PEAK, not the circular mean — a mean between
    two opposing hues lands on a color that is nowhere in the picture (red + cyan -> green);
  * refine within the winning bucket and its neighbours for a smooth ordering.

An image with almost no chromatic pixels is achromatic: it gets no hue and is ordered by
lightness at the end of the run, so the blacks, greys and whites stay together instead of being
scattered through the colors.
"""
import json, os, sys, colorsys, math

BASE = os.path.dirname(os.path.realpath(__file__))   # realpath: symlinks still resolve here
REG = os.path.join(BASE, "crvi_registry.json")
SITE = BASE
NB = 36  # 10-degree buckets


def hue_key(path):
    from PIL import Image
    try:
        im = Image.open(path)
    except Exception:
        return None
    if im.mode in ("RGBA", "LA", "P"):
        # a cut-out's transparent pixels still carry the old studio grey underneath; reading
        # them would mix a background we deliberately removed back into the item's colour
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    im.thumbnail((110, 110))
    px = list(im.getdata())
    hist = [0.0] * NB
    chroma = 0.0
    light_sum = 0.0
    # ⚠️ `chroma` below counts pixels that carry ANY tint, and that is not what the eye sees.
    # A pale wash is chromatic in every pixel and still reads as white: the Chocolate Watch Band
    # sleeve scored 0.885 there while looking cream. `punch` fixes that by weighting saturation
    # DOWN as a pixel approaches white or black, so only colour that actually reads counts.
    # Todd, 2026-09-05: "you're overrating the color sometimes, when actually the true color of
    # note on something is actually just white."
    punch_sum = 0.0
    for r, g, b in px:
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        light_sum += l
        punch_sum += s * (1.0 - abs(2.0 * l - 1.0))
        if l < 0.10 or l > 0.94:      # near-black / near-white carry no usable hue
            continue
        if s < 0.18:                   # too grey to have a hue
            continue
        w = s * (1.0 - abs(l - 0.5))   # favour saturated, mid-lightness pixels
        hist[int(h * 360) // 10 % NB] += w
        chroma += 1
    n = max(1, len(px))
    frac = chroma / n
    light = light_sum / n
    punch = punch_sum / n
    if frac < 0.10 or max(hist) <= 0:
        return {"hue": None, "light": round(light, 4), "chroma": round(frac, 4),
                "punch": round(punch, 4)}
    peak = max(range(NB), key=lambda i: hist[i])
    # refine across the peak and its two neighbours, on the circle
    num = den = 0.0
    for d in (-1, 0, 1):
        i = (peak + d) % NB
        ang = math.radians((i * 10 + 5))
        num += hist[i] * math.sin(ang); den += hist[i] * math.cos(ang)
    ang = math.degrees(math.atan2(num, den)) % 360
    return {"hue": round(ang, 2), "light": round(light, 4), "chroma": round(frac, 4),
            "punch": round(punch, 4)}


def main(write=False):
    reg = json.load(open(REG))
    items = sorted(reg["items"].values(), key=lambda x: x["id"])
    done = 0
    for it in items:
        # ⚠️ A VIDEO ITEM'S `display` IS AN MP4, WHICH PIL CANNOT OPEN. hue_key() swallows the
        # failure and returns nothing, so the item would silently drop out of every colour-sorted
        # tag page instead of erroring. Read its poster frame instead.
        disp = it.get("display") or ""
        if disp.lower().endswith((".mp4", ".webm")):
            p = os.path.join(SITE, "images", it["id"] + ".jpg")
        elif disp:
            p = os.path.join(SITE, disp)
        else:
            p = os.path.join(SITE, "images", it["id"] + ".jpg")
        if not os.path.exists(p):
            continue
        k = hue_key(p)
        if not k:
            continue
        it["hue"], it["light"], it["chroma"] = k["hue"], k["light"], k["chroma"]
        it["punch"] = k["punch"]
        done += 1
    if write:
        json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)
        # carry the keys into the museum payload
        pj = os.path.join(SITE, "crvi.json")
        d = json.load(open(pj))
        by = {v["id"]: v for v in reg["items"].values()}
        for x in d["items"]:
            s = by.get(x["id"]) or {}
            # ⚠️ `chroma` HAS TO REACH crvi.json TOO. build.py needs it to order the dark band, and
            # payload.py does not carry it — so when it was stamped only into the registry, every
            # dark item read as chroma 0 and the whole dark colour wheel silently collapsed to grey.
            x["hue"], x["light"] = s.get("hue"), s.get("light")
            x["punch"], x["chroma"] = s.get("punch"), s.get("chroma")
        json.dump(d, open(pj, "w"), ensure_ascii=False, indent=1)
    chrom = [i for i in items if i.get("hue") is not None]
    print(f"{done} items measured · {len(chrom)} have a dominant hue · "
          f"{done - len(chrom)} are achromatic (black / grey / white)")
    if chrom:
        import collections
        names = [(345, 15, "red"), (15, 45, "orange"), (45, 70, "yellow"), (70, 165, "green"),
                 (165, 200, "cyan"), (200, 255, "blue"), (255, 290, "purple"), (290, 345, "pink")]
        c = collections.Counter()
        for i in chrom:
            h = i["hue"]
            for lo, hi, nm in names:
                if (lo <= h < hi) or (lo > hi and (h >= lo or h < hi)):
                    c[nm] += 1; break
        print("  by hue family:", dict(c.most_common()))


if __name__ == "__main__":
    main("--write" in sys.argv)
