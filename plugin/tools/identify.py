from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ======================================================================
# /identify  (which song is this?)
# ======================================================================
import difflib

# ---------------------------------------------------------------- /identify
# Reply to a song / voice note / video with /identify -> the bot listens to ~20 s of it (Shazam)
# and shows the title + artist, with a Play button (group chats).
# Needs:  pip install shazamio   (ffmpeg is already needed by the music player)
try:
    from shazamio import Shazam as _ShazamCls
except Exception as _e:
    print("shazamio import failed (/identify is off):", type(_e).__name__, _e)
    _ShazamCls = None

IDENT_MAX_MB = int(os.getenv("IDENT_MAX_MB", "50"))      # bigger files are refused
IDENT_COOLDOWN = 20                                       # seconds between two /identify of the same user
_IDENT_SEM = asyncio.Semaphore(2)                         # at most 2 recognitions at the same time
_IDENT_LAST: dict = {}                                    # user id -> time of the last /identify
_IDENT_RESULTS: dict = {}                                 # token -> {"q": "title artist"}  (for the Play button)
_shazam = None


async def _ident_clip(src, dur):
    """A ~20 s mono wav cut from the middle of the file: Shazam only needs a short, clean sample."""
    out = f"{src}.{random.getrandbits(24):x}.wav"
    start = max(0, int(dur) // 2 - 10) if dur and dur > 40 else 0
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-ss", str(start), "-i", src, "-t", "20", "-vn", "-ac", "1", "-ar", "16000", out,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        await asyncio.wait_for(proc.wait(), 60)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("audio conversion timed out")
    if proc.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
        raise RuntimeError("could not read this audio")
    return out


async def _shazam_lookup(path):
    """{"title", "artist", "url", "cover"} or None when Shazam does not know the song."""
    global _shazam
    if _shazam is None:
        _shazam = _ShazamCls()
    fn = getattr(_shazam, "recognize", None) or getattr(_shazam, "recognize_song")   # name changed between versions
    out = await asyncio.wait_for(fn(path), 45)
    tr = (out or {}).get("track")
    if not tr:
        return None
    return {"title": tr.get("title") or "Unknown", "artist": tr.get("subtitle") or "",
            "url": tr.get("url") or "", "cover": (tr.get("images") or {}).get("coverart") or ""}


@bot.on_message(filters.command("identify"))
async def identify_cmd(_, m):
    media = replied_media(m)
    if not media:
        return await m.reply_text(f5("Reply to a song, voice note or video with /identify to find its name."))
    if _ShazamCls is None:
        return await m.reply_text("❌ /identify is not set up yet. Owner: run  pip install shazamio  and restart.")
    u = m.from_user.id if m.from_user else 0
    wait = IDENT_COOLDOWN - (time.time() - _IDENT_LAST.get(u, 0))
    if wait > 0:
        return await m.reply_text(f"⏳ {f5('Wait')} {int(wait) + 1}s")
    _IDENT_LAST[u] = time.time()
    kind, med, _r = media
    if (getattr(med, "file_size", 0) or 0) > IDENT_MAX_MB * 1024 * 1024:
        return await m.reply_text(f"❌ File is too big (max {IDENT_MAX_MB} MB).")
    msg = await m.reply_text("🎧 " + f5("Listening..."))
    clip = None
    try:
        async with _IDENT_SEM:
            path = await asyncio.wait_for(tg_download(kind, med), 180)
            try:
                clip = await _ident_clip(path, int(getattr(med, "duration", 0) or 0))
            except Exception as e:                       # no ffmpeg / odd file: let Shazam try the original
                print("identify: clip failed, using the original file:", e)
                clip = None
            found = await _shazam_lookup(clip or path)
    except Exception as e:
        return await msg.edit_text(f"❌ Could not identify: {str(e)[:150]}")
    finally:
        if clip:
            try:
                os.remove(clip)
            except OSError:
                pass
    if not found:
        return await msg.edit_text("😕 " + f5("Could not recognise this song. Try a clearer 10-20 second part."))

    q = f"{found['title']} {found['artist']}".strip()
    tok = f"{random.getrandbits(32):x}"
    if len(_IDENT_RESULTS) > 300:
        _IDENT_RESULTS.clear()
    _IDENT_RESULTS[tok] = {"q": q}
    text = f"🎧 <b>{f5('Song identified')}</b>\n\n🎵 <b>{html.escape(found['title'])}</b>\n"
    if found["artist"]:
        text += f"👤 {html.escape(found['artist'])}\n"
    text += f"\n<code>/play {html.escape(q)}</code>"
    rows = []
    if m.chat.type != ChatType.PRIVATE:
        rows.append([Btn("▶️ " + f5("Play"), GREEN, callback_data=f"idplay:{tok}")])
    if found["url"].startswith("http"):
        rows.append([Btn("🎼 Shazam", BLUE, key="shazam", url=found["url"])])
    markup = IKM(rows) if rows else None
    sent = False
    if found["cover"].startswith("http"):
        try:
            await m.reply_photo(found["cover"], caption=text, parse_mode=HTML, reply_markup=markup)
            sent = True
        except Exception:
            pass
    if not sent:
        await m.reply_text(text, parse_mode=HTML, reply_markup=markup, **NO_PREVIEW)
    try:
        await msg.delete()
    except Exception:
        pass


@bot.on_callback_query(filters.regex(r"^idplay:[0-9a-f]+$"))
async def identify_play(_, cq):
    info = _IDENT_RESULTS.get(cq.data.split(":", 1)[1])
    if not info:
        return await cq.answer("This button expired. Use /play <song name>.", show_alert=True)
    msg = cq.message
    if msg.chat.type == ChatType.PRIVATE:
        return await cq.answer("Use this in a group with a voice chat.", show_alert=True)
    await cq.answer("🔎 Searching...")
    user = cq.from_user
    name = re.sub(r"[\[\]()`*_~|]", "", f"{user.first_name or ''} {user.last_name or ''}".strip()).strip() or "User"
    note = await msg.reply_text("💗")
    try:
        meta = await asyncio.get_running_loop().run_in_executor(None, search, info["q"])
        track = dict(meta, video=False, channel=False, by=user_link(user), by_id=user.id, by_name=name)
        pos = await add_to_queue(msg.chat.id, msg.chat.id, track)
    except AssistantBanned:
        return await reply_banned(note, msg.chat.id)
    except Exception as e:
        return await note.edit_text(NO_VC_TEXT if is_no_vc_error(e) else f"❌ Could not play: {e}\nIs the VC on in this group? Is the assistant in the group?")
    if pos == 0:
        await note.delete()                                  # first song: the Streaming card is already sent
    else:
        await note.edit_text(queued_card(track, pos), parse_mode=HTML,
                             reply_markup=IKM([[Btn("ᴄʟσѕє", RED, callback_data=f"closemsg:{user.id}")]]))
