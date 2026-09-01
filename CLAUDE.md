# Crambe Repetita Museum

Public archive "Crambe Repetita Visual Inspiration" at https://toddlburns.com/crambe-repetita-museum/.
Items are numbered `CRVI000001`–`CRVI999999`. Static GitHub Pages — flat per-item directories, so a
number can be typed straight into the URL bar.

Todd's design brief: **"SUPER CLEAN. Black and white predominantly. Clinical. The art needs to be the
most important thing by far."** Fixed white theme, no dark mode. Don't add chrome.

## The rules that matter

**`crvi_registry.json` is the source of truth.** It is keyed by a stable `identity` string, and CRVI
numbers are **permanent**. Re-running an add with the same `identity` updates that record; changing an
identity mints a duplicate number for the same object. Never rewrite an identity to tidy it up.

**The publishing bar is one credible source — not two.** Todd's words: *"discogs is fine to confirm…
you don't need two agreeing sources… just one credible enough source is fine."* A museum, Discogs, an
auction house or a dealer listing all qualify. A personal blog usually does not — a student portfolio
was once nearly published as an Awazu. An item whose identity can't be established keeps its number and
waits unpublished, or is published with a record that says plainly what is *not* known. **Never dress a
guess as a fact.** A wrong attribution in an archive outlives whoever wrote it.

**Originals are held.** `originals/` is the byte-for-byte best file we have; `images/` is a display
derivative. An item may set `display` to override what the page loads (alpha PNG cut-outs, animated
GIFs). Animated items point `display` at the original — re-encoding a GIF only degrades it, and a
byte-identical second copy wastes the Pages budget.

**Size budget.** GitHub Pages caps a published site at 1 GB and **that cap cannot be raised on any
plan** — Free, Pro and Enterprise all get 1 GB. The repository is bigger than the site it publishes:
`.github/workflows/pages.yml` builds the site with `.github/prune_unserved_originals.py`, which omits
every original that no page actually links. The originals stay in the repo, byte-for-byte; they just
do not ride along to the CDN.

As of 2026-08-30: repository ~940 MB, **published site ~350 MB** (26 animated GIFs are the only
originals served, at 106 MB; the other 667 were 591 MB of files no visitor ever requested). Each Pages
run prints the live figure to the job summary and warns past 900 MB, so check a recent run rather than
trusting this line. Still measure before bulk-adding: images/ and thumbs/ are published in full.

## Adding an item

Write a spec JSON, then run the adder:

```bash
python3 crvi_add.py spec.json
```

The spec needs: `identity`, `image` (URL or local path), `maker`, `title`, `year`, `tags`, and
`verified_against`. That last field **is** the publishing gate — non-empty and not starting with
"nothing" means it goes live. Optional: `subtitle`, `notes`, `source_url`, `source_page`.

Then rebuild and publish:

```bash
python3 thumbs.py              # 600px grid thumbnails — REQUIRED, see below
python3 crvi_hue.py --write    # dominant-hue keys, for colour-grouped tag pages
python3 build.py               # renders every item and tag page
git add -A && git commit && git push
```

⚠️ **`thumbs.py` is not optional and nothing else calls it.** `payload.py` points every grid tile at
`thumbs/<id>.jpg` unconditionally, so an item added without a thumbnail renders as a broken image on
the home page and on every tag page it belongs to — while `crvi_add.py`, `crvi_hue.py` and `build.py`
all report success. That happened on 2026-08-29 to 109 items added across one session. Run it after
every add, and after replacing any item's artwork (delete that item's stale thumb first).

`crvi_add.py` rewrites `crvi.json` itself, so a single add doesn't need the bulk builder.

## Deleting an item

```bash
python3 crvi_delete.py CRVI000223 CRVI000224     # --dry-run to see it first
```

⚠️ **Use the script, not the steps by hand.** Deletion is a three-stage sequence and the middle
stage — rebuilding `crvi.json` — is easy to skip, because `crvi_hue.py` also writes to that file
and so looks like it rebuilt it. It doesn't; it only stamps hue values onto what's already
there. Miss the rebuild and the item stays live on the site while every command reports success.
That happened once, on CRVI000220.

⚠️ **Deleted numbers ARE reused** — Todd, 2026-08-27: *"i'm happy to re-mint things to anything
that has been previously deleted."* The next `crvi_add.py` takes the **lowest retired number**
before reaching for `reg.next`, so the sequence stays dense. This reverses the earlier rule and
the cost is accepted: a link to a deleted number will eventually resolve to a different object
rather than staying dead. The displaced record is kept under `previously` on the new item, so
what the number used to hold is still recorded.

`payload.py` is the single builder for `crvi.json`, shared by `crvi_add.py`, `crvi.py` and
`crvi_delete.py` — deleted items are excluded there, at the one chokepoint every writer passes.

⚠️ **The publishing gate has to survive the payload too.** `build.py` filters on
`i.get("published", True)`, so a payload that omits the flag renders every HELD item live while
`crvi_add.py`, `crvi_hue.py` and `build.py` all report success. `payload.py` dropped it for
months; three unattributed paintings went to the site that way on 2026-09-01 before it was
caught. It now carries `published` explicitly, and `build.py` prints a line naming every item it
held back — if that line is missing when you know something is unverified, something is wrong.

## What lives where

- `crvi_registry.json` · `crvi_add.py` · `crvi_delete.py` · `crvi_hue.py` · `labels.py` ·
  `payload.py` · `build.py` — here, in the repo,
  so the whole pipeline is reachable from any machine (including a session started from a phone).
- `crvi.py` — the IDM-book bulk builder, still on Todd's Mac at `~/Desktop/Graphic Design/_catalog/`,
  because it reads `FINAL/` and the Discogs credit files. It writes to the registry *here*.
- The old `_catalog` paths are symlinks to this repo, so existing habits keep working.

⚠️ `crvi.py` rebuilds `label` and other fields from its source credit files on every run, so cleaning
the registry by hand is silently undone next time it runs. Normalisation belongs in `labels.py`.

## Tag vocabulary

Facets in use: `designer`, `artist`, `label`, `decade`, `color`, `type`, `photographer`, `illustrator`,
`art director`, `typographer`, `client`, `location`, `subject`, `medium`. Designer names are
**forename first** ("Ernst Reichl", not "Reichl, Ernst"). Prefer an existing `type` value over minting a
near-duplicate. Tag pages with more than 30 images group by dominant colour automatically.

Spelling: American English throughout the interface ("color", not "colour") — but never Americanise a
proper name. `History Always Favours The Winners`, `Coloursound Library` and `Recloose Organisation`
are labels' actual names and stay as they are.
