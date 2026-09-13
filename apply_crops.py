#!/usr/bin/env python3
"""Apply the crops Todd draws in sheets/crop-final.html, then rebuild and deploy.

    python3 apply_crops.py            # apply + rebuild
    python3 apply_crops.py --deploy   # apply + rebuild + deploy + commit + push
    python3 apply_crops.py --dry-run

⚠️ CROPPING IS NOT A MATHS PROBLEM AND FOUR DETECTORS PROVED IT. Background threshold,
column variance, step-edge and a ratio fitted to Todd's own boxes were all tried; the
dumb ratio beat every detector and none was good enough to apply blind. The question is
categorical before it is numeric — is there anything extraneous, and on which edges —
and a dark band at a cover's edge can be a cast shadow or printed design. Nothing in the
pixels separates those. So the boxes here are HIS, and this script only does arithmetic.

⚠️ THE ORIGINAL IS NEVER DESTROYED. originals/ holds files that exist nowhere else and a
bad prune already deleted 2,293 of them once. The uncropped file is copied to
originals_uncropped/ before the crop is written, and each item records its box, its old
and new size, and where the uncropped copy is — so every crop reverses.

⚠️ THE SIZE GUARD IS LOAD-BEARING. A box is drawn against whatever file the browser
loaded. If the original on disk is no longer that size — because it was cropped in an
earlier run — the coordinates are meaningless, so this refuses rather than cropping
blind. That is what makes the script safe to re-run over a cumulative pick file.

⚠️ ORDER MATTERS AFTER THIS. payload.write -> thumbs.py -> crvi_hue.py --write ->
build.py. The payload rebuild drops the stamped hues, and a replaced picture keeps its
stale thumbnail unless the old one is deleted first (this script deletes it).
"""
import collections, io, json, os, shutil, subprocess, sys
from PIL import Image

HERE = os.path.dirname(os.path.realpath(__file__))
REG = os.path.join(HERE, "crvi_registry.json")
PICKS = os.path.expanduser("~/Desktop/Active Work/Contact Sheets/picks/crop-final.json")
KEEP = os.path.join(HERE, "originals_uncropped")


def find_original(i):
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        p = os.path.join(HERE, "originals", i + ext)
        if os.path.exists(p):
            return p
    return None


def main(argv):
    dry = "--dry-run" in argv
    os.makedirs(KEEP, exist_ok=True)
    reg = json.load(open(REG))
    key_of = {v["id"]: k for k, v in reg["items"].items() if not v.get("deleted")}
    done = {v["id"] for v in reg["items"].values() if v.get("crop") and not v.get("deleted")}
    picks = json.load(open(PICKS))["picks"]
    todo = [p for p in picks if p["url"] not in done]
    print("verdicts %d · already applied %d · to consider %d" % (len(picks), len(done), len(todo)))

    applied, noop, bad = [], [], []
    for p in todo:
        i, b = p["url"], p.get("box")
        W, H = p["natural"]
        if p["verdict"] != "crop" or not b:
            noop.append((i, "leave as is")); continue
        if b[0] <= 0 and b[1] <= 0 and b[2] >= W and b[3] >= H:
            noop.append((i, "whole frame")); continue
        src = find_original(i)
        if not src:
            bad.append((i, "no original")); continue
        im = Image.open(src)
        if im.size != (W, H):
            bad.append((i, "size mismatch %s vs %s" % (im.size, (W, H)))); continue
        if dry:
            applied.append(i); continue
        keep = os.path.join(KEEP, os.path.basename(src))
        if not os.path.exists(keep):
            shutil.copy2(src, keep)
        box = (max(0, b[0]), max(0, b[1]), min(W, b[2]), min(H, b[3]))
        out = im.crop(box)
        if src.lower().endswith((".jpg", ".jpeg")):
            out.convert("RGB").save(src, quality=95, subsampling=0)
        else:
            out.save(src)
        nw, nh = out.size
        disp = out.convert("RGB").copy()
        disp.thumbnail((1600, 1600), Image.LANCZOS)
        disp.save(os.path.join(HERE, "images", i + ".jpg"), quality=88)
        t = os.path.join(HERE, "thumbs", i + ".jpg")
        if os.path.exists(t):
            os.remove(t)
        it = reg["items"][key_of[i]]
        it["crop"] = {"box": list(box), "was": [W, H], "now": [nw, nh],
                      "uncropped": "originals_uncropped/" + os.path.basename(src),
                      "decided": "by Todd, by hand"}
        it["original_px"] = [nw, nh]
        it["original_bytes"] = os.path.getsize(src)
        applied.append(i)

    if not dry:
        io.open(REG, "w", encoding="utf-8").write(json.dumps(reg, ensure_ascii=False, indent=1))
    print("\napplied %d · no change needed %d %s" % (
        len(applied), len(noop), collections.Counter(r for _, r in noop).most_common()))
    if bad:
        print("PROBLEMS %d:" % len(bad))
        for i, r in bad:
            print("   %s — %s" % (i, r))
    if dry or not applied:
        return 0

    run = lambda c: subprocess.run(c, cwd=HERE, check=True)
    subprocess.run([sys.executable, "-c",
                    "import json,payload; payload.write(json.load(open('crvi_registry.json')),'.')"],
                   cwd=HERE, check=True)
    run([sys.executable, "thumbs.py"])
    run([sys.executable, "crvi_hue.py", "--write"])
    run([sys.executable, "build.py"])

    cropped = [v for v in reg["items"].values() if v.get("crop") and not v.get("deleted")]
    print("\ncropped items now %d · under the 800px floor %d"
          % (len(cropped), sum(1 for v in cropped if min(v["original_px"]) < 800)))

    if "--deploy" in argv:
        run([sys.executable, "cloudflare_deploy.py"])
        run(["git", "add", "-A"])
        msg = ("Apply %d more hand-drawn crops (%d cropped in total)\n\n"
               "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>\n"
               "Claude-Session: https://claude.ai/code/session_01VnvzywV8byEszAqoGKCqAD"
               % (len(applied), len(cropped)))
        subprocess.run(["git", "commit", "-q", "-m", msg], cwd=HERE, check=True)
        run(["git", "push", "-q", "origin", "main"])
        print("deployed and pushed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
