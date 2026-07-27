---
type: Module
title: Nightly sync pipeline
description: The hands-off GitHub Actions loop that detects new uploads, classifies them, and updates the live playlist.
tags: [ci, automation]
timestamp: 2026-07-27T18:15:00Z
sources: [.github/workflows/nightly-sync.yml, .github/workflows/playlist-apply.yml, scripts/detect_new.py, scripts/classify_prompt.md]
source_commit: f2cc7148945f446ee9e4aa4c55f0f7062a1ca38a
---

# Responsibility

`nightly-sync.yml` (cron 04:00 UTC + manual dispatch) runs the whole sync loop
with **no human step**. The [manual sync playbook](/playbooks/manual-sync.md) is
the set of rules it automates.

# Pipeline (job `sync`)

1. **`detect_new.py`** — reads the channel **RSS feed** (channel_id
   `UCGzfpg1YiBIlgcODQI4lDvQ`), diffs against the ids already in the two
   [source files](/domain/source-files.md), and enriches each new id with
   duration + description via the [Data API](/integrations/youtube-data-api.md).
   RSS + API, **not yt-dlp** — see [Gotchas](#gotchas). Skips the rest if nothing
   is new.
2. **`fetch_transcripts.py`** — before the LLM, adds each new episode's
   `transcript_intro` for dating (see [subtitle mirror](/architecture/subtitles.md)).
3. **`claude -p`** with `classify_prompt.md` — classifies each new video (Short /
   meta / period, [duration-first](/decisions/0002-duration-first-classification.md))
   and edits the text files. The LLM **only edits files**: no YouTube token, no
   network/Bash, and it treats titles/descriptions/transcripts as untrusted.
4. **`fetch_subtitles.py`** — backfills any missing `.ru.srt`
   (see [subtitle mirror](/architecture/subtitles.md)).
5. **create-pull-request** opens a PR on `sync/auto` for anything tracked that
   changed, then **auto-merges** it (squash — the repo's only enabled method). The
   merged PRs are the change log.

# Job `apply`

Runs only when `bushwacker_playlist.txt` changed (a period episode was added):
`yt_playlist_sync.py` (`APPLY=1`) inserts the new video at its chronological
position via the [Data API](/integrations/youtube-data-api.md). Deterministic, no
LLM, gated by the **`youtube-prod`** environment (deployment branch = `main`).
Shorts/meta touch `excluded.txt` only → `apply` is skipped, nothing hits YouTube.

`apply` runs *inline* here rather than on a push trigger because
[GITHUB_TOKEN merges don't trigger workflows](/decisions/0003-apply-inline-and-unprotected-main.md).

# Boundaries

- The classifier never holds the YouTube token; only `detect_new.py` and the
  `apply` job do, and **only `apply` writes** to YouTube.
- `playlist-apply.yml` is a **manual / safety-net** tool (Actions tab: `dry-run` /
  `apply`), or it fires on a **human** push to `main` that changes the playlist
  file. The bot's GITHUB_TOKEN merges don't trigger it → no double-apply.

# Operating

Normal operation, manual runs, and recovery:
[operating the nightly](/playbooks/operating-the-nightly.md).

# Gotchas

- **yt-dlp is bot-blocked from datacenter IPs**, so the detector uses RSS + the
  Data API, and subtitles fall back to [Supadata](/integrations/supadata.md). A
  genuinely-missed upload is caught on a later run — the ID set-difference is
  stable ([files as source of truth](/decisions/0001-files-as-source-of-truth.md)).
