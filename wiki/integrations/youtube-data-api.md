---
type: Integration
title: YouTube Data API (OAuth)
description: The OAuth Data API path used from CI for durations and the deterministic playlist insert.
tags: [youtube, api, ci, secrets]
timestamp: 2026-07-27T18:15:00Z
sources:
  - resource: scripts/yt_playlist_sync.py
  - resource: scripts/mint_youtube_token.py
sources_digest: 53a24034fb4f8562
---

# When to use

`googleapis.com` is **not** datacenter-blocked like the consumer surface, so CI
uses the OAuth Data API for the two things it needs:

- **Read** — durations + descriptions for new ids (`detect_new.py` enrichment,
  decisive for [Short-vs-episode](/architecture/nightly-sync.md#why-classification-is-duration-first)).
- **Write** — the deterministic playlist insert at a chronological `position`
  (`yt_playlist_sync.py`, the [`apply` job](/architecture/nightly-sync.md)).

The same `YT_*` OAuth token does both the read and the write.

# Secrets & minting

- Repo secrets: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`. Re-mint
  with `scripts/mint_youtube_token.py` if revoked.
- The Google OAuth **consent screen must stay "In production"** — otherwise the
  refresh token expires after 7 days.

Full secret inventory + repo settings:
[operating the nightly](/playbooks/operating-the-nightly.md).

# Boundary

This is the *only* path that writes to YouTube from CI, and it **only inserts**
(never deletes) — see
[apply inline / unprotected main](/architecture/nightly-sync.md#why-apply-runs-inline-and-main-stays-unprotected).
Interactive playlist edits from a browser use the
[InnerTube API](/integrations/youtube-innertube.md) instead.
