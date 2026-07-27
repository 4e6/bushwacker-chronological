# Decision

* [Apply runs inline in nightly-sync, and main stays unprotected](0003-apply-inline-and-unprotected-main.md) - A GITHUB_TOKEN merge doesn't trigger other workflows, so the YouTube write is a gated inline job; branch protection would break the auto-merge.
* [Classify Shorts by duration first, not title](0002-duration-first-classification.md) - A video under ~350 s is a Short regardless of an episode-like title; only longer videos are period episodes or meta.
* [The text files are the source of truth, not the live playlist](0001-files-as-source-of-truth.md) - bushwacker_playlist.txt + bushwacker_excluded.txt are authoritative; the YouTube playlist is derived from them.
