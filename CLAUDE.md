# Bushwacker History — chronological playlist (sync guide)

This project maintains a **curated YouTube playlist** that mirrors the channel
**@Bushwackerhistory**, with videos ordered by the **historical period each video
is about** (ancient → modern), not by upload date.

- YouTube playlist: **PLVw98VIsFGF8** — https://www.youtube.com/playlist?list=PLVw98VIsFGF8
  (owned by this Google account; currently **Public**).
- Channel: https://www.youtube.com/@Bushwackerhistory (Russian-language history channel).
- Baseline (2026-06-27): channel had **136** videos → **128** period videos in the
  playlist + **8** excluded (7 shorts + 1 meta).

Your job in a sync session: when the channel posts new videos, add the period
ones to the playlist **in the correct chronological slot** and keep the local files
below in sync.

## Files = source of truth

- **`bushwacker_playlist.txt`** — human-readable mirror of the playlist: only the
  included (period) videos, sorted chronologically. Each entry is 3 lines:
  ```
  [ 1096]  Крестовые походы (с 1096)
          ▶ Крестовые походы
          https://www.youtube.com/watch?v=hq9QEJjYWuY
  ```
  The `watch?v=<ID>` lines are the authoritative record of playlist membership.
- **`bushwacker_excluded.txt`** — channel videos deliberately **NOT** in the
  playlist (shorts + meta), one per line: `[SHORT|META]  <video_id>  <title>  — reason`.
  This exists so they aren't re-detected as "new" every sync.

The video IDs in these two files together = every channel video already classified.

- **`subtitles/`** — a full Russian-caption mirror (one `.ru.srt` per playlist video)
  + `_index.tsv`. A parallel asset, **not** part of playlist membership — see
  **Subtitles** below.

## Period sort key

`[YEAR]` = the **start year of the historical period** the video covers.
Negative = BCE, positive = CE, smaller = older; the file is sorted ascending.
For broad-span topics, use the start of the polity/era (e.g. Republic of Venice → 697;
"Хетты" → -1650; modern "Ликбез по Сирии" → 2011). Keep period labels in Russian,
matching the existing style.

## Sync workflow

> **This now runs automatically** in GitHub Actions — normally you just review & merge a
> PR (see **Automation (GitHub Actions)** below). The manual steps here are the rules the
> bot follows, and the fallback for special cases.

### 1. Find new videos (read-only, no login needed)

```bash
cd <this project dir>
yt-dlp --flat-playlist --no-warnings --print "%(id)s" \
  "https://www.youtube.com/@Bushwackerhistory/videos" | sort > /tmp/chan_ids.txt
{ grep -oE 'watch\?v=[A-Za-z0-9_-]{11}' bushwacker_playlist.txt | sed 's#watch?v=##'
  awk '/^\[(SHORT|META)\]/{print $2}' bushwacker_excluded.txt ; } | sort -u > /tmp/known_ids.txt
comm -23 /tmp/chan_ids.txt /tmp/known_ids.txt    # => NEW, unclassified video IDs
```

Use the **ID set-difference** as the signal (stable). Don't rely on "last video id"
or upload dates — titles/dates can change and videos can be (un)listed out of order.
For each new ID get its title/duration with:
`yt-dlp --skip-download --print "%(duration)s s | %(upload_date)s | %(title)s" "https://youtu.be/<ID>"`

### 2. Classify & date each new video

- **Short — decide by DURATION FIRST, not title.** Anything under ~6 min (≲350 s) is a
  SHORT regardless of how episode-like the title looks — incl. topical clips tagged like
  `#англия #history` and even titles with date ranges (a 65 s "Великий западный раскол
  (1378–1417)" is a Short, not an episode). The "Истфакт №N" / "Fact #N" trivia are one
  subset → **excluded (SHORT)**.
- **Meta / Q&A / broad non-period intro** — e.g. "Вне формата", "...ответы на вопросы",
  a series intro that isn't about one period → **excluded (META)**.
- **Otherwise = a period episode** (full episodes run ~1.5–2.5 h, 5000–8000 s):
  infer its **start year** + a short Russian period label.
  - Most titles state the era or give explicit dates: `(1455 - 1486)`, `XII - XIV вв.`,
    `до н.э.` — use them directly. Otherwise use historical knowledge of the topic.
  - If the period is genuinely ambiguous, read the transcript intro + date mentions:
    ```bash
    yt-dlp --write-auto-subs --sub-langs "ru.*,ru" --sub-format vtt --skip-download \
      -o "sub_%(id)s.%(ext)s" "https://youtu.be/<ID>"
    ```
    Strip VTT to text and look at the first ~300 words + century/"до н.э."/year tokens.
    Some videos have **no captions** — then transcribe locally with Whisper (see
    **Subtitles** below) or, failing that, infer from title + series context.
    **CI automates this**: `scripts/fetch_transcripts.py` puts the first ~15–20 min of
    the episode's captions into `new_videos.json` as `transcript_intro` *before* the
    classifier runs, so the bot dates ambiguous episodes the same way (auto-captions
    garble exact numbers, so it reads the era described, not scraped digits).

### 3. Apply the change

**Period episode:**
1. Insert a 3-line block into `bushwacker_playlist.txt` at the correct `[YEAR]` slot
   (between the two neighbours by year).
2. Add it to the YouTube playlist and move it into that slot (see API below).
3. Bump the header's `videos:` count and `last synced:` date.
4. Fetch its Russian subtitle into `subtitles/` + an `_index.tsv` row —
   `python3 scripts/fetch_subtitles.py` (self-healing; see **Subtitles** below). CI now
   does this automatically; files under `subtitles/` are tracked (no `git add -f` needed).

**Short / meta:** append a `[SHORT|META] <id> <title> — reason` line to
`bushwacker_excluded.txt` and bump its `last synced:` date. (No playlist change.)

### 4. Verify

Re-enumerate the playlist via the **authenticated** API (below) and confirm count,
order, and no duplicates. **Do not trust anonymous yt-dlp or the web UI for the full
list** — both cap at the **first 100** items and this playlist has >100. The
authenticated `enumerate()` returns all of them.

## Automation (GitHub Actions)

The sync above runs **fully hands-off** — there is no human step. `nightly-sync.yml` does
the whole loop in two jobs (`sync`, then `apply`); the manual steps above are the rules it
follows + the fallback.

**`.github/workflows/nightly-sync.yml`** — cron 04:00 UTC + manual `workflow_dispatch`:
1. **`scripts/detect_new.py`** reads the channel **RSS feed**
   (`channel_id=UCGzfpg1YiBIlgcODQI4lDvQ`), diffs against the IDs already in the two text
   files, and enriches each new id with **duration + description via the Data API** (RSS +
   API, *not* yt-dlp — datacenter IPs get bot-blocked). Skips the rest if nothing is new.
2. **`scripts/fetch_transcripts.py`** (deterministic, *before* the LLM) — for each new
   *episode* (Shorts skipped by `duration_s`) fetches the Russian captions via
   yt-dlp→Supadata and adds the **first ~15–20 min** to `new_videos.json` as
   `transcript_intro`, so the classifier can pin a period's **start year** from the
   video's own words — a wrong year is the loop's #1 error mode. Best-effort
   (`continue-on-error`): no transcript → the field is simply absent and classification
   falls back to title+description. The full SRT is cached (`.subs_cache/`) so step 4
   reuses this one fetch (a single Supadata credit feeds both classification and the mirror).
3. **`claude -p`** with **`scripts/classify_prompt.md`** classifies each new video
   (SHORT / META / period — **duration-first**), using `transcript_intro` when present to
   pin the start year, and edits the text files. The LLM only edits files: it never
   receives the YouTube token and has no network/Bash, and treats every title,
   description, and transcript as **untrusted data**.
4. **`scripts/fetch_subtitles.py`** runs **every night** — driven by "is any playlist
   video missing a `.ru.srt`?", *not* by has_new — and for each missing one fetches
   Russian captions (manual subs, else auto-captions) as clean **srv1** timedtext,
   converts to `.ru.srt`, and updates `subtitles/_index.tsv`. It **reuses the transcript
   step 2 cached** for the new episode when present (no re-fetch); otherwise it tries
   **yt-dlp first** (free) and, when that's bot-blocked, the **Supadata API** (`source =
   supadata`) — the *same* YouTube captions over an HTTP API that datacenter IPs can reach.
   **Best-effort** (`continue-on-error`): if both fail (or a fresh upload's auto-captions
   aren't ready yet) the gap is just **retried on later runs until it lands**, even on a
   night with no new video. A cheap `DRY_RUN` check gates whether the yt-dlp binary is
   downloaded at all. No LLM, no YouTube token; needs `SUPADATA_API_KEY` for the fallback.
5. **`peter-evans/create-pull-request`** opens a PR on branch `sync/auto` whenever
   anything tracked changed — new-video classification *and/or* a backfilled subtitle (a
   subtitles-only night gets its own `backfill missing subtitles` PR) — then a step
   **auto-merges it** (`gh pr merge`, GITHUB_TOKEN). The merged PRs are the change log.

Job **`apply`** runs only when `bushwacker_playlist.txt` changed (a period episode was
added): **`scripts/yt_playlist_sync.py`** (`APPLY=1`) inserts the new video at its
chronological `position` via the Data API. Deterministic, no LLM. Gated by the
**`youtube-prod`** environment (deployment branch = `main`). Shorts/META touch
`excluded.txt` only → `apply` is skipped, nothing hits YouTube.

> Why `apply` runs *inside* nightly-sync (not via a push trigger): a merge done with the
> built-in `GITHUB_TOKEN` **does not trigger other workflows**, so it can't rely on a
> `push` event — it runs inline as its own gated job.

**`.github/workflows/playlist-apply.yml`** is now a **manual / safety-net tool**: run it
from the Actions tab (`dry-run` = read-only diff, `apply` = write), or it fires on a
**human** push to `main` that changes `bushwacker_playlist.txt`. The bot's GITHUB_TOKEN
merges don't trigger it → no double-apply.

### Secrets & config
- Repo secrets: `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`), `YT_CLIENT_ID`,
  `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, and `SUPADATA_API_KEY`. The same `YT_*` OAuth
  token does both the read (durations) and the write (insert); re-mint it with
  `scripts/mint_youtube_token.py` if revoked. The Google OAuth consent screen must stay
  **"In production"** or the refresh token expires after 7 days. `SUPADATA_API_KEY`
  (https://supadata.ai) is the subtitle fallback — used **only** when yt-dlp is bot-blocked;
  the script pins it to `mode=native` (~1 credit/fetch), so ≤1 new video/month stays inside
  the free 100-credit/month tier. Locally it's read from `.env`; in CI it **must** be a repo
  secret (add via `gh secret set SUPADATA_API_KEY`). If unset, the fallback is simply skipped.
- `youtube-prod` environment: no secrets of its own (uses the repo secrets), **no reviewer**
  (auto), deployment branch locked to `main`.
- Repo settings: default workflow permissions **read-only**, "Allow Actions to create
  PRs" on, all actions pinned to commit SHAs.
- **Do not enable branch protection that requires review** on `main` — it blocks the bot's
  own auto-merge and silently breaks the loop. `main` is intentionally left unprotected.

### Operating it
- **Normal:** nothing to do. New video → nightly PR → auto-merged → (if a period episode)
  YouTube updated within ~1 min. Skim the merged-PR list for the audit trail.
- **No human gate:** a misclassification goes live. Recoverable — `yt_playlist_sync.py`
  **never deletes** (worst case = a misplaced entry, fixed by a follow-up edit + re-apply);
  duration-first makes Shorts reliable. Main exposure: a period episode with a wrong year.
- **Manual:** Actions → `nightly-sync` → Run; or `playlist-apply` → Run (`dry-run`/`apply`).
- **Watch the first real insert** (first period episode) in the Actions log — a live
  `playlistItems.insert` is the one step not yet battle-tested.
- **Subtitles:** auto-fetched (best-effort) **every night** for any playlist video missing
  one — **yt-dlp first, then the Supadata API** when yt-dlp is bot-blocked — retried until
  it lands, so a blocked or not-yet-ready fetch self-heals on a later run (a subtitles-only
  backfill opens its own auto-merged PR). See **Subtitles**. Only the Whisper fallback
  (videos with *no* YouTube captions at all) runs locally.
- **Optional safety valve:** gate the auto-merge so Shorts/META auto-merge but period-episode
  PRs wait for a human glance (semi-auto). Not currently enabled.

## Subtitles

A full Russian-caption mirror of the playlist lives in **`subtitles/`** (committed):

- **`subtitles/<video_id>.ru.srt`** — one SRT per playlist video (open format, any
  player loads it). **130/130** covered as of 2026-07-27.
- **`subtitles/_index.tsv`** — `year, video_id, source, srt_file, title` in playlist
  order; the record of where each subtitle came from.

`source` ∈ `yt-auto` (YouTube auto-captions via yt-dlp — **114**), `yt-manual` (uploaded
subs — **1**), `supadata` (YouTube captions via the Supadata API, the fallback when yt-dlp
is bot-blocked — **0** so far), `whisper` (locally transcribed because YouTube had none —
**15**).

### Generate a subtitle for a new video — YouTube-first, Whisper fallback

**`python3 scripts/fetch_subtitles.py`** does the YouTube half automatically (and is what
CI runs): for every playlist video missing a `subtitles/<id>.ru.srt` it tries manual subs
(`yt-manual`) then auto-captions (`yt-auto`), fetching YouTube's clean **srv1** timedtext
(`--sub-format srv1` — one `<text start dur>segment</text>` per line, ~500 KB, *not* the
2 MB "rolling" `.vtt`), converts it to SRT (unescape entities twice — srv1 is XML-over-HTML
double-escaped — and clip overlapping cues to the next start), writes the file, and inserts
the `_index.tsv` row in chronological position. **If yt-dlp is bot-blocked** (the usual case
from CI / datacenter IPs), it falls back to the **Supadata API** (`GET /v1/transcript?url=…
&lang=ru&mode=native`, `x-api-key` header) for the same YouTube captions and records
`source = supadata`; Supadata returns the segments as `{text, offset(ms), duration(ms)}`,
which map onto the same clip-to-next-start cue pipeline. Supadata is pinned to `mode=native`
— existing captions only, ~1 credit/call — and **never** its AI-transcription modes
(`auto`/`generate`, 2 credits per video-*minute* → a 2 h episode = 240 credits); videos with
no captions anywhere fall through to free local Whisper instead, so ≤1 new video/month stays
inside the free 100-credit tier. Set `SUPADATA_API_KEY` (env or `.env`) to enable it.
For a **new** episode the nightly already fetched its captions at classify time
(`scripts/fetch_transcripts.py`, for the period-dating intro) and cached them in
`.subs_cache/<id>.json`; this script **reuses that cache** instead of re-fetching, so a new
upload costs a single Supadata call total. Re-runnable and self-healing — it only touches
videos that lack a subtitle. `DRY_RUN=1` previews; `ONLY=<id>` limits to one video.

**No YouTube captions → Whisper (local only):** the script can't do this — grab audio
(`yt-dlp -f bestaudio`) and transcribe with **mlx-whisper**, model
`mlx-community/whisper-large-v3-turbo` (~35× realtime on this Mac; `pip install mlx-whisper`
in a venv, model auto-downloads ~1.6 GB). Save the SRT as `subtitles/<id>.ru.srt`, watch
for Whisper's trailing-silence hallucination loops at the end, and add the `_index.tsv`
row with `source = whisper`.

### Subtitle gotchas

- **`.srt` is gitignored globally** (`*.srt`) **except `subtitles/*.srt`** — a
  `!subtitles/*.srt` negation in `.gitignore` un-ignores the mirror, so new subtitle files
  are tracked with a plain `git add` (no more `git add -f`). Scratch `.srt` elsewhere stays
  ignored.
- **Bulk re-fetching trips bot-detection** — YouTube's "confirm you're not a bot" after
  ~100 back-to-back requests (rate-based, not per-video). Fine for one new video; for a
  bulk pass, space requests (`--sleep-requests 1.5`, a few seconds between videos) and,
  if still blocked, `--cookies-from-browser chrome` (the browser here is **Google
  Chrome**). Per the standing preference, default to cookieless on public data and
  **ask before extracting browser cookies**. (The Supadata fallback isn't IP-blocked, but
  it's **not** for bulk re-fetch — every call spends a credit, so keep it to the ≤1
  missing video/night the nightly actually needs.)

## YouTube playlist API (mutations need the logged-in browser)

Playlist reads/writes use YouTube's internal InnerTube API from the user's
**logged-in** session via the `claude-in-chrome` tools: open
`https://www.youtube.com` (signed in), then run JS with `javascript_tool`.
Auth is a `SAPISIDHASH` computed in-page from the `SAPISID` cookie — never print
or exfiltrate it. **Verified working 2026-06-27.**

> Preference: the user **declined** `yt-dlp --cookies-from-browser`. Keep reads
> cookieless (plain yt-dlp on public data) and do writes through the in-browser
> session. Ask before any browser-cookie extraction. Browser is **Google Chrome**.

Paste this helper in the page context on youtube.com:

```js
const pid = 'PLVw98VIsFGF8';
const API_KEY = ytcfg.get('INNERTUBE_API_KEY'), CTX = ytcfg.get('INNERTUBE_CONTEXT'), ORIGIN = 'https://www.youtube.com';
const sh = async () => { const m = document.cookie.match(/(?:^|;\s*)SAPISID=([^;]+)/) || document.cookie.match(/(?:^|;\s*)__Secure-3PAPISID=([^;]+)/); const S = decodeURIComponent(m[1]); const ts = Math.floor(Date.now()/1000); const b = await crypto.subtle.digest('SHA-1', new TextEncoder().encode(`${ts} ${S} ${ORIGIN}`)); return `SAPISIDHASH ${ts}_${[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')}`; };
const api = async (p, b) => { const a = await sh(); const r = await fetch(`${ORIGIN}/youtubei/v1/${p}?key=${API_KEY}&prettyPrint=false`, { method:'POST', credentials:'include', headers:{'Content-Type':'application/json','Authorization':a,'X-Origin':ORIGIN,'X-Goog-AuthUser':'0'}, body: JSON.stringify(b) }); const t = await r.text(); try { return JSON.parse(t); } catch(e) { return { _raw: t.slice(0,300) }; } };
// full enumeration (paginates past 100; returns playlist order WITH setVideoIds)
const deepTok = (n) => { let t=null; (function w(o){ if(t)return; if(Array.isArray(o)){o.forEach(w);} else if(o&&typeof o==='object'){ if(o.continuationCommand&&o.continuationCommand.token)t=o.continuationCommand.token; for(const k in o)w(o[k]); } })(n); return t; };
const coll = (j) => { let arr=null; (function w(o){ if(arr)return; if(Array.isArray(o)){ if(o.some(e=>e&&e.playlistVideoRenderer)){arr=o;return;} o.forEach(w);} else if(o&&typeof o==='object'){ for(const k in o)w(o[k]); } })(j); const it=[]; let tk=null; if(arr)for(const e of arr){ if(e.playlistVideoRenderer)it.push({v:e.playlistVideoRenderer.videoId, s:e.playlistVideoRenderer.setVideoId}); else if(e.continuationItemRenderer)tk=deepTok(e.continuationItemRenderer); } if(!tk){ let n=null; (function w(o){ if(n)return; if(Array.isArray(o)){o.forEach(w);} else if(o&&typeof o==='object'){ if(o.continuationItemRenderer){n=o.continuationItemRenderer;return;} for(const k in o)w(o[k]); } })(j); if(n)tk=deepTok(n);} return {it,tk}; };
const enumerate = async () => { let all=[]; let r=await api('browse',{context:CTX,browseId:'VL'+pid}); let {it,tk}=coll(r); all.push(...it); let p=1; const seen=new Set(); if(tk)seen.add(tk); while(tk&&p<20){ r=await api('browse',{context:CTX,continuation:tk}); const c=coll(r); p++; if(!c.it.length)break; all.push(...c.it); if(!c.tk||seen.has(c.tk))break; tk=c.tk; seen.add(tk);} return all; };
// const all = await enumerate();  // -> [{v: videoId, s: setVideoId}, ...] in playlist order
```

Operations (each returns `{status:'STATUS_SUCCEEDED', ...}` on success):

```js
// ADD (appends to end). The new entry's setVideoId is in the response's playlistEditResults.
await api('browse/edit_playlist', {context:CTX, playlistId:pid, actions:[{action:'ACTION_ADD_VIDEO', addedVideoId:'<VIDEO_ID>'}]});

// MOVE an entry to right AFTER another existing entry (this is how you place it chronologically).
await api('browse/edit_playlist', {context:CTX, playlistId:pid, actions:[{action:'ACTION_MOVE_VIDEO_AFTER', setVideoId:'<MOVED_setVideoId>', movedSetVideoIdPredecessor:'<PREDECESSOR_setVideoId>'}]});
// To place at the very top (unlikely for this channel): ACTION_MOVE_VIDEO_BEFORE with movedSetVideoIdSuccessor:'<current first setVideoId>'.

// REMOVE a specific entry (e.g. a mistaken duplicate — target the exact setVideoId).
await api('browse/edit_playlist', {context:CTX, playlistId:pid, actions:[{action:'ACTION_REMOVE_VIDEO', setVideoId:'<setVideoId>'}]});

// CREATE a fresh playlist (only if rebuilding from scratch; accepts >100 videoIds, in order):
await api('playlist/create', {context:CTX, title:'...', privacyStatus:'PRIVATE', videoIds:[/* ids in order */]});
```

### Insert-a-new-video recipe

1. `const all = await enumerate();` — current order + setVideoIds.
2. ADD the new video. Re-`enumerate()`, find the new entry by its videoId → `newS`.
3. Predecessor = the **last** entry whose period year ≤ the new video's year (walk your
   local sorted list / `bushwacker_playlist.txt`). Get that entry's setVideoId from `all`.
4. MOVE: `ACTION_MOVE_VIDEO_AFTER {setVideoId:newS, movedSetVideoIdPredecessor:<pred.s>}`.
5. Re-`enumerate()` and confirm the order matches `bushwacker_playlist.txt`.

## Gotchas

- **Anonymous reads cap at 100** (yt-dlp `--flat-playlist`, public web UI). The playlist
  has >100, so always verify with the authenticated `enumerate()`. This caused real
  confusion before — don't repeat it.
- `playlist/create` is **not** capped at 100. `edit_playlist` add/remove/move act
  per-entry by `setVideoId`; the same videoId can appear multiple times, each with its
  own `setVideoId`.
- Regenerating the two text files from scratch was done with `scratchpad/build_playlist.py`
  (a curated `id → (year, label)` map); for routine syncs just edit the text files directly.
