#!/usr/bin/env python3
"""Give items a `movement` facet — carefully, not by whoever made them.

Todd's worry, 2026-09-06, and it is the right one: *"some might get looped into
a movement because of the artist... but aren't actually an example of the
movement per se."* That is exactly what the first pass did. Works arrived in
batches named after a movement and every item in the batch got that name in its
`subject` tag, so Kandinsky's 1906 *Couple Riding* sits under Der Blaue Reiter
five years before the group existed, and Picasso's *Old Guitarist* sits under
Cubism four years before Cubism.

So the test here is the WORK, not the maker:

1. **The work must fall inside the movement's active window.** This is the rule
   that does most of the work, and the windows below are the judgement call —
   they are meant to be edited. An artist may be a founder and still have made
   the picture in front of you decades early or late.
2. **The maker must be named.** An unattributed item cannot be shown to
   participate in anything, so it is never auto-tagged.
3. **The object must be the art, not a document or a later restaging.** A
   photograph *of* an artist, a contemporary illustration of a Bauhaus building,
   a 2024 portrait of Robert Filliou — none of these belong to the movement they
   depict.

Anything failing 1 because its date is simply unknown is HELD, not guessed, and
listed for review. Holding is the whole point: a wrong tag in a browsable
archive is worse than a missing one, because nobody goes looking for it.

    python3 movement_tags.py --report     # propose and print, change nothing
    python3 movement_tags.py --apply      # write `movement` extra_tags
"""
import json
import os
import re
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "crvi_registry.json")

# (first year, last year) the movement was itself, not the years its members
# lived. Deliberately generous at the edges where scholars disagree; deliberately
# hard at the ends where a work is plainly before or after the thing.
WINDOW = {
    "Pre-Raphaelite":        (1848, 1900),
    "Aestheticism":          (1860, 1900),
    "Pointillism":           (1884, 1906),
    "Symbolism":             (1886, 1910),
    "Nabis":                 (1888, 1903),
    "Art Nouveau":           (1890, 1910),
    "Fauvism":               (1904, 1910),
    "Die Brücke":            (1905, 1913),
    "Cubism":                (1907, 1925),
    "Futurism":              (1909, 1944),
    "Der Blaue Reiter":      (1911, 1914),
    "Orphism":               (1912, 1935),
    "Rayonism":              (1912, 1915),
    "Synchromism":           (1912, 1920),
    "Vorticism":             (1913, 1920),
    "Suprematism":           (1915, 1930),
    "Precisionism":          (1915, 1945),
    "Constructivism":        (1915, 1935),
    "Dada":                  (1916, 1925),
    "De Stijl":              (1917, 1931),
    "Purism":                (1918, 1927),
    "Bauhaus":               (1919, 1933),
    "New Objectivity":       (1920, 1933),
    "Mexican Muralism":      (1920, 1960),
    "Surrealism":            (1924, 1966),
    "American Regionalism":  (1928, 1945),
    "Social Realism":        (1929, 1950),
    "Abstract Expressionism": (1943, 1965),
    "Art Informel":          (1945, 1962),
    "Color Field":           (1948, 1975),
    "Neo-Dada":              (1953, 1965),
    "Gutai":                 (1954, 1972),
    "Pop Art":               (1956, 1975),
    "Nouveau Réalisme":      (1960, 1970),
    "Op Art":                (1960, 1972),
    "Fluxus":                (1960, 1978),
    "Minimalism":            (1960, 1978),
    "Conceptual Art":        (1965, 1978),
    "Land Art":              (1967, 1980),
    "Arte Povera":           (1967, 1975),
    "Photorealism":          (1968, 1990),
    "Neo-Expressionism":     (1975, 1995),
    "Memphis":               (1980, 1988),
    "Young British Artists": (1988, 2010),
    "Relational Aesthetics": (1992, 2015),
}

# Phrases that mean "this object is a document, a reproduction or a later
# restaging" — never the movement itself, whatever it depicts.
NOT_THE_ART = (
    "contemporary illustration", "a contemporary", "parametric model",
    "not a period", "not a work on canvas", "not a painting",
    "not fluxus", "not italian futurism", "simulation",
    "photograph of", "installation view", "press image",
    "the photographer", "modern colour photograph",
)


def year_of(item):
    """First 4-digit year in the year field. '1888–89' -> 1888, '' -> None."""
    ys = re.findall(r"(1[6-9]\d\d|20[0-2]\d)", str(item.get("year") or ""))
    return int(ys[0]) if ys else None


def claimed(item):
    """Movement names sitting in the item's `subject` tags.

    ⚠️ Reads BOTH `tags` and `extra_tags`. A batch added later can only put a
    subject on an item through `extra_tags` — writing `tags` onto an IDM-book
    item deletes every tag it derives — so a claim parked there was invisible
    here and 74 of them silently proposed nothing."""
    out = []
    for key in ("tags", "extra_tags"):
        for t in (item.get(key) or []):
            if isinstance(t, dict) and t.get("k") == "subject" and t["v"] in WINDOW:
                out.append(t["v"])
    return sorted(set(out))


def classify(item):
    """-> (list of movements to tag, list of (movement, reason) held back)."""
    tag, hold = [], []
    maker = (item.get("maker") or "").strip()
    blob = " ".join([item.get("verified_against") or "",
                     " ".join(item.get("notes") or [])]).lower()
    y = year_of(item)

    for m in claimed(item):
        lo, hi = WINDOW[m]
        # ⚠️ The registry has FOUR words for "we do not know who made this" —
        # "", "Unknown", "Unidentified" and "unattributed" — and this test used to
        # name only two of them, so an unattributed item could still be shown
        # participating in a movement.
        if maker.lower() in ("", "unknown", "unidentified", "unattributed"):
            hold.append((m, "maker not established — participation cannot be shown"))
        elif any(p in blob for p in NOT_THE_ART):
            hold.append((m, "the object is a document, reproduction or later restaging"))
        elif y is None:
            hold.append((m, "no date on the record"))
        elif y < lo:
            hold.append((m, "dated %d, before the movement (%d–%d)" % (y, lo, hi)))
        elif y > hi:
            hold.append((m, "dated %d, after the movement (%d–%d)" % (y, lo, hi)))
        else:
            tag.append(m)
    return tag, hold


def main(argv):
    reg = json.load(open(REG))
    items = [v for v in reg["items"].values() if not v.get("deleted")]
    tagged = held = 0
    by_move = collections.Counter()
    reasons = collections.defaultdict(list)

    for it in items:
        tag, hold = classify(it)
        for m, why in hold:
            held += 1
            reasons[why.split(",")[0].split("(")[0].strip()].append(
                (it["id"], it.get("maker"), (it.get("title") or "")[:44], m, why))
        if not tag:
            continue
        if "--apply" in argv:
            ex = [t for t in (it.get("extra_tags") or [])
                  if not (isinstance(t, dict) and t.get("k") == "movement")]
            ex += [{"k": "movement", "v": m} for m in sorted(set(tag))]
            it["extra_tags"] = ex
        tagged += len(tag)
        for m in tag:
            by_move[m] += 1

    print("MOVEMENT TAGS PROPOSED: %d across %d movements" % (tagged, len(by_move)))
    for m, n in sorted(by_move.items(), key=lambda x: (-x[1], x[0])):
        print("   %-24s %d" % (m, n))
    print("\nHELD BACK: %d claims, by reason" % held)
    for why, rows in sorted(reasons.items(), key=lambda x: -len(x[1])):
        print("\n  %s — %d" % (why, len(rows)))
        for r in rows[:14]:
            print("     %s  %-22s %-44s  [%s] %s" % (r[0], (r[1] or "")[:22], r[2], r[3], r[4]))
        if len(rows) > 14:
            print("     … and %d more" % (len(rows) - 14))

    if "--apply" in argv:
        json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)
        print("\nwritten to crvi_registry.json — now rebuild:")
        print("  python3 -c \"import json,payload; payload.write("
              "json.load(open('crvi_registry.json')),'.')\"")
        print("  python3 crvi_hue.py --write && python3 thumbs.py && python3 build.py")
    else:
        print("\n(report only — nothing written. Re-run with --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
