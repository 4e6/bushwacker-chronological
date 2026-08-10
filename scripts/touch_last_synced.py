#!/usr/bin/env python3
"""Bump the `last synced:` date in both source files, so the repo has a commit.

GitHub disables scheduled workflows in a **public** repo after 60 days with no
repository activity, and this repo goes silent exactly when the channel does: no
upload → no classification, and with the subtitle mirror complete the backfill
changes nothing either. A quiet month is therefore a month with zero commits, so
without this the nightly switches itself off mid-drought — and the upload that
ends the drought is precisely the one it would then miss. @Bushwackerhistory has
gone quiet for 76 days (Dec 2025–Mar 2026) and 67 days (Apr–Jul 2026), so this is
the normal case, not the edge case. Called monthly by nightly-sync's `keepalive`
job; ops-watch's `gha-nightly-sync` check is the backstop if it ever fails.

Writing the header date is bookkeeping the files already promise rather than a
dummy commit: `last synced:` is only ever bumped today when the *contents* change,
so it understates the truth — the nightly has verified these files against the
channel every night since. This makes it mean what it says.

No-op (exit 0, nothing written) if both files already carry today's date, so
running it twice in a day produces no second commit.

Usage:  python3 scripts/touch_last_synced.py
Env: SYNC_DATE (YYYY-MM-DD, default today UTC) — set it to pin the date in tests.
"""
import os
import re
import sys
from datetime import datetime, timezone

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ("bushwacker_playlist.txt", "bushwacker_excluded.txt")
# Both headers carry "Последняя синхронизация / last synced: YYYY-MM-DD" — the
# playlist's line also holds the `videos:` count, so anchor on the English half.
DATE_RE = re.compile(r"(last synced:\s*)(\d{4}-\d{2}-\d{2})")


def main() -> int:
    date = os.environ.get("SYNC_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        print(f"error: SYNC_DATE must be YYYY-MM-DD, got {date!r}", file=sys.stderr)
        return 1

    changed = False
    for name in FILES:
        path = os.path.join(PROJ, name)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        # Fail loudly rather than silently writing nothing: a header that stopped
        # matching means the format drifted, and a keepalive that quietly does
        # nothing is the one failure mode this whole script exists to prevent.
        new_text, n = DATE_RE.subn(rf"\g<1>{date}", text, count=1)
        if n == 0:
            print(f"error: no 'last synced:' header found in {name}", file=sys.stderr)
            return 1

        if new_text == text:
            print(f"{name}: already {date}")
            continue
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        print(f"{name}: last synced → {date}")
        changed = True

    if not changed:
        print("nothing to do — both files already carry today's date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
