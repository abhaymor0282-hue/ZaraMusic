from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- /autoplay panel + /askip -----
def autoplay_panel_text(pid):
    on = autoplay.get(pid, False)
    q = queues.get(pid, [])
    now = html.escape(q[0]["title"]) if q else "ɴᴏᴛʜɪɴɢ"
    return (
        "<u>⊚ ᴀᴜᴛᴏᴘʟᴀʏ sᴇᴛᴛɪɴɢs :</u>\n\n"
        f"<blockquote>sᴛᴀᴛᴜs : <b>{'ᴏɴ ✓' if on else 'ᴏғғ'}</b>\n"
        f"ɴᴏᴡ ᴘʟᴀʏɪɴɢ : {now}</blockquote>\n\n"
        "<blockquote>💮 ᴀᴜᴛᴏᴘʟᴀʏ sᴇᴀᴍʟᴇssʟʏ ᴀᴅᴅs ʀᴇʟᴀᴛᴇᴅ ᴛʀᴀᴄᴋs ᴛᴏ ᴛʜᴇ ǫᴜᴇᴜᴇ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ "
        "ᴄᴜʀʀᴇɴᴛ ᴘʟᴀʏʟɪsᴛ ғᴏʀ ɴᴏɴ-sᴛᴏᴘ ᴍᴜsɪᴄ.</blockquote>\n\n"
        "<u>๏ ɴᴏᴛᴇ : ʀᴇǫᴜɪʀᴇs ᴀᴛ ʟᴇᴀsᴛ ᴏɴᴇ ᴀᴄᴛɪᴠᴇ sᴏɴɢ ᴛᴏ ғᴜɴᴄᴛɪᴏɴ.</u>"
    )


def autoplay_panel_markup(pid):
    on = autoplay.get(pid, False)
    return IKM([
        [Btn("ᴇɴᴀʙʟᴇ ✓" if on else "ᴇɴᴀʙʟᴇ", GREEN, key="apanel_on", callback_data=f"apanel:enable:{pid}"),
         Btn("ᴅɪsᴀʙʟᴇ" if on else "ᴅɪsᴀʙʟᴇ ✓", RED, key="apanel_off", callback_data=f"apanel:disable:{pid}")],
        [Btn("ᴄʟᴏsᴇ", BLUE, key="apanel_close", callback_data=f"apanel:close:{pid}")],
    ])


@bot.on_message(filters.command("autoplay") & filters.group)
async def autoplay_cmd(_, m):
    pid = m.chat.id
    await m.reply_text(autoplay_panel_text(pid), reply_markup=autoplay_panel_markup(pid),
                       parse_mode=ParseMode.HTML, **NO_PREVIEW)


@bot.on_callback_query(filters.regex(r"^apanel:(enable|disable|close):-?\d+$"))
async def autoplay_panel_button(_, cq):
    _, act, pid_s = cq.data.split(":")
    pid = int(pid_s)
    if act == "close":
        try:
            await cq.message.delete()
        except Exception:
            pass
        return await cq.answer()
    q = queues.get(pid, [])
    note = ""
    if act == "enable":
        if not q:
            return await cq.answer("ɴᴏᴛʜɪɴɢ ɪs ᴘʟᴀʏɪɴɢ. ᴘʟᴀʏ ᴀ sᴏɴɢ ғɪʀsᴛ.", show_alert=True)
        autoplay[pid] = True
        note = "ᴀᴜᴛᴏᴘʟᴀʏ ᴏɴ ✓"
        if len(q) == 1:                                     # line up the next song right away
            nxt = await find_autoplay(pid, q[0])
            if nxt and len(q) == 1:
                q.append(nxt)
                note = f"ᴀᴜᴛᴏᴘʟᴀʏ ᴏɴ ✓\nɴᴇxᴛ sᴏɴɢ: {nxt['title']}"[:190]
    else:
        autoplay[pid] = False
        note = "ᴀᴜᴛᴏᴘʟᴀʏ ᴏғғ"
    try:
        await edit_any(cq.message, autoplay_panel_text(pid), autoplay_panel_markup(pid), ParseMode.HTML)
    except Exception:
        pass
    await cq.answer(note, show_alert=True)


@bot.on_message(filters.command("askip") & filters.group)
async def askip_cmd(_, m):
    if not await can_control(m):
        return await m.reply_text(NOT_AUTH)
    pid = m.chat.id
    q = queues.get(pid, [])
    if not q:
        return await m.reply_text("ɴᴏᴛʜɪɴɢ ɪs ᴘʟᴀʏɪɴɢ ʀɪɢʜᴛ ɴᴏᴡ.")
    if not autoplay.get(pid):
        return await m.reply_text("ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴏғғ. ᴜsᴇ `/autoplay` ᴛᴏ ᴇɴᴀʙʟᴇ ɪᴛ ғɪʀsᴛ.")
    try:
        if len(q) == 1:                                     # nothing lined up yet: finding a related song takes a moment
            await m.reply_text("🔍 ꜰɪɴᴅɪɴɢ ᴛʜᴇ ɴᴇxᴛ ᴀᴜᴛᴏᴘʟᴀʏ ᴛʀᴀᴄᴋ...")
        await next_track(pid, force=True)
    except Exception as e:
        await m.reply_text(f"❌ {e}")
