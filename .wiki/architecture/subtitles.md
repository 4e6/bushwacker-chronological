---
type: Module
title: Subtitle mirror
description: The committed Russian-caption mirror of the playlist and the self-healing fetch pipeline behind it.
tags: [subtitles, ci]
timestamp: 2026-07-27T18:15:00Z
sources: [scripts/fetch_subtitles.py, scripts/fetch_transcripts.py]
source_commit: f2cc7148945f446ee9e4aa4c55f0f7062a1ca38a
---

# Responsibility

A full Russian-caption mirror of the playlist lives in `subtitles/` (committed):
one `subtitles/<id>.ru.srt` per playlist video, plus `subtitles/_index.tsv`
recording provenance (see [source files](/domain/source-files.md)). It is a
**parallel asset**, not part of playlist membership.

# Fetch pipeline

`fetch_subtitles.py` is driven by "is any playlist video missing a `.ru.srt`?"
(not by whether there is a new video), so a fetch that failed before is retried on
later runs until it lands. Per missing video, the source order is:

1. **Per-run cache** — a transcript `fetch_transcripts.py` already fetched this
   run (`.subs_cache/<id>.json`), so a new episode is fetched only **once**.
2. **yt-dlp** manual subs, then auto-captions (free) — YouTube's clean **srv1**
   timedtext, not the 2 MB "rolling" `.vtt`.
3. **[Supadata](/integrations/supadata.md)** (`source = supadata`) when yt-dlp is
   bot-blocked — the same YouTube captions over an API datacenter IPs can reach.
4. Nothing anywhere → left for **local Whisper**
   (see [subtitle generation](/playbooks/subtitle-generation.md)).

Best-effort throughout (`continue-on-error`): a subtitle gap never blocks the
playlist sync, and provenance (`yt-auto` / `yt-manual` / `supadata` / `whisper`)
is recorded honestly in `_index.tsv`.

# Classify-time prefetch

`fetch_transcripts.py` runs *before* the classifier to fetch the first ~15–20 min
of a new episode's captions as `transcript_intro`
([for dating](/decisions/0002-duration-first-classification.md)), caching the full
SRT so the mirror step reuses it — one [Supadata](/integrations/supadata.md)
credit feeds both. Per-video isolation + an atomic `new_videos.json` write keep
that handoff safe.

# Gotchas

- **`.srt` is gitignored globally** (`*.srt`) **except `subtitles/*.srt`** — a
  `!subtitles/*.srt` negation un-ignores the mirror, so new files are tracked with
  a plain `git add`. Scratch `.srt` elsewhere stays ignored.
- yt-dlp bot-blocking is the norm from CI — the reason [Supadata](/integrations/supadata.md)
  exists as a fallback, and why bulk re-fetching needs care
  ([subtitle generation](/playbooks/subtitle-generation.md)).
