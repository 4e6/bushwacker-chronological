---
type: Playbook
title: Manual sync (fallback to the bot)
description: The 4-step manual procedure the nightly automates — find, classify, apply, verify.
tags: [sync, oncall]
timestamp: 2026-07-27T18:15:00Z
---

# When

The [nightly](/architecture/nightly-sync.md) does this hands-off. Run it by hand
only for a special case or to fix a bad classification.

# 1. Find new videos (read-only, no login)

```bash
yt-dlp --flat-playlist --no-warnings --print "%(id)s" \
  "https://www.youtube.com/@Bushwackerhistory/videos" | sort > /tmp/chan_ids.txt
{ grep -oE 'watch\?v=[A-Za-z0-9_-]{11}' bushwacker_playlist.txt | sed 's#watch?v=##'
  awk '/^\[(SHORT|META)\]/{print $2}' bushwacker_excluded.txt ; } | sort -u > /tmp/known_ids.txt
comm -23 /tmp/chan_ids.txt /tmp/known_ids.txt   # => NEW, unclassified ids
```

Use the **ID set-difference** — stable, unlike "last video id" or upload dates
([files as source of truth](/decisions/0001-files-as-source-of-truth.md)). Per id:
`yt-dlp --skip-download --print "%(duration)s s | %(upload_date)s | %(title)s" "https://youtu.be/<ID>"`.

# 2. Classify & date

[Duration-first](/decisions/0002-duration-first-classification.md): Short (≲350 s)
→ `excluded.txt`; meta → `excluded.txt`; else a period episode → pick its
[`[YEAR]`](/domain/source-files.md). For an ambiguous year, read the transcript
intro (CI does this via `fetch_transcripts.py`; by hand,
`yt-dlp --write-auto-subs --sub-langs "ru.*,ru" --skip-download`), reading the era
described, not garbled digits. No captions →
[Whisper](/playbooks/subtitle-generation.md).

# 3. Apply

**Period episode:** insert the 3-line block into `bushwacker_playlist.txt` at the
right `[YEAR]` slot; add + move it on YouTube (recipe below); bump the header's
`videos:` count and `last synced:`; fetch its subtitle
(`python3 scripts/fetch_subtitles.py`). **Short/meta:** append the `[SHORT|META]`
line to `bushwacker_excluded.txt` and bump `last synced:`. (No playlist change.)

Insert-a-new-video on YouTube (via the [InnerTube API](/integrations/youtube-innertube.md)):

1. `const all = await enumerate();` — current order + setVideoIds.
2. ADD the new video; re-`enumerate()`, find it by videoId → `newS`.
3. Predecessor = the **last** entry whose period year ≤ the new video's year (walk
   `bushwacker_playlist.txt`); get its setVideoId from `all`.
4. `ACTION_MOVE_VIDEO_AFTER {setVideoId:newS, movedSetVideoIdPredecessor:<pred.s>}`.
5. Re-`enumerate()` and confirm the order matches the file.

# 4. Verify

Re-`enumerate()` (authenticated) and confirm count, order, and no duplicates. **Do
not** trust anonymous yt-dlp or the web UI —
[they cap at 100](/integrations/youtube-innertube.md) and the playlist has >100.
