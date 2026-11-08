from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


@bot.on_message(filters.command("leave"))
async def leave_cmd(_, m):
    """Owner only: /leave <chat id> (or just /leave inside a group) -> goodbye message, then the bot leaves."""
    if not is_owner(m):
        return
    if len(m.command) > 1:
        arg = m.command[1]
    elif m.chat.type != ChatType.PRIVATE:
        arg = str(m.chat.id)
    else:
        arg = ""
    if not re.fullmatch(r"-?\d+", arg) or int(arg) >= 0:
        return await m.reply_text("υѕαɢє: `/leave <chat id>`\nᴇxᴀᴍᴘʟᴇ: `/leave -1001234567890`")
    cid = int(arg)
    title = arg
    try:
        chat = await bot.get_chat(cid)
        title = chat.title or arg
    except Exception:
        pass
    try:
        uname = await bot_username()
        markup = IKM([[Btn("𝐀ᴅᴅ 𝐌ᴇ 𝐈ɴ 𝐆ʀᴏᴜᴘ", GREEN, key="addme", url=f"https://t.me/{uname}?startgroup=true")]])
        await bot.send_message(cid, LEAVE_TEXT, reply_markup=markup)
    except Exception as e:
        print("leave: goodbye message failed:", e)
    try:                                                    # stop the music + forget this chat
        await call.leave_call(cid)
    except Exception:
        pass
    reset_chat_state(cid)
    try:
        await bot.leave_chat(cid)
    except Exception as e:
        return await m.reply_text(f"❌ ᴄᴏᴜʟᴅ ɴᴏᴛ ʟᴇᴀᴠᴇ **{title}** (`{cid}`)\n`{e}`")
    try:                                                    # the assistant account leaves too
        await assistant.leave_chat(cid)
    except Exception:
        pass
    known["chats"].discard(cid)
    save_known()
    await m.reply_text(f"✅ ʟᴇғᴛ **{title}** (`{cid}`)")
