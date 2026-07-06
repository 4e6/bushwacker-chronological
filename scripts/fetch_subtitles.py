#!/usr/bin/env python3
"""
Self-healing Russian-subtitle fetcher for the chronological playlist.

For every video in bushwacker_playlist.txt that does NOT yet have a committed
subtitle (subtitles/<id>.ru.srt + an _index.tsv row), fetch Russian captions
from YouTube with yt-dlp and write a clean .ru.srt, then rebuild
subtitles/_index.tsv in chronological (playlist) order.

Normally the only missing video is the one the nightly sync just added, but the
playlist-vs-subtitles diff is used as the signal (not new_videos.json), so this
also backfills earlier gaps and *retries* anything a previous run couldn't fetch.
Existing _index.tsv rows are reused verbatim — the only diff is the inserted row.

Why srv1 (not the default .vtt/.srt download): YouTube's auto-caption vtt/srt is
~2 MB of "rolling" duplicated lines with word-timing tags. Its native `srv1`
timedtext format is instead one clean `<text start dur>segment</text>` per line
(~500 KB) — YouTube's own segmentation — so we fetch that and do a trivial,
robust XML→SRT convert. No fragile rolling de-duplication that could silently
break when YouTube changes the vtt cadence (it already changed once).

Best-effort by design: YouTube exposes NO Data-API path to download a third
party's captions, so this must use yt-dlp, which CAN be bot-blocked from
datacenter IPs (see CLAUDE.md — that's why detect_new.py avoids yt-dlp). Any
video whose captions can't be fetched — blocked, or none exist (→ needs local
Whisper) — is left for a later run / the local fallback; the script still
exits 0 so it never breaks the sync. Whisper is deliberately NOT run here (it
needs a GPU + a 1.6 GB model); that stays local per CLAUDE.md "Subtitles".

Usage:
  python3 scripts/fetch_subtitles.py            # fetch every missing subtitle
  DRY_RUN=1 python3 scripts/fetch_subtitles.py  # just report what's missing
  ONLY=<id1,id2> python3 scripts/fetch_subtitles.py   # limit to specific ids

Requires yt-dlp on PATH (pip install yt-dlp). Stdlib only otherwise.
"""
import os
import re
import sys
import glob
import html
import tempfile
import subprocess

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST_FILE = os.path.join(PROJ, "bushwacker_playlist.txt")
SUBS_DIR = os.path.join(PROJ, "subtitles")
INDEX_FILE = os.path.join(SUBS_DIR, "_index.tsv")
INDEX_HEADER = ["year", "video_id", "source", "srt_file", "title"]

DRY_RUN = os.environ.get("DRY_RUN") == "1"
ONLY = {x for x in os.environ.get("ONLY", "").split(",") if x}
TIMEOUT = int(os.environ.get("YTDLP_TIMEOUT", "300"))


# ---------------------------------------------------------------- playlist ---
def playlist_entries():
    """[{year:int, id:str, title:str}, ...] in file (chronological) order.

    A block is: `[YEAR] <label>` / `▶ <original title>` / `watch?v=<id>`.
    The _index.tsv `title` column is the ▶ original title, not the label.
    """
    entries = []
    year = None
    title = None
    with open(PLAYLIST_FILE, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\[\s*(-?\d+)\s*\]", line)
            if m:
                year = int(m.group(1))
                title = None
                continue
            m = re.match(r"^\s*▶\s*(.+?)\s*$", line)  # ▶
            if m:
                title = m.group(1)
                continue
            m = re.search(r"watch\?v=([A-Za-z0-9_-]{11})", line)
            if m:
                entries.append({"year": year, "id": m.group(1), "title": title or ""})
                year = None
                title = None
    if not entries:
        sys.exit("error: parsed 0 entries from the playlist file")
    return entries


# ------------------------------------------------------------------- index ---
def read_index():
    """id -> raw row list, preserving existing fields verbatim."""
    rows = {}
    if not os.path.exists(INDEX_FILE):
        return rows
    with open(INDEX_FILE, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.rstrip("\n")
            if i == 0 or not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 5:
                rows[parts[1]] = parts[:5]
    return rows


def write_index(entries, index, fetched):
    """Rebuild _index.tsv in playlist order; reuse existing rows verbatim,
    insert a fresh row for each newly fetched id at its chronological slot."""
    out = [INDEX_HEADER]
    covered = set()
    for e in entries:
        vid = e["id"]
        if vid in fetched:
            out.append([str(e["year"]), vid, fetched[vid], f"{vid}.ru.srt", e["title"]])
            covered.add(vid)
        elif vid in index:
            out.append(index[vid])
            covered.add(vid)
    # Never silently drop an existing row for a video that left the playlist.
    orphans = [v for v in index if v not in covered]
    if orphans:
        print(f"  ! {len(orphans)} index row(s) not in playlist, kept at end: "
              + ", ".join(orphans[:5]))
        for v in orphans:
            out.append(index[v])
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join("\t".join(r) for r in out) + "\n")


# ---------------------------------------------------------- srv1 -> srt ------
def _ms_to_ts(ms):
    h, ms = divmod(int(ms), 3600000)
    mi, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"


def srv1_to_cues(xml_text):
    """Parse YouTube's srv1 timedtext (<text start dur>seg</text>) into
    [(start_ms, end_ms, text), ...]. srv1 double-escapes entities (XML over
    HTML: `&amp;quot;` == `"`), so unescape twice. Segments overlap because
    YouTube shows a 2-line rolling window — clip each end to the next start so
    the SRT is non-overlapping like the rest of the corpus."""
    cues = []
    for m in re.finditer(r'<text\s+start="([\d.]+)"(?:\s+dur="([\d.]+)")?[^>]*>(.*?)</text>',
                         xml_text, re.S):
        start = float(m.group(1))
        dur = float(m.group(2) or 0.0)
        text = re.sub(r"\s+", " ", html.unescape(html.unescape(m.group(3)))).strip()
        if not text:
            continue
        cues.append([int(round(start * 1000)), int(round((start + dur) * 1000)), text])
    for i in range(len(cues) - 1):
        nxt = cues[i + 1][0]
        if cues[i][1] > nxt:
            cues[i][1] = nxt
    return cues


def cues_to_srt(cues):
    blocks = []
    for i, (a, b, t) in enumerate(cues, 1):
        blocks.append(f"{i}\n{_ms_to_ts(a)} --> {_ms_to_ts(b)}\n{t}\n")
    return "\n".join(blocks)


# ---------------------------------------------------------------- fetching ---
def _run_ytdlp(args):
    try:
        return subprocess.run(
            ["yt-dlp", "--no-warnings", "--no-progress", *args],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except FileNotFoundError:
        sys.exit("error: yt-dlp not found on PATH (pip install yt-dlp)")
    except subprocess.TimeoutExpired:
        return None


def _pick(dirpath, prefer):
    """Choose the best .srv1 in dirpath by language suffix preference."""
    found = {}
    for p in glob.glob(os.path.join(dirpath, "*.srv1")):
        m = re.search(r"\.([A-Za-z-]+)\.srv1$", os.path.basename(p))
        if m:
            found[m.group(1)] = p
    for lang in prefer:
        if lang in found:
            return found[lang]
    return next(iter(found.values()), None)


def _blocked(res):
    err = (res.stderr or "") if res else ""
    return bool(re.search(r"confirm .*not a bot|sign in to confirm", err, re.I))


def _fetch_srv1(video_id, sub_dir, prefer, auto):
    flag = "--write-auto-subs" if auto else "--write-subs"
    langs = "ru-orig,ru" if auto else "ru,ru-RU,ru.*"
    res = _run_ytdlp(["--skip-download", flag, "--sub-langs", langs,
                      "--sub-format", "srv1",
                      "-o", os.path.join(sub_dir, "%(id)s.%(ext)s"),
                      f"https://youtu.be/{video_id}"])
    path = _pick(sub_dir, prefer)
    if not path:
        return None, res
    with open(path, encoding="utf-8") as f:
        cues = srv1_to_cues(f.read())
    return (cues if cues else None), res


def fetch(video_id):
    """Return (source, srt_text, n_cues) or None. Manual subs win over auto."""
    with tempfile.TemporaryDirectory() as tmp:
        man_dir = os.path.join(tmp, "man")
        os.makedirs(man_dir)
        cues, _ = _fetch_srv1(video_id, man_dir, ["ru", "ru-RU"], auto=False)
        if cues:
            return "yt-manual", cues_to_srt(cues), len(cues)

        auto_dir = os.path.join(tmp, "auto")
        os.makedirs(auto_dir)
        cues, res = _fetch_srv1(video_id, auto_dir, ["ru-orig", "ru"], auto=True)
        if cues:
            return "yt-auto", cues_to_srt(cues), len(cues)
        if _blocked(res):
            print("    (yt-dlp bot-blocked — likely a datacenter IP; retry later / run local)")
    return None


# ------------------------------------------------------------------- main ----
def main():
    entries = playlist_entries()
    index = read_index()

    def has_sub(vid):
        return vid in index and os.path.exists(os.path.join(SUBS_DIR, f"{vid}.ru.srt"))

    missing = [e for e in entries if not has_sub(e["id"])]
    print(f"playlist: {len(entries)} videos | with subtitle: "
          f"{len(entries) - len(missing)} | missing: {len(missing)}")
    if ONLY:
        missing = [e for e in missing if e["id"] in ONLY]
    for e in missing:
        print(f"  MISSING  [{e['year']:>5}]  {e['id']}  {e['title']}")
    if not missing:
        print("nothing to do — every playlist video has a subtitle")
        return 0
    if DRY_RUN:
        print("dry-run only — unset DRY_RUN to fetch")
        return 0

    fetched = {}
    for e in missing:
        vid = e["id"]
        res = fetch(vid)
        if not res:
            print(f"  ✗ {vid} — no Russian captions on YouTube (or blocked); "
                  f"leave for local Whisper")
            continue
        source, srt, n = res
        with open(os.path.join(SUBS_DIR, f"{vid}.ru.srt"), "w", encoding="utf-8") as f:
            f.write(srt)
        fetched[vid] = source
        print(f"  ✓ {vid}  {source:9}  {n:>4} cues  -> subtitles/{vid}.ru.srt")

    if fetched:
        write_index(entries, index, fetched)
        print(f"updated subtitles/_index.tsv (+{len(fetched)} row(s))")
    unresolved = len(missing) - len(fetched)
    print(f"done — fetched {len(fetched)}/{len(missing)}"
          + (f", {unresolved} still missing (local Whisper)" if unresolved else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
