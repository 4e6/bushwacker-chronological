---
type: Convention
title: Metered-API cost discipline
description: Prefer the cheapest sufficient path for any metered third-party API; quantify cost before adding one; never silently exceed a free tier.
tags: [cost, apis, ci]
timestamp: 2026-07-27T18:00:41Z
---

# Norm

For any metered / paid third-party API this project calls:

- Default to the **cheapest sufficient** mode, and prefer a **free tool first**
  with the paid one only as a fallback.
- **Quantify** the credit / token / dollar cost before adding or changing an
  integration, and design so a **free tier is never silently exceeded**.
- Enforce it in **code** (a mode pin, a cap, a reuse/cache) rather than trusting
  call volume to stay low, and surface the cost trade-off to the maintainer.

# Why

The maintainer runs this on personal free-tier quotas and has repeatedly steered
designs to stay inside them. Staying free is a hard constraint, not a nicety.

# Exemplar — Supadata subtitles

The subtitle fallback pins Supadata to **`mode=native`** (existing captions,
~1 credit/call) and **never** its AI-transcription modes (2 credits per
video-*minute* → a 2 h episode ≈ 240 credits, past the 100-credit/month free
tier). Videos with no captions fall through to free local Whisper instead, and a
new episode is fetched **once** — cached and reused across the classify and mirror
steps — so it costs a single credit. Mechanics:
[Supadata integration](/integrations/supadata.md) and the
[subtitle mirror](/architecture/subtitles.md).

# Applying it

- New integration? State its pricing model and worst-case monthly cost in the
  proposal, before writing code.
- Reach for free/local paths (yt-dlp, Whisper) first; make the paid call the
  fallback, and cap or reuse it.

See also [design forks are decided with the maintainer](/conventions/design-forks-collaborative.md).
