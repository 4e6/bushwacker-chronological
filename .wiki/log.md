# Update Log

## 2026-10-04
* **Migration**: Bundle moved from OKF v0.1 to v0.2 with the llm-wiki skill's
  `okf.py upgrade` — `sources` entries are now `resource` mappings, Decision
  `status: accepted` became `stable`, and the four pages pinned by `source_commit`
  were re-pinned by `sources_digest`.
* **Deprecation**: Retired the `decisions/` section — none of its three ADRs named
  two rejected alternatives, so each was folded into the page that owns its subject
  (`git log --diff-filter=D -- .wiki/decisions/` finds them):
  `decisions/0001-files-as-source-of-truth.md` →
  [source files](/domain/source-files.md#why-the-files-are-the-source-of-truth);
  `decisions/0002-duration-first-classification.md` and
  `decisions/0003-apply-inline-and-unprotected-main.md` →
  [nightly sync](/architecture/nightly-sync.md#why). Inbound links repointed.
* **Change**: Added `CLAUDE.md` and `AGENTS.md` to the bundle so the editing rules
  load when an agent touches it.

## 2026-08-10
* **Change**: New [keepalive](/architecture/keepalive.md) module — a monthly
  heartbeat commit. This repo is public, so GitHub disables its crons after 60
  days of no commits, and a channel drought (76 days Dec 2025–Mar 2026, 67 days
  Apr–Jul 2026) produces none. It bumps the
  [`last synced:` header](/domain/source-files.md), whose meaning is now stated
  explicitly — *last touched by the sync loop*, and **not** evidence that a sync
  succeeded. Kept in its own workflow file so a green keepalive run cannot mask a
  failed nightly from ops-watch. Failure modes and recovery:
  [operating the nightly](/playbooks/operating-the-nightly.md#if-the-nightly-stops-running-at-all).

## 2026-07-27
* **Migration**: Moved the durable detail out of `CLAUDE.md` into the wiki — the
  [nightly sync](/architecture/nightly-sync.md) and [subtitles](/architecture/subtitles.md)
  modules, three decisions (since folded into the pages they shape), the [source-files data model](/domain/source-files.md),
  three integrations ([InnerTube](/integrations/youtube-innertube.md),
  [Data API](/integrations/youtube-data-api.md), [Supadata](/integrations/supadata.md)),
  and three playbooks ([manual sync](/playbooks/manual-sync.md),
  [subtitle generation](/playbooks/subtitle-generation.md),
  [operating the nightly](/playbooks/operating-the-nightly.md)). CLAUDE.md is now a
  thin pointer; the wiki is the single source of truth for architecture, decisions,
  and mechanics.
* **Initialization**: Bootstrapped the wiki — an [overview](/overview.md) and two
  working conventions ([metered-API cost discipline](/conventions/metered-api-cost-discipline.md),
  [design forks decided with the maintainer](/conventions/design-forks-collaborative.md)),
  migrated from the agent auto-memory folder.
