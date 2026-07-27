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

Fetch order per missing video: a per-run cache (a transcript fetch_transcripts.py
already fetched this run for the classifier — see SUBS_CACHE_DIR) -> yt-dlp manual
subs -> yt-dlp auto-captions (both free) -> the Supadata HTTP API (fallback), so a
new episode is fetched only once per night. yt-dlp is primary because it's free
(YouTube exposes NO Data-API path to a third party's captions), but it CAN be
bot-blocked from datacenter IPs (see CLAUDE.md — that's why detect_new.py avoids
yt-dlp); in GitHub Actions it usually is. Supadata fetches the SAME YouTube
captions over an API that isn't IP-blocked — set SUPADATA_API_KEY (env or a local
.env) to enable it. It is pinned to mode=native: existing captions only, ~1
credit/call. It NEVER uses Supadata's AI transcription (mode=auto/generate — 2
credits per video-MINUTE, so a single 2 h episode = 240 credits, well past the
100-credit/month free tier); videos with no captions anywhere are transcribed for
free by local Whisper instead.

Best-effort by design: any video whose captions can't be fetched — yt-dlp
blocked AND Supadata unset/unavailable, or none exist anywhere (→ needs local
Whisper) — is left for a later run / the local fallback; the script still exits
0 so it never breaks the sync. Whisper is deliberately NOT run here (it needs a
GPU + a 1.6 GB model); that stays local per CLAUDE.md "Subtitles".

Usage:
  python3 scripts/fetch_subtitles.py            # fetch every missing subtitle
  DRY_RUN=1 python3 scripts/fetch_subtitles.py  # just report what's missing
  ONLY=<id1,id2> python3 scripts/fetch_subtitles.py   # limit to specific ids

Requires yt-dlp on PATH for the free primary path (pip install yt-dlp) and, for
the fallback, SUPADATA_API_KEY. Stdlib only otherwise.
"""
import os
import re
import sys
import glob
import html
import json
import time
import tempfile
import subprocess
import urllib.request
import urllib.parse
import urllib.error

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST_FILE = os.path.join(PROJ, "bushwacker_playlist.txt")
SUBS_DIR = os.path.join(PROJ, "subtitles")
INDEX_FILE = os.path.join(SUBS_DIR, "_index.tsv")
INDEX_HEADER = ["year", "video_id", "source", "srt_file", "title"]


def _load_dotenv():
    """Populate os.environ from a local .env (KEY=VALUE per line) for any key not
    already set, so `SUPADATA_API_KEY=…` in .env works for local runs. Real env
    vars (e.g. CI secrets) always win; missing .env is fine (CI has none — it's
    gitignored). Stdlib-only, best-effort."""
    try:
        with open(os.path.join(PROJ, ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_load_dotenv()

DRY_RUN = os.environ.get("DRY_RUN") == "1"
ONLY = {x for x in os.environ.get("ONLY", "").split(",") if x}
TIMEOUT = int(os.environ.get("YTDLP_TIMEOUT", "300"))
# Supadata fallback (mode=native only — see the module docstring / _fetch_supadata).
SUPADATA_API = "https://api.supadata.ai/v1"
SUPADATA_JOB_TIMEOUT = int(os.environ.get("SUPADATA_JOB_TIMEOUT", "180"))
SUPADATA_POLL_INTERVAL = 4
# Per-run transcript cache: fetch_transcripts.py stashes a new episode's SRT here
# (one <id>.json per video) so this mirror reuses that single fetch — one Supadata
# call feeds both the classify-time intro and the committed subtitle. Gitignored.
SUBS_CACHE_DIR = os.environ.get("SUBS_CACHE_DIR") or os.path.join(PROJ, ".subs_cache")


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
_ytdlp_missing = False


def _run_ytdlp(args):
    """Run yt-dlp; None on timeout or if yt-dlp isn't installed. A missing binary
    is noted once (not fatal) so the Supadata fallback can still run."""
    global _ytdlp_missing
    if _ytdlp_missing:
        return None
    try:
        return subprocess.run(
            ["yt-dlp", "--no-warnings", "--no-progress", *args],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except FileNotFoundError:
        _ytdlp_missing = True
        print("    (yt-dlp not on PATH — relying on Supadata if configured)")
        return None
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


# -------------------------------------------------------------- supadata -----
# Fallback for when yt-dlp is bot-blocked from a datacenter IP (the usual case in
# CI): Supadata fetches the SAME YouTube captions over an HTTP API. Pinned to
# mode=native — existing captions only, 1 credit/call. NEVER auto/generate, which
# would run Supadata's own AI transcription at 2 credits per video-MINUTE (a 2 h
# episode = 240 credits, past the 100-credit/month free tier); videos with no
# captions go to free local Whisper instead. Long native transcripts return
# synchronously (200); the async job path (202 -> poll, no extra credits) is
# handled defensively. Stdlib urllib; never raises (best-effort like the rest).
def _supadata_http(path):
    """GET {SUPADATA_API}/{path} with the x-api-key header. Returns (status_code,
    data) — data is parsed JSON (or {'_raw': …}) — or (None, None) with no key or
    on a network error. Non-2xx (incl. 206) is returned, not raised."""
    key = os.environ.get("SUPADATA_API_KEY")
    if not key:
        return None, None
    req = urllib.request.Request(f"{SUPADATA_API}/{path}", headers={"x-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            code, body = r.getcode(), r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read().decode("utf-8", "ignore")
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"    (supadata network error: {e.__class__.__name__})")
        return None, None
    try:
        return code, json.loads(body)
    except ValueError:
        return code, {"_raw": body[:200]}


def _supadata_cues(content):
    """Supadata content array [{text, offset, duration}, …] -> non-overlapping
    [start_ms, end_ms, text] cues (same shape/clipping as srv1_to_cues)."""
    if not isinstance(content, list):
        return None
    cues = []
    for seg in content:
        text = re.sub(r"\s+", " ", (seg.get("text") or "")).strip()
        if not text:
            continue
        off = int(seg.get("offset") or 0)
        cues.append([off, off + int(seg.get("duration") or 0), text])
    for i in range(len(cues) - 1):
        if cues[i][1] > cues[i + 1][0]:
            cues[i][1] = cues[i + 1][0]
    return cues or None


def _supadata_poll(job_id):
    """Poll transcript/{job_id} until completed/failed or SUPADATA_JOB_TIMEOUT.
    Status polls cost no credits. Returns the content array or None."""
    deadline = time.monotonic() + SUPADATA_JOB_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(SUPADATA_POLL_INTERVAL)
        _, data = _supadata_http(f"transcript/{job_id}")
        if not data:
            continue
        status = data.get("status")
        if status == "completed":
            return data.get("content")
        if status == "failed":
            print(f"    (supadata job failed: {str(data.get('error') or '')[:120]})")
            return None
    print("    (supadata job timed out)")
    return None


def _fetch_supadata(video_id):
    """Russian captions via Supadata native mode -> cues, or None. None = not
    configured / no native captions (206) / error -> leave for Whisper."""
    if not os.environ.get("SUPADATA_API_KEY"):
        return None
    q = urllib.parse.urlencode({
        "url": f"https://youtu.be/{video_id}", "lang": "ru", "mode": "native",
    })
    code, data = _supadata_http(f"transcript?{q}")
    if code is None:
        return None
    if code == 200:
        content = (data or {}).get("content")
    elif code == 202 and (data or {}).get("jobId"):
        content = _supadata_poll(data["jobId"])
    elif code == 206:
        print("    (supadata: no native Russian captions — leave for Whisper)")
        return None
    else:
        msg = (data or {}).get("error") or (data or {}).get("message") or (data or {}).get("_raw") or ""
        print(f"    (supadata error {code}: {str(msg)[:120]})")
        return None
    return _supadata_cues(content)


# ---------------------------------------------------------------- fetching ---
def _read_cache(video_id):
    """Reuse a transcript fetch_transcripts.py already fetched this run (one fetch
    feeds both the classify intro and this mirror). Returns (source, srt, n_cues)
    or None. The cache carries the real provenance so _index.tsv stays honest."""
    path = os.path.join(SUBS_CACHE_DIR, f"{video_id}.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (FileNotFoundError, ValueError):
        return None
    srt = d.get("srt")
    if not srt:
        return None
    print("    (reusing the transcript fetched for classification — no re-fetch)")
    return d.get("source") or "supadata", srt, int(d.get("n") or srt.count(" --> "))


def fetch_cues(video_id):
    """Fetch Russian captions → (source, cues) or None, ALWAYS over the network.
    Order: yt-dlp manual → yt-dlp auto (both free) → Supadata native (1 credit; the
    CI fallback for a bot-blocked yt-dlp). None → no captions anywhere → Whisper.
    The cache-first wrapper is fetch(); this is the raw fetch the transcript step
    uses (and the source of what gets cached)."""
    res = None
    with tempfile.TemporaryDirectory() as tmp:
        man_dir = os.path.join(tmp, "man")
        os.makedirs(man_dir)
        cues, _ = _fetch_srv1(video_id, man_dir, ["ru", "ru-RU"], auto=False)
        if cues:
            return "yt-manual", cues

        auto_dir = os.path.join(tmp, "auto")
        os.makedirs(auto_dir)
        cues, res = _fetch_srv1(video_id, auto_dir, ["ru-orig", "ru"], auto=True)
        if cues:
            return "yt-auto", cues
    if _blocked(res):
        print("    (yt-dlp bot-blocked — likely a datacenter IP; trying Supadata)")
    cues = _fetch_supadata(video_id)
    if cues:
        return "supadata", cues
    return None


def fetch(video_id):
    """Return (source, srt_text, n_cues) or None. Cache-first (reuse the classify
    step's fetch), else a fresh yt-dlp→Supadata fetch via fetch_cues()."""
    cached = _read_cache(video_id)
    if cached:
        return cached
    res = fetch_cues(video_id)
    if not res:
        return None
    source, cues = res
    return source, cues_to_srt(cues), len(cues)


# ------------------------------------------------------------------- main ----
def main():
    entries = playlist_entries()
    index = read_index()

    def has_sub(vid):
        return vid in index and os.path.exists(os.path.join(SUBS_DIR, f"{vid}.ru.srt"))

    missing = [e for e in entries if not has_sub(e["id"])]
    print(f"playlist: {len(entries)} videos | with subtitle: "
          f"{len(entries) - len(missing)} | missing: {len(missing)}")
    gh = os.environ.get("GITHUB_OUTPUT")   # let the workflow gate on the count
    if gh:
        with open(gh, "a") as f:
            f.write(f"missing={len(missing)}\n")
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
