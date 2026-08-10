---
type: Data Model
title: Source files & the period-year sort key
description: Formats of bushwacker_playlist.txt, bushwacker_excluded.txt, and subtitles/_index.tsv, and the [YEAR] sort key.
tags: [data, domain]
timestamp: 2026-08-10T00:00:00Z
---

# bushwacker_playlist.txt

Human-readable mirror of the playlist — only the included (period) videos, sorted
chronologically ascending. Each entry is 3 lines:

```
[ 1096]  Крестовые походы (с 1096)
        ▶ Крестовые походы
        https://www.youtube.com/watch?v=hq9QEJjYWuY
```

The `watch?v=<id>` lines are the authoritative record of playlist membership. A
header carries the `videos:` count and `last synced:` date.

`last synced:` (present in **both** files) means *the sync last verified this file
against the channel* — not "the contents last changed". The classifier bumps it
when it edits a file, and `touch_last_synced.py` bumps it monthly otherwise, which
is also what keeps the nightly's cron
[from being auto-disabled](/architecture/nightly-sync.md#job-keepalive). Nothing
parses it; it is informational.

# bushwacker_excluded.txt

Channel videos deliberately **not** in the playlist (Shorts + meta), one per line:
`[SHORT|META]  <video_id>  <title>  — reason`. Exists so they aren't re-detected
as "new" every sync.

> **Invariant:** the video ids in these two files together = **every** channel
> video already classified. New-video detection depends on it — see
> [files as source of truth](/decisions/0001-files-as-source-of-truth.md).

# The `[YEAR]` sort key

`[YEAR]` = the **start year of the historical period** the video is about.
Negative = BCE, positive = CE, smaller = older; the file sorts ascending. For a
broad span, use the start of the polity/era (Republic of Venice → 697; "Хетты" →
-1650; "Ликбез по Сирии" → 2011). Period labels stay in Russian, matching the
existing style. How the year is chosen for a new video:
[duration-first classification](/decisions/0002-duration-first-classification.md).

# subtitles/_index.tsv

`year, video_id, source, srt_file, title` in playlist order — the record of where
each subtitle came from. `source` ∈ `yt-auto` | `yt-manual` | `supadata` |
`whisper`. See [subtitle mirror](/architecture/subtitles.md).
