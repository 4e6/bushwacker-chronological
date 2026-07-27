---
type: Playbook
title: Operating the nightly
description: Normal operation, manual runs, recovery, and the repo secrets/settings the loop depends on.
tags: [oncall, ci, secrets]
timestamp: 2026-07-27T18:15:00Z
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
