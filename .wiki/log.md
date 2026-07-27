# Update Log

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
