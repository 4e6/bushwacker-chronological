---
type: Module
title: Keepalive
description: The monthly heartbeat commit that stops GitHub auto-disabling this repo's scheduled workflows during a channel drought.
tags: [ci, automation]
timestamp: 2026-08-10T00:00:00Z
sources: [.github/workflows/keepalive.yml, scripts/touch_last_synced.py]
---

# Responsibility

GitHub disables scheduled workflows in a **public** repo after 60 days of no
repository activity. This repo commits nothing during a channel drought — no
upload → no classification, and with the [subtitle mirror](/architecture/subtitles.md)
complete the backfill changes nothing either — and @Bushwackerhistory has gone
quiet for 76 days (Dec 2025–Mar 2026) and 67 days (Apr–Jul 2026). So the
[nightly](/architecture/nightly-sync.md) would switch itself off mid-drought and
miss the upload that ends it.

`keepalive.yml` (cron `41 5 1 * *` + manual dispatch) runs
`touch_last_synced.py`, which bumps the `last synced:` header in both
[source files](/domain/source-files.md), and commits it to `main`. That is the
repo's only writer outside the nightly's auto-merged PRs.

# Why a separate workflow file

Not a second job on `nightly-sync.yml`, though the cron-selector version works:
ops-watch's `gha-nightly-sync` check judges the nightly by its **most recent
completed run of that workflow file**, whichever job produced it. A green
keepalive run sharing the file would mask a nightly that failed the same morning
and close its incident as recovered. Separate files keep that signal clean, and
they also drop the cron literal from three places to one.

# Boundaries

- **Writes nothing but the two header dates.** No YouTube token, no LLM, no
  network beyond `git`.
- **Must not trigger a live playlist write.** The commit touches
  `bushwacker_playlist.txt` — exactly the path `playlist-apply.yml`'s push trigger
  watches — so it carries two independent guards: the GITHUB_TOKEN push (which
  cannot trigger workflows, the rule
  [decision 0003](/decisions/0003-apply-inline-and-unprotected-main.md) rests on)
  and `[skip ci]` in the commit message, which still holds if that credential is
  ever swapped for a PAT.
- **Not monitored by ops-watch, deliberately.** If it silently stops working,
  GitHub disables the crons ~60 days later and ops-watch reports nightly-sync as
  `workflow_disabled` within 15 minutes. The backstop is one layer out.

# Gotchas

- **A monthly cron has ~30 days of slack against a 60-day deadline, and
  `schedule` is best-effort** — GitHub delays and drops ticks under load, so a
  dropped firing lands near the line. Accepted, because of the ops-watch backstop
  above.
- **`actions/checkout` pins to the SHA from when the run was created**, so `main`
  can move underneath it (the nightly merging its sync PR, or a human push). The
  job therefore fetches and resets to a fresh `main` inside a retry loop; a
  rejected push is a lost race, never a repo fault.
- **The bump is not evidence that a sync succeeded** — see
  [`last synced:`](/domain/source-files.md).

# Operating

[Operating the nightly](/playbooks/operating-the-nightly.md#if-the-nightly-stops-running-at-all)
— what to do if the workflows are disabled anyway.
