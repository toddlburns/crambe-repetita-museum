#!/usr/bin/env python3
"""Publish the museum to Cloudflare Pages.

Why this exists: GitHub Pages caps a published site at 1 GB on every plan, and on
2026-09-06 the museum's payload reached ~1,105 MB — the deploy could no longer
succeed at all. Cloudflare Pages has no size cap, and Cloudflare Access in front
of it replaces the view-source password with real server-side auth. Todd chose
the move on 2026-09-06.

⚠️ THE PRUNE MUST NOT RUN AGAINST THE WORKING TREE. `.github/prune_unserved_originals.py`
DELETES every original that no built page links. In CI that is safe — it runs on a
throwaway checkout — but run here it would destroy 2.3 GB of held originals that exist
nowhere else but git. So this stages the site into a separate directory of HARDLINKS
(same filesystem, so it is instant and costs no disk) and prunes THAT. Unlinking a
hardlink cannot touch the file in the repo.

⚠️ Cloudflare Pages limits: 20,000 files per deployment and 25 MB per file. The repo
holds 11,605 files and two originals over 25 MB (CRVI001810 at 43 MB, CRVI000812 at
56 MB) — both unserved, so the prune removes them before upload. This script re-checks
both limits and refuses to deploy rather than failing halfway.

    python3 cloudflare_deploy.py --check      # stage, prune, report — upload nothing
    python3 cloudflare_deploy.py              # stage, prune, deploy

Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in the environment, or a prior
`npx wrangler login`.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(HERE, ".deploy-stage")
PROJECT = "crambe-repetita-museum"
SKIP_TOP = {".git", ".github", ".deploy-stage", "node_modules"}
MAX_FILES = 20000
MAX_BYTES = 25 * 1024 * 1024


def stage():
    """Hardlink the publishable tree into .deploy-stage/."""
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    n = 0
    for dp, dn, fn in os.walk(HERE):
        rel = os.path.relpath(dp, HERE)
        if rel == ".":
            dn[:] = [d for d in dn if d not in SKIP_TOP]
        elif rel.split(os.sep)[0] in SKIP_TOP:
            continue
        dest = os.path.join(STAGE, rel) if rel != "." else STAGE
        os.makedirs(dest, exist_ok=True)
        for f in fn:
            if f.startswith("."):
                continue
            try:
                os.link(os.path.join(dp, f), os.path.join(dest, f))
            except OSError:                     # cross-device or already there
                shutil.copy2(os.path.join(dp, f), os.path.join(dest, f))
            n += 1
    return n


def prune():
    """Drop the originals no page links — the same script CI uses, pointed at the hardlinks.

    ⚠️ THE ROOT IS AN ARGUMENT AND MUST BE. This script DELETES. It used to take its tree
    from its own __file__ and ignore cwd, so the first version of this function ran it with
    `cwd=STAGE` and deleted 2,293 originals out of the REAL repository (recovered from git).
    The guard below is belt and braces on top of passing the path."""
    assert os.path.isdir(STAGE) and STAGE.startswith(HERE) and STAGE != HERE, STAGE
    p = os.path.join(HERE, ".github", "prune_unserved_originals.py")
    before = len(os.listdir(os.path.join(HERE, "originals")))
    r = subprocess.run([sys.executable, p, STAGE], capture_output=True, text=True)
    after = len(os.listdir(os.path.join(HERE, "originals")))
    if after != before:
        sys.exit("ABORT: the prune touched the real originals/ (%d -> %d). "
                 "Restore with: git checkout -- originals/" % (before, after))
    if r.returncode != 0:
        sys.exit("prune failed:\n" + r.stdout + r.stderr)
    return r.stdout.strip()


def audit():
    files = 0
    total = 0
    oversize = []
    for dp, dn, fn in os.walk(STAGE):
        for f in fn:
            p = os.path.join(dp, f)
            s = os.path.getsize(p)
            files += 1
            total += s
            if s > MAX_BYTES:
                oversize.append((s, os.path.relpath(p, STAGE)))
    return files, total, oversize


def main(argv):
    print("staging ...")
    print("  %d files hardlinked into %s" % (stage(), os.path.relpath(STAGE, HERE)))
    out = prune()
    if out:
        print("  " + out.replace("\n", "\n  "))
    files, total, oversize = audit()
    print("\nPAYLOAD  %d files, %.0f MB" % (files, total / 1e6))
    print("  Cloudflare limits: %d files, %d MB per file" % (MAX_FILES, MAX_BYTES // 1024 // 1024))
    ok = True
    if files > MAX_FILES:
        print("  ✗ OVER the per-deployment file limit"); ok = False
    if oversize:
        ok = False
        print("  ✗ %d file(s) over 25 MB — Cloudflare will reject the deployment:" % len(oversize))
        for s, p in oversize:
            print("      %.1f MB  %s" % (s / 1e6, p))
    if ok:
        print("  ✓ within both limits")
    if "--check" in argv:
        print("\n(--check: nothing uploaded)")
        return 0 if ok else 1
    if not ok:
        return 1
    print("\ndeploying ...")
    r = subprocess.run(["npx", "--yes", "wrangler@latest", "pages", "deploy", ".",
                        "--project-name", PROJECT, "--commit-dirty=true"],
                       cwd=STAGE)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
