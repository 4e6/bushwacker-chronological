---
type: Overview
title: Bushwacker chronological playlist
description: Automated mirror of the Bushwackerhistory channel as a YouTube playlist ordered by historical period.
tags: [overview]
timestamp: 2026-07-27T18:15:00Z
---

# What this is

A curated YouTube playlist (`PLVw98VIsFGF8`) mirroring the Russian-language history
channel **Bushwackerhistory**, ordered by the **historical period each video is
about** (ancient → modern), not by upload date. A nightly GitHub Actions loop
detects new uploads, classifies each (Short / meta / period episode), dates period
episodes to a start-year sort key, inserts them into the live playlist at the right
chronological slot, and mirrors Russian subtitles.

# Map

- **How the automation works** — [nightly sync pipeline](/architecture/nightly-sync.md),
  [subtitle mirror](/architecture/subtitles.md).
- **Why it's shaped this way** — [files are the source of truth](/decisions/0001-files-as-source-of-truth.md),
  [duration-first classification](/decisions/0002-duration-first-classification.md),
  [apply inline / unprotected main](/decisions/0003-apply-inline-and-unprotected-main.md).
- **Data & vocabulary** — [source files & the period-year sort key](/domain/source-files.md).
- **Third parties** — [YouTube InnerTube](/integrations/youtube-innertube.md),
  [YouTube Data API](/integrations/youtube-data-api.md),
  [Supadata](/integrations/supadata.md).
- **How to operate it** — [manual sync](/playbooks/manual-sync.md),
  [subtitle generation](/playbooks/subtitle-generation.md),
  [operating the nightly](/playbooks/operating-the-nightly.md).
- **Working norms** — [metered-API cost discipline](/conventions/metered-api-cost-discipline.md),
  [design forks decided with the maintainer](/conventions/design-forks-collaborative.md).

# Source of truth

`bushwacker_playlist.txt` + `bushwacker_excluded.txt` are the authoritative record
of what is classified; the live YouTube playlist is derived from them. See
[source files](/domain/source-files.md).
