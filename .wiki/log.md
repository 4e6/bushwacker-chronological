# Update Log

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
  modules, three [decisions](/decisions/), the [source-files data model](/domain/source-files.md),
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
