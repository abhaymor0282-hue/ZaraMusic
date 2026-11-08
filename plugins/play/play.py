from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


def tg_title(kind, med):
    t = getattr(med, "title", None)
    if t:
        perf = getattr(med, "performer", None)
        return f"{perf} - {t}" if perf else t
    name = os.path.splitext(getattr(med, "file_name", "") or "")[0]
    return name or {"voice": "Voice note", "video_note": "Video message", "video": "Video",
                    "animation": "Video"}.get(kind, "Telegram audio")


async def play_telegram_media(m, media, channel, want_video, force=False):
    kind, med, r = media
    pid = target(m, channel)
    if not pid:
        return await m.reply_text(NO_CHANNEL)
    mime = (getattr(med, "mime_type", "") or "").lower()
    is_video = kind in ("video", "video_note", "animation") or mime.startswith("video/")
    video = bool(want_video and is_video)                   # /vplay on a voice note or song = audio only
    msg = await m.reply_text("💗")
    join_f = asyncio.ensure_future(ensure_assistant(pid))   # the assistant joins while the file downloads
    try:
        path = await tg_download(kind, med)
    except Exception as e:
        join_f.cancel()
        return await msg.edit_text(f" ᴄσυʟᴅ ησᴛ ᴅσωηʟσαᴅ: {e}")
    try:
        await join_f
    except AssistantBanned:
        return await reply_banned(msg, pid)
    except Exception as e:
        return await msg.edit_text(play_fail_text(e))
    track = {"title": tg_title(kind, med), "duration": int(getattr(med, "duration", 0) or 0), "thumb": None,
             "link": getattr(r, "link", None) or "", "local": path, "video": video, "channel": channel,
             "by": mention(m), "by_id": uid(m), "by_name": plain_name(m)}
    try:
        pos = await (force_play if force else add_to_queue)(m.chat.id, pid, track)
    except AssistantBanned:
        return await reply_banned(msg, pid)
    except Exception as e:
        hint = "\nɪѕ ᴛнє ᴠᴄ ση ɪη ᴛнє ᴄнαηηєʟ? ɪѕ ᴛнє αѕѕɪѕᴛαηᴛ αη αᴅϻɪη?" if channel else "\nɪѕ ᴛнє ᴠᴄ ση ɪη ᴛнє ɢʀσυᴘ? ɪѕ ᴛнє αѕѕɪѕᴛαηᴛ ɪη ᴛнє ɢʀσυᴘ?"
        return await msg.edit_text(play_fail_text(e, hint))
    try:
        await msg.delete()
    except Exception:
        pass
    if pos:                                                 # queued behind another song
        markup = IKM([[Btn("ᴄʟσѕє", RED, callback_data=f"closemsg:{uid(m)}")]])
        await m.reply_text(queued_card(track, pos), parse_mode=ParseMode.HTML, reply_markup=markup)


@bot.on_message(filters.command(["play", "cplay", "vplay", "vcplay"]) & filters.group)
async def play(_, m):
    name = m.command[0].lower()
    channel = name in ("cplay", "vcplay")
    video = name in ("vplay", "vcplay")
    if len(m.command) < 2:
        media = replied_media(m)
        if media:                                           # /play as a reply to an audio / voice note / video
            return await play_telegram_media(m, media, channel, video)
        return await m.reply_text(f"υѕαɢє: /{name} <ѕσηɢ ηαϻє σʀ ʟɪηᴋ>\nσʀ ʀєᴘʟʏ ᴛσ αη ᴀυᴅɪσ / ᴠσɪᴄє / ᴠɪᴅєσ ωɪᴛн /{name}")
    pid = target(m, channel)
    if not pid:
        return await m.reply_text(NO_CHANNEL)
    query = " ".join(m.command[1:])
    loop = asyncio.get_running_loop()
    msg_f = asyncio.ensure_future(m.reply_text("💗"))            # the placeholder is sent while the search already runs
    join_f = asyncio.ensure_future(ensure_assistant(pid))       # join check runs while we search
    search_f = loop.run_in_executor(None, search, query)
    lid = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", query)
    if lid:                                                     # a link: the download starts before the lookup finishes
        prefetch(f"https://www.youtube.com/watch?v={lid.group(1)}", video)
    try:
        meta = await search_f
    except Exception as e:
        join_f.cancel()
        msg = await msg_f
        return await msg.edit_text(f" Not found: {e}")
    prefetch(meta["link"], video)                               # download starts NOW, while the VC join is still running
    msg = await msg_f
    try:
        await join_f
    except AssistantBanned:
        return await reply_banned(msg, pid)
    except Exception as e:
        return await msg.edit_text(play_fail_text(e))
    track = dict(meta, video=video, channel=channel, by=mention(m), by_id=uid(m), by_name=plain_name(m))
    try:
        pos = await add_to_queue(m.chat.id, pid, track)
    except AssistantBanned:
        return await reply_banned(msg, pid)
    except Exception as e:
        hint = "\nɪѕ ᴛнє ᴠᴄ ση ɪη ᴛнє ᴄнαηηєʟ? ɪѕ ᴛнє αѕѕɪѕᴛαηᴛ αη αᴅϻɪη?" if channel else "\nɪѕ ᴛнє ᴠᴄ ση ɪη ᴛнє ɢʀσυᴘ? ɪѕ ᴛнє αѕѕɪѕᴛαηᴛ ɪη ᴛнє ɢʀσυᴘ?"
        return await msg.edit_text(play_fail_text(e, hint))
    if pos == 0:
        await msg.delete()                      # first song: the Streaming card is already sent by send_card
    else:
        try:
            await msg.delete()
        except Exception:
            pass
        text = queued_card(track, pos)
        markup = IKM([[Btn("ᴄʟσѕє", RED, callback_data=f"closemsg:{uid(m)}")]])
        await m.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)      # text only, no picture


@bot.on_message(filters.command(["forceplay", "cforceplay", "vforceplay", "vcforceplay"]) & filters.group)
async def forceplay(_, m):
    name = m.command[0].lower()
    channel = name in ("cforceplay", "vcforceplay")
    video = name in ("vforceplay", "vcforceplay")
    if not await can_control(m):
        return await m.reply_text(NOT_AUTH)
    if len(m.command) < 2:
        media = replied_media(m)
        if media:
            return await play_telegram_media(m, media, channel, video, force=True)
        return await m.reply_text(f"υѕαɢє: /{name} <ѕσηɢ ηαϻє σʀ ʟɪηᴋ>\nσʀ ʀєᴘʟʏ ᴛσ αη ᴀυᴅɪσ / ᴠσɪᴄє / ᴠɪᴅєσ ωɪᴛн /{name}")
    pid = target(m, channel)
    if not pid:
        return await m.reply_text(NO_CHANNEL)
    query = " ".join(m.command[1:])
    loop = asyncio.get_running_loop()
    msg_f = asyncio.ensure_future(m.reply_text("💗"))
    join_f = asyncio.ensure_future(ensure_assistant(pid))
    search_f = loop.run_in_executor(None, search, query)
    lid = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", query)
    if lid:
        prefetch(f"https://www.youtube.com/watch?v={lid.group(1)}", video)
    try:
        meta = await search_f
    except Exception as e:
        join_f.cancel()
        msg = await msg_f
        return await msg.edit_text(f" Not found: {e}")
    prefetch(meta["link"], video)
    msg = await msg_f
    try:
        await join_f
    except AssistantBanned:
        return await reply_banned(msg, pid)
    except Exception as e:
        return await msg.edit_text(play_fail_text(e))
    track = dict(meta, video=video, channel=channel, by=mention(m), by_id=uid(m), by_name=plain_name(m))
    try:
        await force_play(m.chat.id, pid, track)
    except AssistantBanned:
        return await reply_banned(msg, pid)
    except Exception as e:
        return await msg.edit_text(play_fail_text(e))
    try:
        await msg.delete()                      # the Streaming card was already sent by send_card
    except Exception:
        pass

@bot.on_message(filters.command(["playforce", "cplayforce", "vplayforce", "vcplayforce"]) & filters.group)
async def forceplay(_, m):
    name = m.command[0].lower()
    channel = name in ("cplayforce", "vcplayforce")
    video = name in ("vplayforce", "vcplayforce")
    if not await can_control(m):
        return await m.reply_text(NOT_AUTH)
    if len(m.command) < 2:
        media = replied_media(m)
        if media:
            return await play_telegram_media(m, media, channel, video, force=True)
        return await m.reply_text(f"υѕαɢє: /{name} <ѕσηɢ ηαϻє σʀ ʟɪηᴋ>\nσʀ ʀєᴘʟʏ ᴛσ αη ᴀυᴅɪσ / ᴠσɪᴄє / ᴠɪᴅєσ ωɪᴛн /{name}")
    pid = target(m, channel)
    if not pid:
        return await m.reply_text(NO_CHANNEL)
    query = " ".join(m.command[1:])
    loop = asyncio.get_running_loop()
    msg_f = asyncio.ensure_future(m.reply_text("💗"))
    join_f = asyncio.ensure_future(ensure_assistant(pid))
    search_f = loop.run_in_executor(None, search, query)
    lid = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", query)
    if lid:
        prefetch(f"https://www.youtube.com/watch?v={lid.group(1)}", video)
    try:
        meta = await search_f
    except Exception as e:
        join_f.cancel()
        msg = await msg_f
        return await msg.edit_text(f" Not found: {e}")
    prefetch(meta["link"], video)
    msg = await msg_f
    try:
        await join_f
    except AssistantBanned:
        return await reply_banned(msg, pid)
    except Exception as e:
        return await msg.edit_text(play_fail_text(e))
    track = dict(meta, video=video, channel=channel, by=mention(m), by_id=uid(m), by_name=plain_name(m))
    try:
        await force_play(m.chat.id, pid, track)
    except AssistantBanned:
        return await reply_banned(msg, pid)
    except Exception as e:
        return await msg.edit_text(play_fail_text(e))
    try:
        await msg.delete()                      # the Streaming card was already sent by send_card
    except Exception:
        pass
        