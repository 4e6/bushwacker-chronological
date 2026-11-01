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

`last synced:` (present in **both** files) is *the date the sync loop last touched
this file* — the classifier bumps it when it edits one, and the
[keepalive](/architecture/keepalive.md) bumps it monthly otherwise. It is **not**
evidence that a sync succeeded that day: the keepalive writes it unconditionally
and never runs `detect_new.py`, so during a run of failing nights the date still
advances. For "did the sync actually work", read the workflow runs or ops-watch.
Nothing parses the field; it is informational.

# bushwacker_excluded.txt

Channel videos deliberately **not** in the playlist (Shorts + meta), one per line:
`[SHORT|META]  <video_id>  <title>  — reason`. Exists so they aren't re-detected
as "new" every sync.

> **Invariant:** the video ids in these two files together = **every** channel
> video already classified. New-video detection depends on it — see
> [files as source of truth](/domain/source-files.md#why-the-files-are-the-source-of-truth).

# The `[YEAR]` sort key

`[YEAR]` = the **start year of the historical period** the video is about.
Negative = BCE, positive = CE, smaller = older; the file sorts ascending. For a
broad span, use the start of the polity/era (Republic of Venice → 697; "Хетты" →
-1650; "Ликбез по Сирии" → 2011). Period labels stay in Russian, matching the
existing style. How the year is chosen for a new video:
[duration-first classification](/architecture/nightly-sync.md#why-classification-is-duration-first).

# subtitles/_index.tsv

`year, video_id, source, srt_file, title` in playlist order — the record of where
each subtitle came from. `source` ∈ `yt-auto` | `yt-manual` | `supadata` |
`whisper`. See [subtitle mirror](/architecture/subtitles.md).

# Why the files are the source of truth

The two text files are authoritative; the live playlist is *derived* from them.
The `watch?v=<id>` lines in `bushwacker_playlist.txt` plus the `[SHORT|META]` ids
in `bushwacker_excluded.txt` together are the record of every channel video
already classified.

- New-video detection is a stable **ID set-difference** (channel ids − known ids),
  so a missed upload is simply caught on a later run.
- The change log is the git history of these files (the merged sync PRs).
- Writes to YouTube are one-directional and deterministic
  ([apply job](/architecture/nightly-sync.md#job-apply)), and the code only ever
  inserts, so the worst case is a misplaced entry — fixable by editing the file
  and re-applying.

# Rejected alternatives

- **Read playlist state live from YouTube.** Anonymous reads
  [cap at 100 items](/integrations/youtube-innertube.md) and the playlist has more;
  titles and dates change, and videos get (un)listed out of order, so the live
  list is not a stable record of what was classified.
- **Detect new uploads by "last video id" or upload date.** Out-of-order
  (un)listing breaks both; the id set-difference does not.
