from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


@bot.on_callback_query(filters.regex(r"^closemsg:"))
async def close_msg(_, cq):
    """Close button: the person who ran the command, a group admin or the bot owner can delete the message."""
    ok = cq.from_user.id in (int(cq.data.split(":")[1]), OWNER_ID)
    if not ok:
        try:
            member = await bot.get_chat_member(cq.message.chat.id, cq.from_user.id)
            ok = member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
        except Exception:
            ok = False
    if not ok:
        return await cq.answer("ᴏɴʟʏ ᴛʜᴇ ᴘᴇʀꜱᴏɴ ᴡʜᴏ ʀᴀɴ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ ᴏʀ ᴀɴ ᴀᴅᴍɪɴ ᴄᴀɴ ᴄʟᴏꜱᴇ ᴛʜɪꜱ.", show_alert=True)
    chat_id = cq.message.chat.id
    try:
        await cq.message.delete()
    except Exception:
        return await cq.answer()
    note = await bot.send_message(chat_id, f"**ᴄʟᴏꜱᴇ ʙʏ :-** {user_link(cq.from_user)}")
    task = asyncio.create_task(delete_after(note, 3))      # the "close by" note removes itself after 3 seconds
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
