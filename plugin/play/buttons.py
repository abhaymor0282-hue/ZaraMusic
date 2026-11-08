from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- inline buttons -----
@bot.on_callback_query(filters.regex(r"\|"))
async def buttons(_, cq):
    action, pid = cq.data.split("|")
    pid = int(pid)
    if action in ("pause", "resume", "skip", "stop", "close") and \
            not await can_control_id(cq.message.chat.id, cq.from_user.id):
        return await cq.answer("🔒 ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴꜱ ᴏʀ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜꜱᴇʀꜱ ᴄᴀɴ ᴅᴏ ᴛʜɪꜱ.", show_alert=True)
    try:
        if action == "pause":
            await vc_pause(pid)
            mark_pause(pid)
        elif action == "resume":
            await vc_resume(pid)
            mark_resume(pid)
        elif action == "skip":
            await cq.answer()                   # stop the button spinner at once; the new card follows
            await next_track(pid, force=True)
            return
        elif action == "close":                 # Close button: just remove this card
            await cq.answer()
            try:
                await cq.message.delete()
            except Exception:
                pass
            return
        elif action == "stop":                  # ▢ button: same as /end
            await cq.answer()
            await end_stream(pid, cq.message.chat.id, cq.from_user)
            return
        elif action == "autoplay":
            q = queues.get(pid, [])
            if not q:
                return await cq.answer("ɴᴏᴛʜɪɴɢ ɪꜱ ᴘʟᴀʏɪɴɢ.", show_alert=True)
            autoplay[pid] = not autoplay.get(pid, False)
            note = "ᴀᴜᴛᴏᴘʟᴀʏ ᴏꜰꜰ"
            if autoplay[pid]:
                note = "ᴀᴜᴛᴏᴘʟᴀʏ ᴏɴ ✓\nꜱɪᴍɪʟᴀʀ ꜱᴏɴɢꜱ ᴡɪʟʟ ᴘʟᴀʏ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴡʜᴇɴ ᴛʜᴇ ǫᴜᴇᴜᴇ ᴇɴᴅꜱ."
                if len(q) == 1:                 # start right away: line up the next song now
                    nxt = await find_autoplay(pid, q[0])
                    if nxt and len(q) == 1:
                        q.append(nxt)
                        note = f"ᴀᴜᴛᴏᴘʟᴀʏ ᴏɴ ✓\nɴᴇxᴛ ꜱᴏɴɢ: {nxt['title']}"[:190]
            await cq.message.edit_reply_markup(panel(pid))
            return await cq.answer(note, show_alert=True)
        await cq.answer()
    except Exception as e:
        await cq.answer(str(e)[:150], show_alert=True)


@call.on_update(fl.stream_end())
async def on_end(_, update):
    await next_track(update.chat_id)


# Voice chat ended (admin closed it) or the assistant was removed: forget the old queue of that chat.
# LEFT_CALL is NOT used on purpose: /end and "queue finished" leave the call themselves.
try:
    from pytgcalls.types import ChatUpdate as _CU
    _S = _CU.Status
    _END_FLAGS = None
    for _n in ("CLOSED_VOICE_CHAT", "DISCARDED_CALL", "KICKED"):
        _f = getattr(_S, _n, None)
        if _f is not None:
            _END_FLAGS = _f if _END_FLAGS is None else (_END_FLAGS | _f)

    if _END_FLAGS is not None:
        @call.on_update(fl.chat_update(_END_FLAGS))
        async def on_vc_end(_, update):
            pid = update.chat_id
            if pid in queues:
                reset_chat_state(pid)
                try:
                    await call.leave_call(pid)          # clean pytgcalls' own state too (may already be gone)
                except Exception:
                    pass
except Exception as e:
    print("VC-end detection not available in this pytgcalls version:", e)
