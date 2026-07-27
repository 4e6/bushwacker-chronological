#!/usr/bin/env python3
"""Enrich new_videos.json with a transcript intro so the CI classifier can date
each new PERIOD episode from the video's own words — a wrong start year is the
automated loop's #1 error mode (CLAUDE.md "Operating it"). These episodes state
the era they cover in the first minutes, so the opening ~15-20 min of captions is
usually enough to pin the [YEAR] when the title is vague.

For each new upload that could be a full episode (`duration_s` >= MIN_EPISODE_S;
Shorts need no year and are skipped, which also avoids spending a Supadata credit
on them), it fetches the Russian captions ONCE via fetch_subtitles.fetch_cues()
(yt-dlp → Supadata), then:
  • adds `transcript_intro` (the first INTRO_MINUTES of caption text) to that
    video's entry in new_videos.json — the classifier reads it as *untrusted*
    context (see classify_prompt.md); and
  • caches the full SRT under SUBS_CACHE_DIR (<id>.json) so the later
    subtitles-mirror step (fetch_subtitles.py) reuses this same fetch — one
    Supadata call feeds both classification and the committed subtitle.

Runs BEFORE classify (the classifier itself has no network, by design). No
timestamps/whole transcript are handed to the LLM — auto-captions mangle exact
numbers, so we give it the prose and let it reason about the period rather than
scraping digits. Best-effort: any fetch failure just leaves `transcript_intro`
absent and the classifier falls back to title+description, exactly as before. It
never fails the job (always exits 0), needs no YouTube token, and runs no LLM.

Usage:  python3 scripts/fetch_transcripts.py
Env: OUT_JSON (new_videos.json path, shared with detect_new.py), SUPADATA_API_KEY,
     SUBS_CACHE_DIR, INTRO_MINUTES (default 20), MIN_EPISODE_S (default 350),
     INTRO_CHAR_CAP (default 40000, a safety bound only).
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_subtitles as fs  # noqa: E402  (reuse the fetch + SRT primitives)

# Same env + default as detect_new.py (the producer), so detect → this step chain
# by default locally too. CI sets OUT_JSON on both, so detect, this step, and the
# classifier all share $GITHUB_WORKSPACE/new_videos.json.
NEW_JSON = os.environ.get("OUT_JSON") or "/tmp/new_videos.json"
INTRO_MINUTES = int(os.environ.get("INTRO_MINUTES", "20"))
MIN_EPISODE_S = int(os.environ.get("MIN_EPISODE_S", "350"))
INTRO_CHAR_CAP = int(os.environ.get("INTRO_CHAR_CAP", "40000"))


def intro_from_cues(cues):
    """Join the text of every cue that STARTS within the first INTRO_MINUTES.
    Time-based (not a char count) so it's literally 'the first ~N minutes'; the
    char cap is only a guard against a pathologically dense/garbled transcript."""
    cutoff_ms = INTRO_MINUTES * 60 * 1000
    text = " ".join(t for (start, _end, t) in cues if start < cutoff_ms)
    return text[:INTRO_CHAR_CAP].strip()


def main():
    try:
        with open(NEW_JSON, encoding="utf-8") as f:
            videos = json.load(f)
    except FileNotFoundError:
        print(f"no {NEW_JSON} — nothing to do")
        return 0
    if not videos:
        print("no new videos — nothing to do")
        return 0

    os.makedirs(fs.SUBS_CACHE_DIR, exist_ok=True)
    done = 0
    for v in videos:
        vid = v.get("id")
        if not vid:
            continue
        dur = v.get("duration_s")
        if dur is not None and dur < MIN_EPISODE_S:
            print(f"  skip {vid} — {dur}s < {MIN_EPISODE_S}s (Short; no period year needed)")
            continue

        # Best-effort per video: one bad fetch must not drop the others or skip the
        # final write (which would desync new_videos.json from an already-cached SRT).
        try:
            res = fs.fetch_cues(vid)
            if not res:
                print(f"  ✗ {vid} — no transcript (blocked / none / not ready yet); "
                      f"classifier will use title + description")
                continue
            source, cues = res
            v["transcript_intro"] = intro_from_cues(cues)
            # Stash the full SRT (+ provenance) for the mirror step to reuse this run.
            with open(os.path.join(fs.SUBS_CACHE_DIR, f"{vid}.json"), "w", encoding="utf-8") as cf:
                json.dump({"source": source, "n": len(cues), "srt": fs.cues_to_srt(cues)},
                          cf, ensure_ascii=False)
            done += 1
            print(f"  ✓ {vid}  {source:9}  intro {len(v['transcript_intro'])} chars "
                  f"(first ~{INTRO_MINUTES} min of {len(cues)} cues) + cached full SRT")
        except Exception as e:  # best-effort — never abort the sync over one video
            print(f"  ! {vid} — transcript step error ({e.__class__.__name__}: {e}); skipping")

    # Atomic write so the classifier never reads a half-written new_videos.json.
    tmp = NEW_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
    os.replace(tmp, NEW_JSON)
    print(f"done — added transcript_intro to {done}/{len(videos)} new video(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
