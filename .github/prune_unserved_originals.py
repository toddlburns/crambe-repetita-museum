#!/usr/bin/env python3
"""Drop the held originals that the published site never serves.

THE MUSEUM STILL HOLDS EVERY ORIGINAL BYTE-FOR-BEYTE — in git, in `originals/`, forever.
This script runs only inside the Pages build, on the runner's throwaway checkout, and only
decides what rides along to the CDN. Nothing it deletes leaves the repository.

Why it exists: GitHub Pages caps a *published site* at 1 GB and that cap cannot be raised on
any plan. As of 2026-08-30 the site was 937 MB, of which 591 MB was originals that no page
links and no visitor ever requests. `build.py` deliberately does not advertise the original on
the item page (Todd: "i don't want this 1500x1500 - 0.4 mb thing in there"), so they were being
uploaded and served to no one.

An original is KEPT if either mechanism can actually put it in front of a browser:
  1. some built .html points a src= or href= at it, or
  2. an item's `display` in crvi.json points at it — this is how the 26 animated GIFs work,
     since re-encoding a GIF only degrades it (see crvi_add.py).

The `original` field that payload.py writes into crvi.json for EVERY item does NOT count. No
client JS reads it; it is dead data. ⚠️ If you ever add a "download the original" link driven
by that field, this script will happily prune the files out from under it — add the field to
the keep-set below at the same time.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "originals")
ATTR = re.compile(r'(?:src|href)\s*=\s*["\'][^"\']*?originals/([A-Za-z0-9_.\-]+)')

def keep_set():
    keep = set()
    for cur, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", ".github", "originals")]
        for f in files:
            if f.endswith(".html"):
                with open(os.path.join(cur, f), encoding="utf-8", errors="ignore") as fh:
                    keep.update(ATTR.findall(fh.read()))
    payload = os.path.join(ROOT, "crvi.json")
    if os.path.exists(payload):
        data = json.load(open(payload, encoding="utf-8"))
        items = data["items"] if isinstance(data, dict) and "items" in data else data
        for it in (items.values() if isinstance(items, dict) else items):
            d = isinstance(it, dict) and (it.get("display") or it.get("image"))
            if d and d.startswith("originals/"):
                keep.add(os.path.basename(d))
    return keep

def main():
    if not os.path.isdir(ORIG):
        print("no originals/ directory — nothing to prune"); return 0
    keep, have = keep_set(), set(os.listdir(ORIG))
    missing = keep - have
    if missing:
        print("FATAL: the site links originals that are not in originals/:", file=sys.stderr)
        for m in sorted(missing): print("  " + m, file=sys.stderr)
        return 1
    drop = have - keep
    kept_b = sum(os.path.getsize(os.path.join(ORIG, f)) for f in keep)
    drop_b = sum(os.path.getsize(os.path.join(ORIG, f)) for f in drop)
    for f in drop:
        os.remove(os.path.join(ORIG, f))
    site = sum(os.path.getsize(os.path.join(r, f))
               for r, d, fs in os.walk(ROOT) if ".git" not in r.split(os.sep)
               for f in fs)
    report = (
        f"| | files | size |\n|---|---:|---:|\n"
        f"| originals kept (actually served) | {len(keep)} | {kept_b/1e6:.0f} MB |\n"
        f"| originals held but not published | {len(drop)} | {drop_b/1e6:.0f} MB |\n"
        f"| **published site** | | **{site/1e6:.0f} MB** of the 1 GB cap |\n"
    )
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write("### Pages payload\n\n" + report + "\n")
    if site > 900e6:
        print(f"::warning::published site is {site/1e6:.0f} MB, within 10% of the 1 GB Pages cap")
    return 0

if __name__ == "__main__":
    sys.exit(main())
