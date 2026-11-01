# Bushwacker History — Chronological Playlist

A curated playlist of the [Bushwackerhistory](https://www.youtube.com/@Bushwackerhistory)
YouTube channel, ordered by the **historical period each video covers** (ancient to modern)
rather than by upload date.

**Playlist:** https://www.youtube.com/playlist?list=PLVw98VIsFGF8

## How it works

The playlist is maintained automatically: new uploads are classified and added overnight.
It is generated from two text files:

- [`bushwacker_playlist.txt`](bushwacker_playlist.txt): every episode in the playlist, sorted by
  a `[YEAR]` key, which is the **start year of the period** the episode covers (negative = BCE).
- [`bushwacker_excluded.txt`](bushwacker_excluded.txt): channel videos left out on purpose, such
  as Shorts and meta videos (Q&A, off-format streams).

The two files list every channel video that has been classified. The live playlist is built
from them.

A GitHub Actions job runs every night:

1. **Detect.** It reads the channel's RSS feed and picks out any video IDs that aren't in either
   file yet.
2. **Classify.** An LLM categorizes each new video. Anything under about 6 minutes is a Short
   and gets excluded. Longer videos are either meta (excluded) or a period episode, which gets
   a `[YEAR]`. The year comes from the title, the opening of the transcript, the description
   and general historical knowledge. The LLM only edits the text files and never touches
   YouTube.
3. **Record.** The changes go into a pull request that merges automatically, so the git
   history is the log of every classification.
4. **Apply.** Inserts each new episode into the YouTube playlist at its chronological position.
   It only ever adds videos, so a wrong year is fixed by editing the file and applying again.

Subtitles for every episode are mirrored in [`subtitles/`](subtitles/).

Architecture, design decisions and operating playbooks are in the project wiki:
[`.wiki/index.md`](.wiki/index.md).
