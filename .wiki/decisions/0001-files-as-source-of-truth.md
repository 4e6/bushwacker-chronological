---
type: Decision
title: The text files are the source of truth, not the live playlist
description: bushwacker_playlist.txt + bushwacker_excluded.txt are authoritative; the YouTube playlist is derived from them.
status: accepted
tags: [architecture, data]
timestamp: 2026-07-27T18:15:00Z
---

# Context

Playlist state could be read live from YouTube, but anonymous reads
[cap at 100 items](/integrations/youtube-innertube.md) and the playlist has >100,
titles/dates change, and videos get (un)listed out of order.

# Decision

The two committed text files are authoritative; the live playlist is *derived*
from them. The `watch?v=<id>` lines in `bushwacker_playlist.txt` plus the
`[SHORT|META]` ids in `bushwacker_excluded.txt` together are the record of every
channel video already classified (see [source files](/domain/source-files.md)).

# Consequences

- New-video detection is a stable **ID set-difference** (channel ids − known ids),
  not "last video id" or upload dates.
- The change log is the git history of these files (the merged sync PRs).
- Writes to YouTube are one-directional and deterministic
  ([apply job](/architecture/nightly-sync.md)); the code
  [never deletes](/decisions/0003-apply-inline-and-unprotected-main.md), so the
  worst case is a misplaced entry, fixable by editing the file and re-applying.
