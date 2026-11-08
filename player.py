from core import *
import core as _core
globals().update({k: v for k, v in vars(_core).items() if not k.startswith("__")})


# ---------- youtube ----------
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
_tl = threading.local()


def http():
    """One requests.Session per thread: the connection stays open, so only the first call pays the TLS handshake."""
    s = getattr(_tl, "s", None)
    if s is None:
        s = _tl.s = requests.Session()
    return s


_aio = None


async def aio():
    """One shared aiohttp session (connection reuse) for all song downloads."""
    global _aio
    if _aio is None or _aio.closed:
        _aio = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=20, ttl_dns_cache=300))
    return _aio


AUDIO_FMT = "bestaudio/best"
VIDEO_FMT = "best[height<=720][ext=mp4]/best[height<=720]/best"


def ydl_opts(video=False):
    o = {"quiet": True, "noplaylist": True, "format": VIDEO_FMT if video else AUDIO_FMT}
    if os.path.exists("cookies.txt"):
        o["cookiefile"] = "cookies.txt"
    return o


def fmt(sec, ref=None):
    """mm:ss for songs under 1 hour, hh:mm:ss for 1 hour or more (ref = song length that decides the style)."""
    sec = int(sec or 0)
    ref = sec if ref is None else int(ref or 0)
    if ref >= 3600:
        return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"
    return f"{sec // 60:02d}:{sec % 60:02d}"


def iso_to_sec(d):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    h, mi, se = (int(x or 0) for x in m.groups()) if m else (0, 0, 0)
    return h * 3600 + mi * 60 + se


def yt_api_lookup(query):
    if "youtu" in query:
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", query)
        vid = m.group(1) if m else None
    else:
        r = http().get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video", "maxResults": 1, "key": YT_API_KEY},
            timeout=15)
        r.raise_for_status()
        items = r.json().get("items", [])
        vid = items[0]["id"]["videoId"] if items else None
    if not vid:
        raise ValueError("No results")
    r = http().get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "snippet,contentDetails", "id": vid, "key": YT_API_KEY}, timeout=15)
    r.raise_for_status()
    v = r.json()["items"][0]
    th = v["snippet"]["thumbnails"]
    thumb = (th.get("maxres") or th.get("high") or th.get("default"))["url"]
    return {"title": v["snippet"]["title"], "duration": iso_to_sec(v["contentDetails"]["duration"]),
            "artist": v["snippet"].get("channelTitle", ""), "thumb": thumb, "link": f"https://www.youtube.com/watch?v={vid}"}


_search_cache: dict = {}      # normalized query -> (time, track meta)   (same song asked again = instant)
SEARCH_TTL = 3600


def search(query):
    """Returns track metadata only. Stream URL is resolved at play time (URLs expire)."""
    key = query.strip().lower()
    hit = _search_cache.get(key)
    if hit and time.time() - hit[0] < SEARCH_TTL:
        return dict(hit[1])
    # Runs in an executor thread: no yt-dlp (it triggers YouTube's bot check on Railway).
    # innertube is ONE request; the YouTube Data API needs two, so it is only the fallback.
    try:
        meta = innertube_lookup(query)
    except Exception:
        if not YT_API_KEY:
            raise
        meta = yt_api_lookup(query)
    if len(_search_cache) > 500:
        _search_cache.clear()
    _search_cache[key] = (time.time(), meta)
    return dict(meta)


def innertube_list(query, limit=10):
    """Videos matching `query` (YouTube search, videos only) as track dicts, best match first."""
    r = http().post(
        "https://www.youtube.com/youtubei/v1/search?prettyPrint=false",
        json={"context": {"client": {"clientName": "WEB", "clientVersion": "2.20250101.00.00",
                                     "hl": "en", "gl": "US"}},
              "query": query, "params": "EgIQAQ%3D%3D"},   # filter: videos only
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"},
        timeout=15)
    r.raise_for_status()
    videos = []
    sections = (r.json().get("contents", {}).get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", []))
    for sec in sections:
        for item in sec.get("itemSectionRenderer", {}).get("contents", []):
            v = item.get("videoRenderer")
            if v and v.get("videoId"):
                videos.append(v)
    if not videos:
        raise ValueError("No results")
    out = []
    for v in videos[:limit]:
        dur = v.get("lengthText", {}).get("simpleText")
        sec = sum(int(x) * 60 ** i for i, x in enumerate(reversed(dur.split(":")))) if dur else 0
        title = "".join(run.get("text", "") for run in v.get("title", {}).get("runs", [])) or "Unknown"
        vid = v["videoId"]
        artist = "".join(run.get("text", "") for run in (v.get("ownerText") or v.get("longBylineText") or {}).get("runs", []))
        out.append({"title": title, "duration": sec, "artist": artist,
                    "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "link": f"https://www.youtube.com/watch?v={vid}"})
    return out


def innertube_lookup(query):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", query) or re.fullmatch(r"([\w-]{11})", query.strip())
    want = m.group(1) if m else None
    results = innertube_list(want or query)
    if want:
        for t in results:
            if t["link"].endswith(want):
                return t
    return results[0]


DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")   # song cache; keep it OUT of the /data volume (it would fill it up)


def video_id_of(link):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", link or "")
    return m.group(1) if m else link


_dl_tasks: dict = {}          # path -> running download task (so a prefetch and a real play never download twice)


async def api_download(link, video):
    """Same as _api_download, but concurrent callers share one download."""
    vid = video_id_of(link)
    path = os.path.join(DOWNLOAD_DIR, f"{vid}.{'mp4' if video else 'mp3'}")
    t = _dl_tasks.get(path)
    if t is None:
        t = asyncio.ensure_future(_api_download(link, video))
        _dl_tasks[path] = t
        t.add_done_callback(lambda _t, k=path: _dl_tasks.pop(k, None))
    return await asyncio.shield(t)


def prefetch(link, video):
    """Starts downloading in the background so the song is ready (or almost) when it is needed."""
    async def _go():
        try:
            await api_download(link, video)
        except Exception:
            pass
    asyncio.ensure_future(_go())


HEDGE_AFTER = float(os.getenv("API_HEDGE_SECONDS", "4"))   # primary API silent for this long -> ask the backup too
STREAM_DIRECT = os.getenv("STREAM_DIRECT", "0") == "1"      # 1 = start playing from the API url while it downloads


def cached_path(link, video):
    vid = video_id_of(link)
    path = os.path.join(DOWNLOAD_DIR, f"{vid}.{'mp4' if video else 'mp3'}")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    if not video:                                   # audio saved by the yt-dlp fallback (.webm / .m4a / ...)
        import glob
        for p in glob.glob(os.path.join(DOWNLOAD_DIR, f"{vid}.*")):
            if not p.endswith((".part", ".mp4", ".ytdl")) and os.path.getsize(p) > 0:
                return p
    return None


def stream_url(link, video):
    return (f"{API_URL}/download?url={video_id_of(link)}&type={'video' if video else 'audio'}"
            f"&api_key={SHRUTI_API_KEY}")


async def _fetch_to(base, vid, video, tmp):
    """One attempt on one API host: writes `tmp`, raises on any problem."""
    s = await aio()
    t0 = time.time()
    async with s.get(f"{base}/download",
                     params={"url": vid, "type": "video" if video else "audio", "api_key": SHRUTI_API_KEY},
                     timeout=aiohttp.ClientTimeout(total=600 if video else 300)) as r:
        if r.status != 200:
            raise RuntimeError(f"API status {r.status}")
        first = time.time() - t0
        n = 0
        with open(tmp, "wb") as f:
            async for chunk in r.content.iter_chunked(262144):
                f.write(chunk)
                n += len(chunk)
    if n == 0:
        raise RuntimeError("empty file")
    print(f"[dl] {vid} via {base}: first byte {first:.1f}s, total {time.time() - t0:.1f}s, {n // 1024} KB")


def _ytdlp_audio_sync(link, vid):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    o = ydl_opts(False)
    o["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{vid}.%(ext)s")
    with YoutubeDL(o) as y:
        info = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=True)
        return y.prepare_filename(info)


async def _api_download(link, video):
    """Downloads the track through Shruti API and returns the file path.
    The backup API is asked too when the primary is slow (or fails); whoever finishes first wins."""
    vid = video_id_of(link)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    path = os.path.join(DOWNLOAD_DIR, f"{vid}.{'mp4' if video else 'mp3'}")
    hit = cached_path(link, video)
    if hit:
        return hit
    bases = [b for b in (API_URL, API_URL_BACKUP) if b]
    tmps = {b: f"{path}.{i}.part" for i, b in enumerate(bases)}
    pending, owner, errors, winner = set(), {}, [], None

    def launch(i):
        t = asyncio.ensure_future(_fetch_to(bases[i], vid, video, tmps[bases[i]]))
        owner[t] = bases[i]
        pending.add(t)

    launch(0)
    nxt = 1
    try:
        while pending:
            done, _ = await asyncio.wait(pending, timeout=HEDGE_AFTER if nxt < len(bases) else None,
                                         return_when=asyncio.FIRST_COMPLETED)
            if not done:                                    # primary is slow: ask the backup as well
                launch(nxt)
                nxt += 1
                continue
            for t in done:
                pending.discard(t)
                if t.exception() is None:
                    winner = owner[t]
                    break
                errors.append(str(t.exception()) or type(t.exception()).__name__)
            if winner:
                break
            if not pending and nxt < len(bases):            # primary failed fast: backup now
                launch(nxt)
                nxt += 1
    finally:
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    if winner:
        os.replace(tmps[winner], path)
    for tmp in tmps.values():
        if os.path.exists(tmp):
            os.remove(tmp)
    if winner:
        return path
    # Both Shruti APIs failed (e.g. Cloudflare 522) -> fall back to yt-dlp
    print(f"[dl] APIs failed ({errors[-1] if errors else 'unknown'}), trying yt-dlp for {vid}")
    try:
        fn = _ytdlp_video_sync if video else _ytdlp_audio_sync
        got = await asyncio.get_running_loop().run_in_executor(None, fn, link, vid)
        if got and os.path.exists(got) and os.path.getsize(got) > 0:
            return got
        errors.append("yt-dlp: empty file")
    except Exception as e:
        errors.append(f"yt-dlp: {str(e)[:100]}")
    raise RuntimeError(f"Download failed ({'; '.join(errors[-2:]) if errors else 'unknown error'})")


# ---------- ui ----------
def mmss(sec, ref=None):
    return fmt(sec, ref)


def progress_label(pid):
    """'01:15 ╱╲╱●╲╱╲╱╲╱ 03:49' (position / straight line with a dot / length) for the first panel button."""
    q = queues.get(pid)
    n = 10

    def line(i):
        # played part = zigzag ╱╲╱╲, dot on the current spot, rest = plain line ─
        return "".join("\u25fb" if k == i else "\u2500" for k in range(n))

    if not q:
        return "00:00 " + line(0) + " 00:00"
    t = q[0]
    dur, pos = int(t.get("duration") or 0), int(track_pos(t))
    if dur:
        pos = min(pos, dur)
    i = min(n - 1, pos * n // dur) if dur else 0
    return f"{mmss(pos, dur)} {line(i)} {mmss(dur) if dur else '--:--'}"


def panel(pid):
    ap_on = autoplay.get(pid)
    upd = Btn("υᴘᴅᴧᴛє", GREEN, key="update", url=UPDATE_URL) if UPDATE_URL else None
    return IKM([
        [Btn(progress_label(pid), BLUE, callback_data=f"noop|{pid}")],
        [Btn("II", GREEN, callback_data=f"pause|{pid}"),        # pause
         Btn("▷", BLUE, callback_data=f"resume|{pid}"),         # resume
         Btn("▷▷", GREEN, callback_data=f"skip|{pid}"),         # skip
         Btn("▢", RED, callback_data=f"stop|{pid}")],           # stop
        [Btn("ᴧᴜᴛσᴘʟαʏ", GREEN if ap_on else BLUE, callback_data=f"autoplay|{pid}")] + ([upd] if upd else []),
    ])


def requester_html(track):
    """Clickable requester name; built here so it is not HTML-escaped."""
    if track.get("by_id"):
        return f'<a href="tg://user?id={track["by_id"]}">{html.escape(str(track.get("by_name") or "User"))}</a>'
    return html.escape(re.sub(r"<[^>]+>", "", str(track.get("by", "Unknown"))))


TITLE_MAX = 28                                      # characters of the song name shown on the cards


def title_html(track):
    """Short song name ending in "...", clickable when the track has a YouTube link."""
    t = str(track.get("title") or "Unknown").strip()
    if len(t) > TITLE_MAX:
        t = t[:TITLE_MAX].rstrip() + "..."
    t = html.escape(t)
    link = str(track.get("link") or "")
    return f'<a href="{html.escape(link, quote=True)}">{t}</a>' if link.startswith("http") else t


def queued_card(track, pos):
    """Card for a song added behind the one that is already playing in the VC."""
    title = title_html(track)
    return (
        f"<blockquote><b>💮 ɪηᴄσϻɪηɢ ᴛʀαᴄᴋ ᴅєᴛєᴄᴛєᴅ : #{pos}</b></blockquote>\n"
        "<blockquote>"
        f"<b>🎋 ᴛɪᴛʟє :</b> {title}\n"
        f"<b>✨ ᴅυʀαᴛɪσɴ :</b> {fmt(track.get('duration'))}\n"
        f"<b>🥀 ʀєǫυєѕᴛєʀ :</b> {requester_html(track)}\n"
        "<b>🏵️ѕᴛαηᴅʙʏ, ʏσυʀ ѕєѕѕɪσɴ вєɢɪηѕ ѕнσʀᴛʟʏ</b>"
        "</blockquote>"
    )


def card(track, pid):
    """HTML caption: blockquote 1 = Streaming, blockquote 2 = title / duration / requester."""
    title = title_html(track)
    by = requester_html(track)
    return (
        "<blockquote><b>💮 ѕᴛʀєαϻɪηɢ</b></blockquote>\n"
        "<blockquote>"
        f"<b>🎋 ᴛɪᴛʟє :</b> {title}\n"
        f"<b>✨ ᴅυʀαᴛɪσɴ :</b> {fmt(track.get('duration'))}\n"
        f"<b>🥀 ʀєǫυєѕᴛєʀ :</b> {by}"
        "</blockquote>"
    )


async def progress_loop(pid, track, msg):
    """Refreshes the progress button every ~10 s while this track is the one playing."""
    last = None
    try:
        while True:
            await asyncio.sleep(10)
            q = queues.get(pid)
            if not q or q[0] is not track:
                return
            if track.get("paused_at"):
                continue
            markup = panel(pid)
            label = markup.inline_keyboard[0][0].text
            if label == last:
                continue
            last = label
            try:
                await msg.edit_reply_markup(markup)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception:
                pass                            # message deleted / not modified
    except asyncio.CancelledError:
        pass


# ---------- now-playing card picture (blurred background + glass player) ----------
THUMB_DIR = os.path.join(os.getenv("DOWNLOAD_DIR", "downloads"), "cards")
CARD_FONT_MED = os.getenv("CARD_FONT_MED", "fonts/Poppins-Medium.ttf")
CARD_FONT_REG = os.getenv("CARD_FONT_REG", "fonts/Poppins-Regular.ttf")


def _card_font(path, size):
    from PIL import ImageFont
    for f in (path, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _round_mask(size, radius):
    from PIL import Image, ImageDraw
    k = 3                                                   # draw big, shrink = smooth edges
    m = Image.new("L", (size[0] * k, size[1] * k), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] * k - 1, size[1] * k - 1), radius * k, fill=255)
    return m.resize(size, Image.LANCZOS)


def _fit_text(draw, text, font, max_w):
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "...", font=font) > max_w:
        text = text[:-1]
    return text.rstrip() + "..."


def _build_card(raw_img, title, artist, duration, out):
    """Player picture: blurred background + rounded album art on the left, grey player panel on the right."""
    from PIL import Image, ImageDraw, ImageFilter
    import math
    S = 2                                                   # draw at 2x, shrink at the end = smooth edges
    W, H = 1280 * S, 720 * S

    def P(v):
        return int(round(v * S))

    def R(*c):
        return tuple(P(v) for v in c)

    src = Image.open(raw_img).convert("RGB")
    sw, sh = src.size
    if sh > sw * 0.7 and sw / sh < 1.45:                    # hqdefault has black bars on top and bottom: cut them
        bar = int(sh * 0.125)
        src = src.crop((0, bar, sw, sh - bar))
        sw, sh = src.size
    # background: cover + heavy blur + a little darker
    sc = max(W / sw, H / sh)
    bg = src.resize((int(sw * sc) + 1, int(sh * sc) + 1), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    bg = bg.resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BICUBIC)
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.12)
    # right half: grey player panel with a little grain
    px = P(640)
    right = bg.crop((px, 0, W, H))
    grain = Image.blend(Image.new("RGB", right.size, (88, 88, 88)), Image.effect_noise(right.size, 14).convert("RGB"), 0.05)
    bg.paste(Image.blend(right, grain, 0.975), (px, 0))
    # album art: centre square, rounded corners, soft shadow
    side = min(src.size)
    sq = src.crop(((src.width - side) // 2, (src.height - side) // 2, (src.width + side) // 2, (src.height + side) // 2))
    art = P(512)
    sq = sq.resize((art, art), Image.LANCZOS)
    ax, ay = P(100), P(104)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((ax, ay + P(22), ax + art, ay + art + P(22)), P(34), fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(P(18)))
    bg = Image.alpha_composite(bg.convert("RGBA"), shadow).convert("RGB")
    bg.paste(sq, (ax, ay), _round_mask((art, art), P(30)))
    d = ImageDraw.Draw(bg, "RGBA")
    white, light, grey = (255, 255, 255, 255), (225, 225, 225, 255), (190, 190, 190, 255)
    # title + artist
    f_title, f_artist, f_time = _card_font(CARD_FONT_MED, P(28)), _card_font(CARD_FONT_REG, P(20)), _card_font(CARD_FONT_REG, P(19))
    max_w = P(345)
    d.text((P(715), P(132)), _fit_text(d, title or "Unknown", f_title, max_w), font=f_title, fill=white, anchor="lm")
    if artist:
        d.text((P(714), P(167)), _fit_text(d, artist, f_artist, max_w), font=f_artist, fill=(205, 205, 205, 235), anchor="lm")
    # star + more buttons
    for cx in (1112, 1188):
        d.ellipse(R(cx - 24, 136, cx + 24, 184), fill=(255, 255, 255, 55))
    pts = []
    for i in range(10):
        r = 12 if i % 2 == 0 else 5.2
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((P(1112 + r * math.cos(a)), P(161 + r * math.sin(a))))
    d.line(pts + [pts[0]], fill=white, width=P(2), joint="curve")
    for dy in (-10, 0, 10):
        d.ellipse(R(1188 - 2.8, 160 + dy - 2.8, 1188 + 2.8, 160 + dy + 2.8), fill=white)
    # progress bar + times
    secs = int(duration or 0)
    total = f"{secs // 3600}:{secs % 3600 // 60:02d}:{secs % 60:02d}" if secs >= 3600 else f"{secs // 60}:{secs % 60:02d}"
    d.rounded_rectangle(R(748, 239, 1210, 251), P(6), fill=(120, 120, 114, 255))
    d.ellipse(R(748, 238, 762, 252), fill=light)
    d.text((P(745), P(285)), "0:00", font=f_time, fill=(175, 175, 175, 255), anchor="lm")
    d.text((P(1203), P(283)), "-" + total, font=f_time, fill=(175, 175, 175, 255), anchor="rm")
    # controls: rewind / pause / forward
    def tri(pts_):
        pts_ = [(P(x), P(y)) for x, y in pts_]
        d.polygon(pts_, fill=white)
        d.line(pts_ + [pts_[0]], fill=white, width=P(5), joint="curve")
    for x0 in (779, 816):                                   # rewind: two triangles pointing left
        tri([(x0 + 1, 416), (x0 + 33, 396), (x0 + 33, 436)])
    for x0 in (1109, 1146):                                 # forward: two triangles pointing right
        tri([(x0 + 33, 416), (x0 + 1, 396), (x0 + 1, 436)])
    d.rounded_rectangle(R(951, 380, 965, 450), P(6), fill=white)
    d.rounded_rectangle(R(992, 380, 1006, 450), P(6), fill=white)
    # volume
    def speaker(x):
        d.polygon([(P(x), P(541)), (P(x + 6), P(541)), (P(x + 15), P(533)), (P(x + 15), P(559)), (P(x + 6), P(551)), (P(x), P(551))], fill=grey)
    speaker(755)
    d.rounded_rectangle(R(798, 540, 1140, 552), P(6), fill=(112, 112, 106, 255))
    d.rounded_rectangle(R(798, 540, 1050, 552), P(6), fill=light)
    speaker(1167)
    d.arc(R(1176, 537, 1192, 555), -50, 50, fill=grey, width=P(2))
    d.arc(R(1180, 531, 1202, 561), -50, 50, fill=grey, width=P(2))
    # lyrics + queue icons
    d.rounded_rectangle(R(850, 619, 890, 649), P(8), outline=grey, width=P(3))
    d.polygon([(P(860), P(648)), (P(860), P(660)), (P(872), P(648))], fill=grey)
    for qx in (862, 877):
        d.ellipse(R(qx - 4, 630, qx + 4, 638), fill=grey)
        d.line([(P(qx + 3), P(634)), (P(qx - 1), P(643))], fill=grey, width=P(2))
    for yy in (623, 637, 651):
        d.ellipse(R(1066, yy - 2.5, 1071, yy + 2.5), fill=grey)
        d.line([(P(1079), P(yy)), (P(1106), P(yy))], fill=grey, width=P(3))
    bg.resize((1280, 720), Image.LANCZOS).save(out, "JPEG", quality=92)


_card_tasks: dict = {}


async def card_thumb(track):
    """Path of the glass-player picture for this track (cached), or None -> caller uses the plain thumbnail."""
    try:
        from PIL import Image                                # noqa: F401
    except ImportError:
        return None
    vid = video_id_of(track.get("link"))
    if not track.get("thumb") or not vid:
        return None
    os.makedirs(THUMB_DIR, exist_ok=True)
    out = os.path.join(THUMB_DIR, f"{vid}_v2.jpg")
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    t = _card_tasks.get(out)
    if t is None:
        async def _go():
            s = await aio()
            data = None
            for url in (f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg", track["thumb"]):
                try:
                    async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                        if r.status == 200:
                            data = await r.read()
                            if len(data) > 5000:
                                break
                except Exception:
                    pass
            if not data:
                raise RuntimeError("thumbnail download failed")
            import io
            await asyncio.get_running_loop().run_in_executor(
                None, _build_card, io.BytesIO(data), track.get("title"), track.get("artist"), track.get("duration"), out)
            files = sorted((os.path.join(THUMB_DIR, f) for f in os.listdir(THUMB_DIR)), key=os.path.getmtime)
            for old in files[:-200]:                         # keep the newest 200 pictures only
                try:
                    os.remove(old)
                except Exception:
                    pass
            return out
        t = asyncio.ensure_future(_go())
        _card_tasks[out] = t
        t.add_done_callback(lambda _t, k=out: _card_tasks.pop(k, None))
    try:
        return await asyncio.shield(t)
    except Exception as e:
        print("card thumb failed:", e)
        return None


async def send_card(pid, track):
    origin = origins.get(pid, pid)
    text = card(track, pid)
    msg = None
    try:
        if track.get("thumb"):
            pic = await card_thumb(track) or track["thumb"]
            msg = await bot.send_photo(origin, pic, caption=text, parse_mode=ParseMode.HTML, reply_markup=panel(pid))
    except Exception:
        pass
    if msg is None:
        msg = await bot.send_message(origin, text, parse_mode=ParseMode.HTML, reply_markup=panel(pid))
    old = progress_tasks.pop(pid, None)
    if old:
        old.cancel()
    progress_tasks[pid] = asyncio.create_task(progress_loop(pid, track, msg))
    return msg


# ---------- logger ----------
async def send_log(origin, pid, track, pos):
    """Log message for the logger group: text only (no picture)."""
    if not LOGGER_ID or not settings.get("logger", True):
        return
    try:
        chat = await bot.get_chat(origin)
        gname = chat.title or "Unknown"
        glink = f"https://t.me/{chat.username}" if chat.username else None
        group_line = f"[{gname}]({glink})" if glink else gname
        status = "▶ Now Playing" if pos == 0 else f"➕ Added to queue: {pos}"
        title = str(track.get("title") or "Unknown").replace("[", "(").replace("]", ")")
        title_line = f"[{title}]({track['link']})" if str(track.get("link") or "").startswith("http") else title
        secs = int(track.get("duration") or 0)
        dur_text = fmt(secs) if secs >= 3600 else f"{secs // 60}:{secs % 60:02d}"       # 4:52
        text = (
            f"{status}\n\n"
            f"🏠 **Group:-** {group_line}\n"
            f"🆔 **Group id :-** `{origin}`\n\n"
            f"🎵 **Title:** {title_line}\n"
            f"⏱ **Duration:** {dur_text} min\n"
            f"👤 **Requested by:** {track.get('by', 'Unknown')}"
        )
        try:
            await bot.send_message(LOGGER_ID, text, **NO_PREVIEW)
        except Exception:                                   # a strange character in the title broke the formatting
            await bot.send_message(LOGGER_ID, text.replace("**", "").replace("`", ""),
                                   parse_mode=ParseMode.DISABLED, **NO_PREVIEW)
    except Exception as e:
        print("logger error:", e)


# ---------- video safety: the file MUST really contain a picture ----------
async def has_video_stream(path):
    """True when ffprobe finds a video stream in the file (True too when ffprobe is not installed)."""
    try:
        p = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type",
            "-of", "csv=p=0", path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(p.communicate(), 25)
        return b"video" in out
    except FileNotFoundError:
        return True
    except Exception as e:
        print("ffprobe failed:", e)
        return True


def _ytdlp_video_sync(link, vid):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    o = ydl_opts(True)
    o.update({"outtmpl": os.path.join(DOWNLOAD_DIR, f"{vid}.%(ext)s"), "merge_output_format": "mp4",
              "format": "best[height<=720][ext=mp4]/best[height<=720]/best"})
    with YoutubeDL(o) as y:
        info = y.extract_info(link, download=True)
        return y.prepare_filename(info)


async def ensure_video_file(track, path):
    """The API sometimes answers a /vplay with an audio-only file (the VC then shows no video).
    Detect that and fetch a real video with yt-dlp instead."""
    if await has_video_stream(path):
        return path
    print(f"[video] {path} has NO video stream, trying yt-dlp instead")
    try:
        os.remove(path)
    except Exception:
        pass
    vid = video_id_of(track["link"])
    try:
        got = await asyncio.get_running_loop().run_in_executor(None, _ytdlp_video_sync, track["link"], vid)
    except Exception as e:
        raise RuntimeError(f"video download failed ({str(e)[:120]})")
    if not got or not os.path.exists(got) or not await has_video_stream(got):
        raise RuntimeError("no video available for this song")
    want = os.path.join(DOWNLOAD_DIR, f"{vid}.mp4")
    if got != want:
        os.replace(got, want)
    return want


# ---------- playback core ----------
async def vc_pause(pid):
    await call.pause(pid)


async def vc_resume(pid):
    await call.resume(pid)


async def start_track(pid, offset=0):
    """Plays the first track of the queue, optionally starting `offset` seconds in (used by /seek)."""
    track = queues[pid][0]
    path = track.get("local") if track.get("local") and os.path.exists(track["local"]) else None   # file from Telegram
    if path is None:
        path = cached_path(track["link"], track["video"])
    if path is None:
        if STREAM_DIRECT and not offset:
            prefetch(track["link"], track["video"])         # also cache it (loop / seek / previous need the file)
            path = stream_url(track["link"], track["video"])
        else:
            path = await api_download(track["link"], track["video"])
    if track["video"] and not track.get("local") and not str(path).startswith("http"):
        path = await ensure_video_file(track, path)
    extra = {"ffmpeg_parameters": f"-ss {int(offset)}"} if offset else {}
    if track["video"]:
        stream = MediaStream(path, **extra)
    else:
        stream = MediaStream(path, video_flags=MediaStream.Flags.IGNORE, **extra)
    await call.play(pid, stream)
    track["t0"] = time.time() - offset          # wall-clock moment the track "would have" started
    track["paused_at"] = None


def track_pos(track):
    """Current playback position in seconds (pause-aware)."""
    if not track.get("t0"):
        return 0
    return max(0, (track.get("paused_at") or time.time()) - track["t0"])


def mark_pause(pid):
    q = queues.get(pid)
    if q and q[0].get("t0") and not q[0].get("paused_at"):
        q[0]["paused_at"] = time.time()


def mark_resume(pid):
    q = queues.get(pid)
    if q and q[0].get("paused_at"):
        q[0]["t0"] += time.time() - q[0]["paused_at"]
        q[0]["paused_at"] = None


def record_play(chat_id, user_id, name):
    """Counts one played/queued song for this user in this group (for /leaderboard)."""
    if not user_id:
        return
    g = plays.setdefault(str(chat_id), {})
    u = g.setdefault(str(user_id), {"n": 0, "name": name or "User"})
    u["n"] += 1
    if name:
        u["name"] = name
    save("plays.json", plays)


joined: set = set()     # chats where the assistant is already known to be a member
_assistant_id = None
_assistant_me = None


class AssistantBanned(RuntimeError):
    pass


async def assistant_info():
    """(username, id) of the assistant account, cached."""
    global _assistant_me, _assistant_id
    if _assistant_me is None:
        _assistant_me = await assistant.get_me()
        _assistant_id = _assistant_me.id
    return _assistant_me.username, _assistant_me.id


def _mention_html(user_id, name):
    return f'<a href="tg://user?id={user_id}">{html.escape(name)}</a>'


async def banned_text():
    await assistant_info()
    me = _assistant_me
    name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "Assistant"
    uname = f"@{me.username}" if me.username else "No username"
    return (
        f"<b> {_mention_html(me.id, name)} ᴧѕѕɪѕᴛαηᴛ ɪѕ вαηηєᴅ ɪη ʏσυʀ ɢʀσυᴘ.</b>\n\n"
        f"<b>ɴαϻє :-</b> {_mention_html(me.id, name)}\n"
        f"<b>ɪᴅ :-</b> <code>{me.id}</code>\n"
        f"<b>υѕєʀηαϻє :-</b> {html.escape(uname)}"
    )


async def reply_banned(msg, pid):
    """Edit `msg` into the 'assistant is banned' card with an Unban Assistant button."""
    markup = IKM([[Btn("υηвαη ᴧѕѕɪѕᴛαηᴛ", GREEN, callback_data=f"unbanast:{pid}")]])
    return await msg.edit_text(await banned_text(), parse_mode=ParseMode.HTML, reply_markup=markup)


async def assistant_banned(chat_id):
    """Ask the BOT (it is an admin) whether the assistant is banned. A banned
    assistant cannot read the chat itself, it only gets CHANNEL_PRIVATE."""
    try:
        _, aid = await assistant_info()
        member = await bot.get_chat_member(chat_id, aid)
        return member.status == ChatMemberStatus.BANNED
    except Exception:
        return False


async def ensure_assistant(chat_id, force=False):
    """Makes the assistant join the chat by itself. The bot only needs the
    'Invite Users via Link' admin right (it creates a private invite link)."""
    global _assistant_id
    if chat_id in joined:
        return
    try:
        member = await assistant.get_chat_member(chat_id, "me")
        if member.status == ChatMemberStatus.BANNED:
            raise AssistantBanned("assistant is banned")
        joined.add(chat_id)
        return
    except AssistantBanned:
        raise
    except Exception:
        if await assistant_banned(chat_id):    # CHANNEL_PRIVATE can also mean "banned"
            raise AssistantBanned("assistant is banned")
        # not a member (or never seen this chat): join below
    try:
        chat = await bot.get_chat(chat_id)
        if chat.username:
            link = f"https://t.me/{chat.username}"
        else:
            inv = await bot.create_chat_invite_link(chat_id, name="Music Assistant", member_limit=1)
            link = inv.invite_link
    except ChatAdminRequired:
        raise RuntimeError("ϻαᴋє ᴛнє вσᴛ αη αᴅϻɪη αηᴅ ɢɪᴠє ɪᴛ ᴛнє 'ɪηᴠɪᴛє υѕєʀѕ ᴠɪα ʟɪηᴋ' ᴘєʀϻɪѕѕɪση, "
                           "ѕσ ᴛнє αѕѕɪѕᴛαηᴛ ᴄαη ᴊσɪη αυᴛσϻαᴛɪᴄαʟʟʏ,")
    try:
        await assistant.join_chat(link)
    except UserAlreadyParticipant:
        pass
    except InviteRequestSent:                  # group has join-requests on: bot approves the assistant
        if not _assistant_id:
            _assistant_id = (await assistant.get_me()).id
        try:
            await bot.approve_chat_join_request(chat_id, _assistant_id)
        except Exception:
            raise RuntimeError("ᴧ ᴊσɪη ʀєǫυєѕᴛ ɪѕ ᴘєηᴅɪηɢ. ɢɪᴠє ᴛнє вσᴛ ᴛнє 'ɪηᴠɪᴛє υѕєʀѕ' αᴅϻɪη ʀɪɢнᴛ "
                               "σʀ αᴘᴘʀσᴠє ᴛнє αѕѕɪѕᴛαηᴛ ϻαηυαʟʟʏ.")
    except UserBannedInChannel:
        raise AssistantBanned("assistant is banned")
    joined.add(chat_id)


def reset_chat_state(pid):
    """Forget EVERYTHING about this play_id (queue, history, loop, autoplay, background tasks)."""
    queues.pop(pid, None)
    history.pop(pid, None)
    loops.pop(pid, None)
    autoplay.pop(pid, None)
    for d in (progress_tasks, _lineups):
        t = d.pop(pid, None)
        if t and not t.done():
            t.cancel()


async def drop_stale_queue(pid):
    """The voice chat was closed but the end update never reached us: if the queue says 'playing' while the
    assistant is no longer in a call, throw the old queue away so the new /play starts fresh."""
    q = queues.get(pid)
    if not q or not q[0].get("t0"):    # nothing playing / the first song is still starting up
        return
    try:
        await call.played_time(pid)
    except AttributeError:                      # this pytgcalls has no played_time: rely on the end update only
        return
    except Exception as e:
        if type(e).__name__ in ("NotInCallError", "NoActiveGroupCall", "NoActiveGroupCallError"):
            reset_chat_state(pid)


async def add_to_queue(origin, pid, track):
    await ensure_assistant(pid)
    await drop_stale_queue(pid)
    origins[pid] = origin
    q = queues.setdefault(pid, [])
    if len(q) >= 2 and _is_auto(q[-1]) and not _is_auto(track):
        q.insert(len(q) - 1, track)            # requested songs play before the lined-up autoplay song
    else:
        q.append(track)
    if len(q) == 1:
        try:
            await start_track(pid)
        except Exception:
            joined.discard(pid)                # re-check membership next time
            q.pop(0)
            if not q:
                queues.pop(pid, None)
            if await assistant_banned(pid):
                raise AssistantBanned("assistant is banned")
            try:
                await ensure_assistant(pid)    # raises AssistantBanned if that is the real cause
            except AssistantBanned:
                raise
            except Exception:
                pass
            raise
        await send_card(pid, track)
        record_play(origin, track.get("by_id"), track.get("by_name"))
        asyncio.create_task(send_log(origin, pid, track, 0))
        lineup_autoplay(pid)                   # autoplay on: find + download the related song while this one plays
        return 0
    if not track.get("local"):
        prefetch(track["link"], track["video"])    # queued song: download now, so it starts instantly later
    record_play(origin, track.get("by_id"), track.get("by_name"))
    pos = next(i for i, t in enumerate(q) if t is track)
    asyncio.create_task(send_log(origin, pid, track, pos))
    return pos


async def force_play(origin, pid, track):
    """/forceplay: the new song starts at once, the current one is stopped (the rest of the queue stays)."""
    await ensure_assistant(pid)
    await drop_stale_queue(pid)
    origins[pid] = origin
    q = queues.get(pid)
    if not q:                                   # nothing is playing: same as a normal /play
        return await add_to_queue(origin, pid, track)
    old = q[0]
    # download BEFORE touching the queue: if the old song ends meanwhile, on_end must not pop the new one
    if not track.get("local"):
        await api_download(track["link"], track["video"])
    q = queues.get(pid)
    if not q or q[0] is not old:                # the old song ended / was skipped while downloading
        return await add_to_queue(origin, pid, track)
    q.insert(0, track)
    try:
        await start_track(pid)                  # call.play() replaces the running stream
    except Exception:
        if track in q:
            q.remove(track)                     # failed: the old song keeps playing
        raise
    if old in q:
        q.remove(old)                           # the interrupted song is stopped ...
    history.setdefault(pid, []).append(old)     # ... but the ⏮️ button can still bring it back
    del history[pid][:-20]
    if len(q) >= 2 and _is_auto(q[-1]):         # lined-up autoplay song was related to the OLD song: drop it
        q.pop()
    lt = _lineups.pop(pid, None)
    if lt and not lt.done():
        lt.cancel()
    await send_card(pid, track)
    record_play(origin, track.get("by_id"), track.get("by_name"))
    asyncio.create_task(send_log(origin, pid, track, 0))
    lineup_autoplay(pid)
    return 0


def _cand_ids(data):
    """Video ids from the Shruti /autoplay answer (format-tolerant: ids, links or dicts)."""
    items = data.get("tracks") if isinstance(data, dict) else data
    out = []
    for t in items or []:
        if isinstance(t, str):
            out.append(video_id_of(t))
        elif isinstance(t, dict):
            for k in ("id", "video_id", "videoId", "vidid", "link", "url"):
                if t.get(k):
                    out.append(video_id_of(str(t[k])))
                    break
    return [i for i in out if re.fullmatch(r"[\w-]{11}", i or "")]


# ---------- autoplay: songs that are LIKE the one playing ----------
_NOISE = re.compile(
    r"\b(official|video|videos|music|lyrical|lyrics?|audio|full|song|songs|hd|4k|visualizer|version|"
    r"ft|feat|featuring|new|latest)\b", re.I)
_BAD = re.compile(
    r"\b(jukebox|nonstop|non-stop|mashup|playlist|best of|top \d+|\d+ hours?|full album|podcast|interview|"
    r"reaction|trailer|teaser|shorts?)\b", re.I)
_WEB_CTX = {"client": {"clientName": "WEB", "clientVersion": "2.20250101.00.00", "hl": "en", "gl": "US"}}
_ID11 = re.compile(r"[\w-]{11}")


def _clean_title(title):
    t = re.sub(r"[\(\[\{].*?[\)\]\}]", " ", title or "")      # (Official Video) [Lyrical] ...
    t = _NOISE.sub(" ", t)
    t = re.sub(r"[|\-–—]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _tokens(title):
    return {w for w in re.split(r"[^\w\u0900-\u097F]+", _clean_title(title).lower()) if w}


def _same_song(a, b):
    """True when two titles are the same song (another upload / lyric video / lofi of it)."""
    if not a or not b:
        return False
    if a == b:
        return True
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    if len(small) == 1:                       # one-word title: "Ishq" vs "Ishq Faheem Abdullah"
        return small <= big and len(big) <= 3
    return len(small & big) / len(small) >= 0.8


def _ok(meta, skip_ids, skip_keys):
    """A usable autoplay pick: a real song (not a jukebox/mashup/short), not played already, not a re-upload of one."""
    if video_id_of(meta["link"]) in skip_ids:
        return False
    d = meta.get("duration") or 0
    if d and not 60 <= d <= 660:
        return False
    if _BAD.search(meta["title"] or ""):
        return False
    k = _tokens(meta["title"])
    return not any(_same_song(k, s) for s in skip_keys)


def _txt(x):
    if isinstance(x, dict):
        return x.get("simpleText") or "".join(r.get("text", "") for r in x.get("runs", []))
    return x or ""


def _clock_to_sec(s):
    try:
        parts = [int(p) for p in str(s).strip().split(":")]
    except ValueError:
        return 0
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))


def _first_clock(node):
    """First '3:45'-looking string anywhere inside `node` (new lockup layout keeps the length in a thumbnail badge)."""
    if isinstance(node, str):
        return node if re.fullmatch(r"\d{1,2}(?::\d{2}){1,2}", node.strip()) else None
    if isinstance(node, dict):
        node = list(node.values())
    if isinstance(node, list):
        for v in node:
            c = _first_clock(v)
            if c:
                return c
    return None


def _track_meta(vid, title, dur):
    return {"title": title or "Unknown", "duration": dur, "link": f"https://www.youtube.com/watch?v={vid}",
            "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}


def _video_items(node, out):
    """Collects every video found anywhere in a YouTube JSON answer (works for old and new page layouts)."""
    if isinstance(node, dict):
        for key in ("playlistPanelVideoRenderer", "compactVideoRenderer", "videoRenderer", "gridVideoRenderer"):
            v = node.get(key)
            if isinstance(v, dict) and _ID11.fullmatch(v.get("videoId") or ""):
                out.append(_track_meta(v["videoId"], _txt(v.get("title")), _clock_to_sec(_txt(v.get("lengthText")))))
        lv = node.get("lockupViewModel")
        if isinstance(lv, dict) and lv.get("contentType") in (None, "LOCKUP_CONTENT_TYPE_VIDEO") \
                and _ID11.fullmatch(lv.get("contentId") or ""):
            title = ((lv.get("metadata") or {}).get("lockupMetadataViewModel") or {}).get("title") or {}
            out.append(_track_meta(lv["contentId"], title.get("content", ""), _clock_to_sec(_first_clock(lv) or "")))
        for v in node.values():
            _video_items(v, out)
    elif isinstance(node, list):
        for v in node:
            _video_items(v, out)


def youtube_related(vid):
    """YouTube's own 'songs like this': the song's auto-Mix first (same artist / same mood), then the related column."""
    r = http().post("https://www.youtube.com/youtubei/v1/next?prettyPrint=false",
                    json={"context": _WEB_CTX, "videoId": vid, "playlistId": "RD" + vid},
                    headers={"User-Agent": UA}, timeout=12)
    r.raise_for_status()
    data = r.json()
    two = (data.get("contents") or {}).get("twoColumnWatchNextResults") or {}
    mix, side = [], []
    _video_items(two.get("playlist") or {}, mix)
    _video_items(two.get("secondaryResults") or {}, side)
    if not mix and not side:                  # layout changed: take whatever videos the answer has
        _video_items(data, side)
    seen, out = set(), []
    for t in mix + side:
        i = video_id_of(t["link"])
        if i not in seen:
            seen.add(i)
            out.append(t)
    return out


def related_sync(last, skip_ids, skip_keys):
    """Blocking: picks a song that is like `last`. YouTube's related list, then the Shruti API, then a search."""
    vid = video_id_of(last["link"])
    try:
        for meta in youtube_related(vid):
            if _ok(meta, skip_ids, skip_keys):
                return meta
    except Exception as e:
        print("autoplay: youtube related failed:", e)
    for base in (API_URL, API_URL_BACKUP):
        try:
            r = http().get(f"{base}/autoplay", params={"video_id": vid, "api_key": SHRUTI_API_KEY}, timeout=10)
            if r.status_code != 200:
                continue
            for cid in [c for c in _cand_ids(r.json()) if c not in skip_ids][:4]:
                try:
                    meta = innertube_lookup(cid)
                except Exception:
                    continue
                if _ok(meta, skip_ids, skip_keys):
                    return meta
            break                                # API answered but nothing usable: use search below
        except Exception:
            continue
    try:
        for meta in innertube_list(_clean_title(last["title"]) + " songs", 15):
            if _ok(meta, skip_ids, skip_keys):
                return meta
    except Exception:
        pass
    return None


def _is_auto(t):
    return t.get("by_id") == 0 and t.get("by_name") == "Autoplay"


async def find_autoplay(pid, last):
    played = history.get(pid, []) + queues.get(pid, []) + [last]
    skip_ids = {video_id_of(t["link"]) for t in played}
    skip_keys = [_tokens(t["title"]) for t in played]
    loop = asyncio.get_running_loop()
    try:
        meta = await loop.run_in_executor(None, related_sync, last, skip_ids, skip_keys)
    except Exception as e:
        print("autoplay error:", e)
        return None
    if not meta:
        return None
    prefetch(meta["link"], last["video"])        # download now, so the switch to this song is instant
    return dict(meta, video=last["video"], channel=last.get("channel"),
                by="ᴧυᴛσᴘʟαʏ", by_id=0, by_name="Autoplay")


_lineups: dict = {}      # play_id -> task that is finding the next autoplay song


def lineup_autoplay(pid):
    """While a song plays, find + download the related song in the background: /skip and the song end then switch at once."""
    q = queues.get(pid)
    if not autoplay.get(pid) or not q or len(q) != 1 or q[0].get("local"):
        return                                  # (a voice note / audio file has no "related songs")
    t = _lineups.get(pid)
    if t and not t.done():
        return
    seed = q[0]

    async def _go():
        nxt = await find_autoplay(pid, seed)
        q2 = queues.get(pid)
        if not nxt or not autoplay.get(pid) or q2 is None:
            return
        still_playing = len(q2) == 1 and q2[0] is seed
        just_skipped = not q2 and bool(history.get(pid)) and history[pid][-1] is seed
        if still_playing or just_skipped:
            q2.append(nxt)

    task = asyncio.ensure_future(_go())
    _lineups[pid] = task

    def _done(_t, k=pid):
        if _lineups.get(k) is _t:
            _lineups.pop(k, None)
    task.add_done_callback(_done)


async def next_track(pid, force=False):
    q = queues.get(pid, [])
    last = None
    if q and (force or not loops.get(pid)):
        last = q.pop(0)
        history.setdefault(pid, []).append(last)
        del history[pid][:-20]                  # remember the last 20 tracks only
    if not q and last and autoplay.get(pid) and not last.get("local"):    # queue ran out: play the related song that was lined up
        lt = _lineups.get(pid)
        if lt and not lt.done():                # it is being found right now: wait for it instead of searching twice
            try:
                await asyncio.wait_for(asyncio.shield(lt), 25)
            except Exception:
                pass
        if not q:                               # nothing lined up (autoplay just switched on, or the lookup failed)
            nxt = await find_autoplay(pid, last)
            if nxt:
                q.append(nxt)
    retries = 0
    while q:
        try:
            await start_track(pid)
            await send_card(pid, q[0])
            lineup_autoplay(pid)
            return
        except Exception as e:
            bad = q.pop(0)
            await bot.send_message(origins.get(pid, pid), f" Skipped `{bad['title']}`: {e}")
            if not q and autoplay.get(pid) and _is_auto(bad) and retries < 2:
                retries += 1                    # a broken autoplay song must not end the music: try another one
                history.setdefault(pid, []).append(bad)
                nxt = await find_autoplay(pid, bad)
                if nxt:
                    q.append(nxt)
    queues.pop(pid, None)
    history.pop(pid, None)
    try:
        await call.leave_call(pid)
    except Exception:
        pass
    await bot.send_message(
        origins.get(pid, pid),
        "<b>🎵 ǫᴜᴇᴜᴇ ꜰɪɴɪꜱʜᴇᴅ!</b>\n\n"
        "ɴᴏ ᴍᴏʀᴇ ꜱᴏɴɢꜱ ᴛᴏ ᴘʟᴀʏ. ᴜꜱᴇ /play ᴛᴏ ᴀᴅᴅ ᴍᴏʀᴇ ᴛʀᴀᴄᴋꜱ! 🎶",
        parse_mode=ParseMode.HTML,
    )


def target(m, channel):
    """Returns the chat id whose voice chat should be used (or None)."""
    if channel:
        return channels.get(str(m.chat.id))
    return m.chat.id


NO_CHANNEL = "ғɪʀѕᴛ ᴄσηηєᴄᴛ α ᴄнαηηєʟ ωɪᴛн `/playchannel <channel id or @username>`."


NO_VC_TEXT = ("🎙️ ɴᴏ ᴀᴄᴛɪᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ\n\n"
              "ɪ ᴄᴀɴ'ᴛ ᴊᴏɪɴ — ᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴀ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ғɪʀsᴛ.")


FETCH_FAIL_TEXT = "ꜰᴀɪʟᴇᴅ ᴛᴏ ꜰᴇᴛᴄʜ ᴛʀᴀᴄᴋ ᴅᴇᴛᴀɪʟs.\n\nᴛʀʏ ᴘʟᴀʏɪɴɢ ᴀɴʏ ᴏᴛʜᴇʀ."


def is_no_vc_error(e):
    """True when play failed only because no voice chat / video chat is running (the bot is not allowed to create one)."""
    blob = (type(e).__name__ + " " + str(e)).lower()
    return any(k in blob for k in ("creategroupcall", "noactivegroupcall", "no active group call",
                                   "groupcall_invalid", "groupcall_forbidden", "no active voice", "no active video"))


def play_fail_text(e, hint=""):
    """Text for a failed play: a clean 'no active voice chat' note when the VC is off, otherwise the real error."""
    if is_no_vc_error(e):
        return NO_VC_TEXT
    blob = str(e).lower()
    if any(k in blob for k in ("download failed", "api status", "yt-dlp", "empty file")):
        print("play failed (download):", e)                 # real reason stays in the logs only
        return FETCH_FAIL_TEXT
    return f" ᴄσυʟᴅ ησᴛ ᴘʟαʏ: {e}{hint}"


def uid(m):
    return m.from_user.id if m.from_user else 0


def user_link(u):
    """Markdown mention that never depends on the client's parse mode (no raw <a href> text)."""
    name = re.sub(r"[\[\]()`*_~|<>]", "", f"{u.first_name or ''} {u.last_name or ''}".strip()).strip() or "User"
    return f"[{name}](tg://user?id={u.id})"


def mention(m):
    return user_link(m.from_user) if m.from_user else "Anonymous"


def plain_name(m):
    """Display name without characters that could break Markdown links."""
    if not m.from_user:
        return "Anonymous"
    name = f"{m.from_user.first_name or ''} {m.from_user.last_name or ''}".strip()
    return re.sub(r"[\[\]()`*_~|]", "", name).strip() or "User"


# ---------- commands ----------
_username = None


async def bot_username():
    global _username
    if not _username:
        _username = (await bot.get_me()).username
    return _username


HELP_TEXT = (
    "<blockquote>💮 ᴅɪᴠᴇ ɪɴᴛᴏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅ ᴄᴀᴛᴇɢᴏʀɪᴇs ʙᴇʟᴏᴡ</blockquote>\n\n"
    "<blockquote>• ɢᴇᴛ ɢᴜɪᴅᴀɴᴄᴇ &amp; "
    f'<a href="{html.escape(SUPPORT_URL)}">sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ</a> ᴀssɪsᴛᴀɴᴄᴇ\n'
    "• ᴜsᴇ ᴄᴏᴍᴍᴀɴᴅs ᴡɪᴛʜ ᴛʜɪs sʏɴᴛᴀx ➜ /</blockquote>"
)


async def start_markup():
    uname = await bot_username()
    add_url = (f"https://t.me/{uname}?startgroup=true"
               "&admin=delete_messages+invite_users+pin_messages+manage_video_chats+restrict_members")
    mid = ([Btn("˹υᴘᴅᴧᴛє˼", BLUE, key="update", url=UPDATE_URL)] if UPDATE_URL else []) + [Btn("˹ѕυᴘᴘσʀᴛ˼", RED, key="support", url=SUPPORT_URL)]
    return IKM([
        [Btn(" ˹ᴧᴅᴅ ϻє ᴛσ ʏσυʀ ɢʀσυᴘ˼ ", GREEN, key="addme", url=add_url)],
        mid,                                                            # Update | Support
        [Btn("˹нєʟᴘ & ᴄσϻϻαηᴅѕ˼", BLUE, callback_data="help")],
    ])


async def edit_any(msg, text, markup, parse_mode=None):
    kw = {"parse_mode": parse_mode} if parse_mode else {}
    if msg.photo:
        await msg.edit_caption(text, reply_markup=markup, **kw)
    else:
        await msg.edit_text(text, reply_markup=markup, **NO_PREVIEW, **kw)


# ---------- fancy fonts (help page 2, /font and the group commands) ----------
_ABC = "abcdefghijklmnopqrstuvwxyz"
_F5 = dict(zip(_ABC, "αвᴄᴅєғɢнɪᴊᴋʟϻησᴘǫʀѕᴛυᴠωχʏᴢ"))            # the bot's own font  (ᴧ ᴊσɪη ʀєǫυєѕᴛ ɪѕ ᴘєηᴅɪηɢ)
_F2 = dict(zip(_ABC, "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"))            # ᴀ ʙ ᴄ ᴅ ᴇ ꜰ ɢ ...


def f5(text):
    """Bot font. Capital A becomes ᴧ (like ᴧᴅϻɪηѕ), everything else uses the normal bot letters."""
    out = []
    for part in re.split(r"(/\w+)", text):                 # /commands stay as they are
        if part.startswith("/"):
            out.append(part)
        else:
            out.append("".join("ᴧ" if c == "A" else _F5.get(c.lower(), c) for c in part))
    return "".join(out)


def _title_font(text, cap):
    """First letter of every word gets `cap`, the rest is small caps (Nᴏᴡ Uꜱᴇ Uꜱᴇʀʙᴏᴛ ...)."""
    out, start = [], True
    for c in text:
        if c.isspace():
            start = True
            out.append(c)
        elif c.isalpha():
            out.append(cap(c) if (start and c.isascii()) else _F2.get(c.lower(), c))
            start = False
        else:
            if c.isdigit():
                start = False
            out.append(c)
    return "".join(out)


def font4(text):
    return _title_font(text, lambda c: chr(0x1D400 + ord(c.upper()) - 65))      # 𝐍 𝐔 𝐅 ...


# ----- /play (or /vplay) as a reply to an audio / voice note / video / audio file -----
TG_DIR = os.path.join(DOWNLOAD_DIR, "tg")
TG_MAX_MB = int(os.getenv("TG_MAX_MB", "200"))          # bigger Telegram files are refused
_TG_EXT = {"voice": ".ogg", "audio": ".mp3", "video": ".mp4", "video_note": ".mp4", "animation": ".mp4"}


def replied_media(m):
    """(kind, media, message) when the command replies to something playable, else None."""
    r = m.reply_to_message
    if not r:
        return None
    for kind in ("audio", "voice", "video", "video_note", "animation", "document"):
        med = getattr(r, kind, None)
        if not med:
            continue
        if kind == "document":
            mime = (getattr(med, "mime_type", "") or "").lower()
            if not (mime.startswith(("audio/", "video/")) or mime == "application/ogg"):
                continue
        return kind, med, r
    return None


def _tg_cleanup():
    """Telegram files older than 6 hours go, unless they are still queued or in the ⏮️ history."""
    try:
        used = {t.get("local") for d in (queues, history) for lst in d.values() for t in lst}
        for f in os.listdir(TG_DIR):
            fp = os.path.join(TG_DIR, f)
            if fp not in used and time.time() - os.path.getmtime(fp) > 6 * 3600:
                os.remove(fp)
    except Exception:
        pass


async def tg_download(kind, med):
    os.makedirs(TG_DIR, exist_ok=True)
    _tg_cleanup()
    ext = os.path.splitext(getattr(med, "file_name", "") or "")[1] or _TG_EXT.get(kind, ".mp3")
    path = os.path.join(TG_DIR, f"{med.file_unique_id}{ext}")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    size = getattr(med, "file_size", 0) or 0
    if size > TG_MAX_MB * 1024 * 1024:
        raise RuntimeError(f"file is too big (max {TG_MAX_MB} MB)")
    out = await bot.download_media(med.file_id, file_name=path)
    out = out if isinstance(out, str) else path
    if not os.path.exists(out) or os.path.getsize(out) == 0:
        raise RuntimeError("download failed")
    return out


# ----- /end (was /stop) -----
END_TEXT = "➻ sᴛʀᴇᴀᴍ ᴇɴᴅᴇᴅ/sᴛᴏᴩᴩᴇᴅ 🎄\n│ \n└ʙʏ : {by}"
END_DELETE_AFTER = 5                                    # seconds until the note removes itself


async def end_stream(pid, chat_id, user):
    """Leaves the VC and clears the queue, then posts the 'stream ended' note (Close button + auto-delete)."""
    was_playing = bool(queues.get(pid))
    queues.pop(pid, None)
    history.pop(pid, None)
    try:
        await call.leave_call(pid)
        left = True
    except Exception:
        left = False                                    # the assistant was not in a call
    if not (was_playing or left):
        return await bot.send_message(chat_id, "ɴᴏᴛʜɪɴɢ ɪѕ ᴘʟαʏɪɴɢ.")
    if user:
        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "User"
        by = _mention_html(user.id, name)
    else:
        by = "Anonymous"
    markup = IKM([[Btn("ᴄʟσѕє", RED, callback_data=f"closemsg:{user.id if user else 0}")]])
    note = await bot.send_message(chat_id, END_TEXT.format(by=by), parse_mode=ParseMode.HTML, reply_markup=markup)
    task = asyncio.create_task(delete_after(note, END_DELETE_AFTER))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return note


# ----- auth (who may control playback) -----
NOT_AUTH = " σηʟʏ ɢʀσυᴘ αᴅϻɪηѕ σʀ αυᴛнσʀɪᴢєᴅ υѕєʀѕ ᴄαη ᴅσ ᴛнɪѕ.\nαѕᴋ αη αᴅϻɪη ᴛσ ʀυη `/auth` ғσʀ ʏσυ."


async def is_admin_id(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False


_admin_seen: dict = {}      # (chat_id, user_id) -> when they were last confirmed as admin


async def can_control_id(chat_id, user_id):
    """Bot owner, group admins/owner (auth or not) and /auth users may control playback."""
    if OWNER_ID and user_id == OWNER_ID:
        return True
    if str(user_id) in authed.get(str(chat_id), {}):
        return True
    t = _admin_seen.get((chat_id, user_id))
    if t and time.time() - t < 60:                          # confirmed admin a moment ago: skip the Telegram call
        return True
    ok = await is_admin_id(chat_id, user_id)
    if ok:
        _admin_seen[(chat_id, user_id)] = time.time()
    return ok


async def can_control(m):
    if not m.from_user:                                     # anonymous admin posts as the group itself
        return bool(m.sender_chat and m.sender_chat.id == m.chat.id)
    return await can_control_id(m.chat.id, m.from_user.id)


def clean_name(u):
    name = f"{u.first_name or ''} {u.last_name or ''}".strip()
    return re.sub(r"[\[\]()`*_~|]", "", name).strip() or "User"


async def resolve_target(m):
    """User to (un)auth: the replied-to user, or an @username / user id given as argument."""
    if m.reply_to_message and m.reply_to_message.from_user:
        return m.reply_to_message.from_user
    if len(m.command) > 1:
        arg = m.command[1]
        arg = int(arg) if arg.lstrip("-").isdigit() else arg
        try:
            return await bot.get_users(arg)
        except Exception:
            return None
    return None


def disp_name(u):
    return f"{u.first_name or ''} {u.last_name or ''}".strip() or "User"


_bg_tasks = set()


async def delete_after(msg, seconds):
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except Exception:
        pass


async def is_group_admin(m):
    """Bot owner, group owner or group admin (also anonymous admins)."""
    if m.from_user and OWNER_ID and m.from_user.id == OWNER_ID:
        return True
    if m.sender_chat and m.sender_chat.id == m.chat.id:     # anonymous admin
        return True
    if not m.from_user:
        return False
    try:
        member = await bot.get_chat_member(m.chat.id, m.from_user.id)
        return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False


# ----- owner -----
def is_owner(m):
    return bool(OWNER_ID) and m.from_user and m.from_user.id == OWNER_ID


def is_sudo_id(user_id):
    return str(user_id) in sudoers


def is_owner_or_sudo(m):
    """Bot owner or a sudo user. Used ONLY by /broadcast, /auth, /unauth and /stats."""
    return bool(m.from_user) and (is_owner(m) or is_sudo_id(m.from_user.id))


LEAVE_TEXT = (
    "😊 𝐈ᴛ 𝐖ᴀꜱ 𝐍ɪᴄᴇ 𝐌ᴇᴇᴛɪɴɢ 𝐘ᴏᴜ 𝐀ʟʟ!\n"
    "❤️‍🩹 𝐈'ᴍ 𝐋ᴇᴀᴠɪɴɢ 𝐍ᴏᴡ.\n"
    "💕 𝐈ꜰ 𝐘ᴏᴜ 𝐖ᴀɴᴛ 𝐓ᴏ 𝐋ɪꜱᴛᴇɴ 𝐓ᴏ 𝐍ᴏɴꜱᴛᴏᴘ 𝐒ᴏɴɢꜱ 𝐀ɢᴀɪɴ, 𝐉ᴜꜱᴛ 𝐀ᴅᴅ 𝐌ᴇ 𝐁ᴀᴄᴋ. ❤️🎶"
)


# ----- picture helpers (used by the welcome picture) -----
# Needs Pillow (pip install pillow); without it the bot sends the text only.
try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    Image = None


# --- picture (PIL) ---
def _avatar(path, name, size=437):
    """Square avatar: the profile photo, or a coloured square with the first letter."""
    if path:
        try:
            return ImageOps.fit(Image.open(path).convert("RGB"), (size, size))
        except Exception:
            pass
    img = Image.new("RGB", (size, size), (random.randint(90, 200), random.randint(60, 160), random.randint(110, 200)))
    try:
        font = ImageFont.load_default(size=220)
        ImageDraw.Draw(img).text((size // 2, size // 2), (name or "?")[:1].upper(), fill="white", anchor="mm", font=font)
    except Exception:
        pass
    return img
# --- end picture ---


async def _profile_pic(user_id, out):
    try:
        chat = await bot.get_chat(user_id)
        if chat.photo:
            return await bot.download_media(chat.photo.big_file_id, file_name=out)
    except Exception:
        pass
    return None


# ----- group management: /pin /pinned /unpin /settitle /setdiscription /setphoto /removephoto /zombies /imposter -----
# (/staff is the same list as /adminlist, /bots is further up)
HTML = ParseMode.HTML


async def has_right(m, right=None):
    """Bot owner, group owner, anonymous admin, or an admin that has the given right (None = any admin)."""
    if m.from_user is None:
        return bool(m.sender_chat and m.sender_chat.id == m.chat.id)
    if OWNER_ID and m.from_user.id == OWNER_ID:
        return True
    try:
        mem = await bot.get_chat_member(m.chat.id, m.from_user.id)
    except Exception:
        return False
    if mem.status == ChatMemberStatus.OWNER:
        return True
    if mem.status != ChatMemberStatus.ADMINISTRATOR:
        return False
    return right is None or bool(mem.privileges and getattr(mem.privileges, right, False))


async def deny(m):
    await m.reply_text("🔒 " + f5("You don't have the required admin right for this."), parse_mode=HTML)


async def fail(m, e):
    if isinstance(e, ChatAdminRequired):
        txt = f5("I need the required admin right for this. Please promote me first.")
    else:
        txt = html.escape(str(e))[:200]
    await m.reply_text("❌ " + txt, parse_mode=HTML)
