from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- seek -----
@bot.on_message(filters.command(["seek", "cseek", "seekback", "cseekback"]) & filters.group)
async def seek(_, m):
    if not await can_control(m):
        return await m.reply_text(NOT_AUTH)
    name = m.command[0].lower()
    channel = name.startswith("c")
    back = name.endswith("back")
    if len(m.command) < 2 or not m.command[1].isdigit() or int(m.command[1]) <= 0:
        return await m.reply_text(f"Usage: `/{name} [seconds]`\nExample: `/{name} 20` = {'ɢᴏ ʙᴀᴄᴋ' if back else 'ꜱᴋɪᴘ ꜰᴏʀᴡᴀʀᴅ'} 20 ꜱᴇᴄᴏɴᴅꜱ.")
    pid = target(m, channel)
    if not pid:
        return await m.reply_text(NO_CHANNEL)
    q = queues.get(pid)
    if not q:
        return await m.reply_text("ɴᴏᴛʜɪɴɢ ɪꜱ ᴘʟᴀʏɪɴɢ.")
    track, step = q[0], int(m.command[1])
    pos = int(track_pos(track))
    new = max(0, pos - step) if back else pos + step
    dur = int(track.get("duration") or 0)
    if not back and dur and new >= dur - 2:
        return await m.reply_text(
            f" ᴄᴀɴ'ᴛ ꜱᴇᴇᴋ ᴛʜᴀᴛ ꜰᴀʀ. ᴄᴜʀʀᴇɴᴛʟʏ ᴀᴛ `{fmt(pos, dur)}` / `{fmt(dur)}`, ʏᴏᴜ ᴄᴀɴ ꜱᴇᴇᴋ ᴀᴛ ᴍᴏꜱᴛ `{max(dur - 3 - pos, 0)}s` ᴀʜᴇᴀᴅ.")
    try:
        await start_track(pid, offset=new)
    except Exception as e:
        return await m.reply_text(f" ꜱᴇᴇᴋ ꜰᴀɪʟᴇᴅ: {e}")
    await m.reply_text(
        "» sᴛʀᴇᴀᴍ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴇᴇᴋᴇᴅ.\n\n"
        f"ᴅᴜʀᴀᴛɪᴏɴ : `{fmt(new, dur)}`\n"
        f"ʙʏ : {mention(m)}",
        reply_markup=IKM([[Btn("ᴄʟᴏsᴇ", RED, callback_data=f"closemsg:{uid(m)}")]]))
