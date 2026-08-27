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

**Size budget.** GitHub Pages caps a published site at 1 GB. Currently ~390 MB, mostly held originals.
Check before bulk-adding anything large.

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
python3 crvi_hue.py --write    # dominant-hue keys, for colour-grouped tag pages
python3 build.py               # renders every item and tag page
git add -A && git commit && git push
```

`crvi_add.py` rewrites `crvi.json` itself, so a single add doesn't need the bulk builder.

## What lives where

- `crvi_registry.json` · `crvi_add.py` · `crvi_hue.py` · `labels.py` · `build.py` — here, in the repo,
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
