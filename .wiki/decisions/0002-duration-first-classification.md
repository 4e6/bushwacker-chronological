---
type: Decision
title: Classify Shorts by duration first, not title
description: A video under ~350 s is a Short regardless of an episode-like title; only longer videos are period episodes or meta.
status: accepted
tags: [classification]
timestamp: 2026-07-27T18:15:00Z
---

# Context

Titles lie about length: a 65 s clip can be titled "Великий западный раскол
(1378–1417)" — a full date range that looks like an episode. Real episodes run
~1.5–2.5 h (5000–8000 s).

# Decision

Decide **Short by duration first**: anything under ~6 min (`duration_s` ≲ 350) is
a Short → `bushwacker_excluded.txt`, regardless of title (incl. hashtag-tagged
clips and the "Истфакт №N" trivia). Only longer videos are a **period episode**
(about one era → playlist, dated to a [`[YEAR]`](/domain/source-files.md)) or
**meta** (Q&A, "Вне формата", broad non-period intro → `excluded.txt`).

# Consequences

- Reliable Shorts detection is what makes the
  [no-human-gate nightly](/architecture/nightly-sync.md) safe — the main residual
  exposure is a period episode with a *wrong year*.
- To cut that exposure, the classifier is fed a **transcript intro**
  (`fetch_transcripts.py`, see [subtitle mirror](/architecture/subtitles.md)): for
  an ambiguous year, prefer explicit title dates, then the intro's described era
  (auto-captions garble exact digits — read the era, not scraped numbers), then
  the description, then historical knowledge. Full procedure:
  [manual sync](/playbooks/manual-sync.md).
