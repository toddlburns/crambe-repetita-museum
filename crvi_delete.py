#!/usr/bin/env python3
"""Remove an item from the museum, in one command, without stranding it half-deleted.

    python3 crvi_delete.py CRVI000223 CRVI000224
    python3 crvi_delete.py CRVI000223 --dry-run

⚠️ THE NUMBER IS RETIRED, NEVER RECYCLED. The registry record is KEPT and flagged `deleted`,
and `reg.next` is untouched, so the number can never be minted again. If it were reused, an old
link to CRVI000223 would one day resolve to a completely different object and the archive would
be quietly lying about its own history. A gap in the sequence is the honest outcome.

⚠️ THIS EXISTS BECAUSE THE ORDER OF OPERATIONS IS A TRAP. Deleting used to take three commands
in a specific sequence, and the middle one — regenerating `crvi.json` — is the one that is easy
to skip, because `crvi_hue.py` also writes to that file and so *looks* like it rebuilt it. It
does not: it only stamps hue values onto whatever is already there. Skip the rebuild and the
item stays live on the site while every command you ran reports success. That happened once, on
CRVI000220, and this script is the fix.

What it does, in order:
  1. mark the record deleted, unpublished, and dated, keeping it in the registry
  2. delete the display and original files from disk
  3. rebuild `crvi.json` from the registry via the shared builder in payload.py
  4. re-render the site with build.py
  5. report what is now retired

Run `crvi_hue.py --write` afterwards only if you are also adding items; hue values for surviving
items are unaffected by a deletion.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
REG = os.path.join(HERE, "crvi_registry.json")
sys.path.insert(0, HERE)
import payload


def main(ids, dry=False):
    reg = json.load(open(REG))
    by_id = {v["id"]: (k, v) for k, v in reg["items"].items()}

    missing = [i for i in ids if i not in by_id]
    if missing:
        raise SystemExit(f"no such item: {', '.join(missing)}")
    already = [i for i in ids if by_id[i][1].get("deleted")]
    if already:
        print(f"already deleted, skipping: {', '.join(already)}")
    todo = [i for i in ids if i not in already]
    if not todo:
        return

    for cid in todo:
        _, it = by_id[cid]
        print(f'{cid}  {it.get("maker","")} — {it.get("title","")} ({it.get("year","")})')
        # the item's own paths first, then the conventional ones as a backstop for strays —
        # deduped, because for most items original_file IS originals/<id>.jpg
        cands, seen = [], set()
        # ⚠️ THE THUMBNAIL HAS TO GO TOO. `thumbs.py` skips any thumb that already exists, and
        # deleted numbers ARE reused — so a thumb left behind is served for whatever object is
        # minted onto that number next, and every script reports success. Found 2026-09-03,
        # after six deletions left six stale thumbs sitting on numbers queued for reuse.
        for f in (it.get("display"), it.get("original_file"),
                  f"images/{cid}.jpg", f"originals/{cid}.jpg", f"thumbs/{cid}.jpg"):
            if f and f not in seen:
                seen.add(f); cands.append(f)
        for f in cands:
            p = os.path.join(HERE, f)
            if os.path.exists(p):
                n = os.path.getsize(p)
                print(f"    {'would remove' if dry else 'removed'} {f} ({n/1024:.0f} KB)")
                if not dry:
                    os.remove(p)
        if not dry:
            it["deleted"] = True
            it["published"] = False
            it.setdefault("deleted_on", __import__("datetime").date.today().isoformat())
            it["notes"] = (it.get("notes") or []) + [
                f"DELETED from the museum on {it['deleted_on']}. The record is kept so {cid} "
                "stays provably retired and is never reissued."]

    if dry:
        print("\ndry run — nothing written")
        return

    json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)
    # ⚠️ THE STEP THAT IS EASY TO FORGET. Without this the site still ships the item.
    out = payload.write(reg, HERE)
    subprocess.run([sys.executable, os.path.join(HERE, "build.py")], check=True, cwd=HERE)

    gone = sorted(v["id"] for v in reg["items"].values() if v.get("deleted"))
    print(f'\n{len(out)} items live · retired {", ".join(gone)} · '
          f'next number CRVI{reg["next"]:06d}')
    stray = [c for c in todo
             if os.path.exists(os.path.join(HERE, c))
             or os.path.exists(os.path.join(HERE, "images", c + ".jpg"))
             or os.path.exists(os.path.join(HERE, "originals", c + ".jpg"))
             or os.path.exists(os.path.join(HERE, "thumbs", c + ".jpg"))
             or any(x["id"] == c for x in out)]
    print("verified fully removed" if not stray else f"⚠️ STILL PRESENT: {stray}")
    print("now commit and push")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        raise SystemExit(__doc__)
    main(args, dry="--dry-run" in sys.argv)
