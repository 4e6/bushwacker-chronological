---
type: Playbook
title: Generate a subtitle for a video
description: YouTube-first via the fetch script; local Whisper when YouTube has no captions.
tags: [subtitles, oncall]
timestamp: 2026-07-27T18:15:00Z
---

# YouTube-first (what CI runs)

`python3 scripts/fetch_subtitles.py` fetches every missing
[`subtitles/<id>.ru.srt`](/architecture/subtitles.md) — yt-dlp (manual, then
auto), else [Supadata](/integrations/supadata.md) — and inserts the `_index.tsv`
row in chronological position. Re-runnable and self-healing; `DRY_RUN=1` previews,
`ONLY=<id>` limits to one video.

# No YouTube captions → Whisper (local only)

The script can't do this. Grab audio (`yt-dlp -f bestaudio`) and transcribe with
**mlx-whisper**, model `mlx-community/whisper-large-v3-turbo` (~35× realtime on
this Mac; `pip install mlx-whisper` in a venv, model auto-downloads ~1.6 GB). Save
as `subtitles/<id>.ru.srt`, watch for Whisper's trailing-silence hallucination
loops at the end, and add the `_index.tsv` row with `source = whisper`.

# Gotcha — bulk re-fetching trips bot-detection

YouTube shows "confirm you're not a bot" after ~100 back-to-back requests
(rate-based, not per-video). Fine for one new video; for a bulk pass, space
requests (`--sleep-requests 1.5`, a few seconds between videos) and, if still
blocked, `--cookies-from-browser chrome`. Per the standing preference, default to
cookieless on public data and **ask before extracting browser cookies**. The
[Supadata](/integrations/supadata.md) fallback isn't IP-blocked but **isn't** for
bulk re-fetch — every call spends a credit
([cost discipline](/conventions/metered-api-cost-discipline.md)).
