# Bushwacker History — chronological playlist

This project maintains a **curated YouTube playlist** that mirrors the channel
**Bushwackerhistory**, with videos ordered by the **historical period each video
is about** (ancient → modern), not by upload date. A nightly GitHub Actions loop
does the whole sync hands-off; normally you just review the auto-merged PRs.

- Playlist: **PLVw98VIsFGF8** — https://www.youtube.com/playlist?list=PLVw98VIsFGF8 (Public).
- Channel: https://www.youtube.com/@Bushwackerhistory (Russian-language history).

## Project knowledge → the wiki

**All durable knowledge — architecture, decisions, data formats, integrations, and
operational playbooks — lives in the OKF wiki at [.wiki/](.wiki/). Start at
[.wiki/index.md](.wiki/index.md).** Quick map:

- **What runs & why** — [.wiki/architecture/](.wiki/architecture/) (nightly-sync,
  subtitles) and [.wiki/decisions/](.wiki/decisions/).
- **Data & the `[YEAR]` sort key** — [.wiki/domain/source-files.md](.wiki/domain/source-files.md).
- **Third parties** — [.wiki/integrations/](.wiki/integrations/) (YouTube InnerTube,
  Data API, Supadata).
- **How to sync / fetch subtitles / operate the nightly** — [.wiki/playbooks/](.wiki/playbooks/).
- **Working norms** — [.wiki/conventions/](.wiki/conventions/).

Keep it current: a change that alters a decision, an invariant, a convention, a
data model, or an integration boundary updates the relevant `.wiki/` page **in the
same commit**.

## Source of truth

`bushwacker_playlist.txt` + `bushwacker_excluded.txt` are authoritative; the live
YouTube playlist is derived from them. Formats and the sort key:
[.wiki/domain/source-files.md](.wiki/domain/source-files.md).
