---
type: Decision
title: Apply runs inline in nightly-sync, and main stays unprotected
description: A GITHUB_TOKEN merge doesn't trigger other workflows, so the YouTube write is a gated inline job; branch protection would break the auto-merge.
status: accepted
tags: [ci, automation]
timestamp: 2026-07-27T18:15:00Z
---

# Context

The nightly opens a PR and auto-merges it with the built-in `GITHUB_TOKEN`. A
merge done with that token **does not trigger other workflows** (GitHub's
recursion guard), so the YouTube write cannot rely on a `push`-triggered workflow.

# Decision

- The **`apply`** job runs *inside* `nightly-sync.yml`, gated by the
  [`youtube-prod` environment](/architecture/nightly-sync.md), not via a push
  trigger. `playlist-apply.yml` is left as a manual / safety-net tool.
- **`main` is intentionally left unprotected.** Branch protection requiring review
  would block the bot's own auto-merge and silently break the loop.

# Consequences

- Do **not** enable required-review branch protection on `main`.
- The apply is deterministic and **never deletes** (`yt_playlist_sync.py` only
  inserts), so an unattended misclassification is recoverable — worst case a
  misplaced entry, fixed by a follow-up edit + re-apply.
- Depends on repo settings (read-only default token, "allow Actions to create
  PRs", squash-only merge) — see
  [operating the nightly](/playbooks/operating-the-nightly.md).
