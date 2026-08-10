---
type: Playbook
title: Operating the nightly
description: Normal operation, manual runs, recovery, and the repo secrets/settings the loop depends on.
tags: [oncall, ci, secrets]
timestamp: 2026-08-10T00:00:00Z
---

# Normal

Nothing to do. New video → nightly PR → auto-merged → (if a period episode)
YouTube updated within ~1 min. Skim the merged-PR list for the audit trail. See
the [pipeline](/architecture/nightly-sync.md).

# Manual runs

Actions → `nightly-sync` → Run; or `playlist-apply` → Run (`dry-run` = read-only
diff, `apply` = write). **Watch the first real period-episode insert** in the
Actions log — a live `playlistItems.insert` is the least battle-tested step.

# Recovery

No human gate, so a misclassification goes live — but it is recoverable: the apply
[never deletes](/decisions/0003-apply-inline-and-unprotected-main.md) (worst case
a misplaced entry, fixed by editing the file + re-applying), and
[duration-first](/decisions/0002-duration-first-classification.md) makes Shorts
reliable. Main residual exposure: a period episode with a wrong year.

Optional safety valve (not enabled): gate the auto-merge so Shorts/meta auto-merge
but period-episode PRs wait for a human glance.

# If the nightly stops running at all

GitHub disables scheduled workflows in a **public** repo after 60 days of no
repository activity — and this repo commits nothing during a channel drought (no
upload → no classification; the subtitle mirror is complete, so the backfill
changes nothing either). The channel has gone quiet for 76 and 67 days, so the
loop would switch itself off exactly when it is about to be needed.

Two things stop that being silent:

- **Prevention** — the monthly [keepalive](/architecture/keepalive.md) commits a
  heartbeat, ~30 days of slack against the deadline.
- **Detection** — ops-watch's `gha-nightly-sync` check alerts on
  `workflow_disabled` (and `overdue`) every 15 minutes.

Recovery, if it is disabled anyway:

```
gh workflow enable nightly-sync.yml && gh workflow enable keepalive.yml
gh workflow run keepalive.yml      # the commit is what resets the 60-day clock
gh workflow run nightly-sync.yml   # catches up on anything uploaded meanwhile
git fetch && git log -1 origin/main   # confirm the keepalive commit actually landed
```

That last check matters: the keepalive exits 0 *without* committing if the date is
already today (fine — something else reset the clock), and nothing else alerts on
it failing, so confirm rather than assume.

Enable **both**: the disable hits every scheduled workflow, and re-enabling only
the nightly leaves nothing to reset the clock. Nothing is lost by an outage —
detection is a set-difference against the two files
([source of truth](/decisions/0001-files-as-source-of-truth.md)), so a missed
upload is simply picked up on the next run.

> **Gotcha:** the disable takes the **whole workflow**, not just its schedule —
> `workflow_dispatch` is blocked too, so "Manual runs" above will not work until
> you re-enable it. Note `gh workflow run nightly-sync.yml` on its own commits
> nothing on a quiet channel, so it does **not** count as activity.

# Secrets & settings

- Repo secrets: `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`), the
  [`YT_*`](/integrations/youtube-data-api.md) trio, and
  [`SUPADATA_API_KEY`](/integrations/supadata.md).
- `youtube-prod` environment: no secrets of its own (uses the repo secrets), **no
  reviewer** (auto), deployment branch locked to `main`.
- Repo settings: default workflow token **read-only**, "Allow Actions to create
  PRs" **on**, all actions pinned to commit SHAs.
- **Do not enable required-review branch protection on `main`** — it breaks the
  bot's auto-merge ([why](/decisions/0003-apply-inline-and-unprotected-main.md)).
