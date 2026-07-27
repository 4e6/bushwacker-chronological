---
type: Integration
title: Supadata transcript API
description: The subtitle fallback used when yt-dlp is bot-blocked; pinned to native mode to stay in the free tier.
tags: [subtitles, api, cost]
timestamp: 2026-07-27T18:15:00Z
---

# When to use

The subtitle fallback for when [yt-dlp is bot-blocked](/architecture/subtitles.md)
from CI — the same YouTube captions, over an HTTP API datacenter IPs can reach.

# Contract

- `GET https://api.supadata.ai/v1/transcript?url=<yt>&lang=ru&mode=native`, header
  `x-api-key: <SUPADATA_API_KEY>`.
- Returns segments as `{text, offset(ms), duration(ms)}`, which map onto the same
  clip-to-next-start cue → SRT pipeline as yt-dlp's srv1.
- Long transcripts may return `202 {jobId}` (poll `/v1/transcript/{jobId}`); `206`
  means no captions available. Both handled defensively in `fetch_subtitles.py`.

# Cost — native only

Pinned to **`mode=native`** (existing captions only, **~1 credit/call**) and
**never** the AI-transcription modes (`auto` / `generate`, **2 credits per
video-minute** → a 2 h episode ≈ 240 credits, past the 100-credit/month free
tier). Videos with no captions go to free local Whisper instead, and a new episode
is fetched **once** (cached, reused across steps). Rationale:
[metered-API cost discipline](/conventions/metered-api-cost-discipline.md).

# Config

`SUPADATA_API_KEY`: locally read from `.env`; in CI a repo secret (`gh secret set
SUPADATA_API_KEY`). If unset, the fallback is simply skipped.
