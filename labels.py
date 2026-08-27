#!/usr/bin/env python3
"""Canonical record-label names for the museum.

Todd, 2026-08-26: *"clean up labels please. history favours. warp records / warp / war facords
planet mu / virgin should be planet mu only. look for more to clean up too."*

This lives in its own module because `crvi.py` REBUILDS the label field from `idm_credits.json`
on every run — cleaning the registry by hand fixes the site once and is silently undone the next
time the bulk builder runs. Normalising here means the fix survives.

Two jobs:

1. `CANON` — merge variants of one label into one name. The book prints "Warp", Discogs says
   "Warp Records", and one OCR pass produced "War facords"; they are one label and belong on one
   tag page.

2. `split_catalogue` — a catalogue number is not part of a label's name. "Prestige LP 7020" and
   "Prestige 7113" are the same label, and left alone they make one-item tag pages that never
   join up. The number is kept in its own field rather than thrown away.

⚠️ Two traps, both hit while writing this:
  * "Pacific Jazz 1219" — a 1-4 letter prefix rule eats "Jazz" and leaves the label as "Pacific".
    Real catalogue prefixes are ALL-CAPS (LP, RLP, AS, CAS, MCF, PCS, S); "Jazz" is a word.
  * "Plus 8 Records" — the number is inside the NAME. It survives because the string ends in a
    word, and the pattern is anchored to a trailing number.

⚠️ British spellings here are the labels' actual names, not stray English: "History Always
Favours The Winners", "Recloose Organisation", "Coloursound Library". Do not Americanise them —
the same care the museum's own "colour"→"color" rename had to take.
"""
import re

CANON = {
    "warp": "Warp Records",
    "warp records": "Warp Records",
    "war facords": "Warp Records",              # OCR damage: 'p Re' -> ' fa'
    "history always favours the winners": "History Always Favours The Winners",
    "planet mu / virgin": "Planet Mu",          # two labels in one field; the release is Planet Mu
    "nova musicha - n. 8": "Cramps Records",    # nova musicha is a SERIES on Cramps
}

# Discogs' way of saying "this release has no label" — not the name of one.
NOT_A_LABEL = {"not on label", "none", "n/a", "unknown"}

# trailing catalogue number: optional ALL-CAPS prefix + digits ("LP 7020", "AS-9138",
# "RLP 12-241", "6360 025", "CAS1052", "7113")
_CAT = re.compile(r"\s+((?:[A-Z]{1,4}[- ]?)?\d[\d\-]*(?:\s+\d[\d\-]*)?)\s*$")


def split_catalogue(raw):
    """-> (label, catalogue). Catalogue is '' when there isn't one."""
    s = (raw or "").strip()
    m = _CAT.search(s)
    if not m:
        return s, ""
    stem = s[:m.start()].strip()
    if len(stem) < 2:          # the whole string was a number; leave it alone
        return s, ""
    return stem, m.group(1).strip()


def canon(raw):
    """-> (label, catalogue). Label is '' if the value does not name a label at all."""
    s = (raw or "").strip()
    if not s:
        return "", ""
    if s.lower() in NOT_A_LABEL:
        return "", ""
    lab, cat = split_catalogue(s)
    return CANON.get(lab.lower(), lab), cat


if __name__ == "__main__":
    for t in ["Warp", "War facords", "Pacific Jazz 1219", "Plus 8 Records", "Prestige LP 7020",
              "Vertigo 6360 025", "Impulse! AS-9138", "Not On Label", "Riverside RLP 12-241",
              "Coloursound Library", "Planet Mu / Virgin"]:
        print(f"  {t:24s} -> {canon(t)}")
