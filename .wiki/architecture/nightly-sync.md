---
type: Module
title: Nightly sync pipeline
description: The hands-off GitHub Actions loop that detects new uploads, classifies them, and updates the live playlist.
tags: [ci, automation]
timestamp: 2026-08-10T00:00:00Z
sources:
  - resource: .github/workflows/nightly-sync.yml
  - resource: .github/workflows/playlist-apply.yml
  - resource: scripts/detect_new.py
  - resource: scripts/classify_prompt.md
sources_digest: ddff954812696f67
---

# Responsibility

`nightly-sync.yml` (cron 04:00 UTC + manual dispatch) runs the whole sync loop
with **no human step**. The [manual sync playbook](/playbooks/manual-sync.md) is
the set of rules it automates. Its cron staying alive at all is the
[keepalive](/architecture/keepalive.md)'s job.

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
   meta / period, [duration-first](/architecture/nightly-sync.md#why-classification-is-duration-first))
   and edits the text files. The LLM **only edits files**: no YouTube token, no
   network/Bash, and it treats titles/descriptions/transcripts as untrusted.
4. **`fetch_subtitles.py`** — backfills any missing `.ru.srt`
   (see [subtitle mirror](/architecture/subtitles.md)).
5. **create-pull-request** opens a PR on `sync/auto` for anything tracked that
   changed, then **auto-merges** it (squash — the repo's only enabled method). The
   merged PRs are the change log — the only other writer is the monthly
   [keepalive](/architecture/keepalive.md), which commits straight to `main`.

# Job `apply`

Runs only when `bushwacker_playlist.txt` changed (a period episode was added):
`yt_playlist_sync.py` (`APPLY=1`) inserts the new video at its chronological
position via the [Data API](/integrations/youtube-data-api.md). Deterministic, no
LLM, gated by the **`youtube-prod`** environment (deployment branch = `main`).
Shorts/meta touch `excluded.txt` only → `apply` is skipped, nothing hits YouTube.

`apply` runs *inline* here rather than on a push trigger because
[GITHUB_TOKEN merges don't trigger workflows](/architecture/nightly-sync.md#why-apply-runs-inline-and-main-stays-unprotected).

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
  stable ([files as source of truth](/domain/source-files.md#why-the-files-are-the-source-of-truth)).

# Why

## Why classification is duration-first

A video under ~6 min (`duration_s` ≲ 350) is a **Short** → `bushwacker_excluded.txt`,
whatever its title (incl. hashtag-tagged clips and the "Истфакт №N" trivia). Only
longer videos are a **period episode** (about one era → playlist, dated to a
[`[YEAR]`](/domain/source-files.md#the-year-sort-key)) or **meta** (Q&A, "Вне
формата", a broad non-period intro → `excluded.txt`). Real episodes run ~1.5–2.5 h
(5000–8000 s), so the gap is wide.

Reliable Shorts detection is what makes the no-human-gate nightly safe; the main
residual exposure is a period episode with a *wrong year*. To cut that, the
classifier is fed a **transcript intro** (`fetch_transcripts.py`, see
[subtitle mirror](/architecture/subtitles.md)): for an ambiguous year, prefer
explicit title dates, then the intro's described era (auto-captions garble exact
digits — read the era, not scraped numbers), then the description, then
historical knowledge. Full procedure: [manual sync](/playbooks/manual-sync.md).

## Why apply runs inline and `main` stays unprotected

The PR is auto-merged with the built-in `GITHUB_TOKEN`, and a merge done with that
token **does not trigger other workflows** (GitHub's recursion guard). So the
YouTube write is the `apply` job *inside* this workflow, gated by the
`youtube-prod` environment; `playlist-apply.yml` stays a manual / safety-net tool.

- **`main` is intentionally left unprotected.** Do **not** enable required-review
  branch protection: it would block the bot's own auto-merge and silently break
  the loop.
- Depends on repo settings (read-only default token, "allow Actions to create
  PRs", squash-only merge) — see
  [operating the nightly](/playbooks/operating-the-nightly.md).
- The [keepalive](/architecture/keepalive.md) leans on the same recursion guard in
  the opposite direction (its push must *not* fire `playlist-apply.yml`). It
  carries `[skip ci]` as an independent second guard, but if this rule ever
  changes, check both.

# Rejected alternatives

- **Classify by title.** A 65 s clip can be titled "Великий западный раскол
  (1378–1417)", a full date range that looks exactly like an episode; titles lie
  about length, duration does not.
- **A `push`-triggered apply workflow.** The bot's `GITHUB_TOKEN` merge never
  fires it, so the playlist would silently stop updating.
- **Branch protection requiring review on `main`.** Blocks the auto-merge; the
  loop breaks without any error. The unattended risk it would guard against is
  bounded instead by apply being insert-only, so a misclassification is
  recoverable.
