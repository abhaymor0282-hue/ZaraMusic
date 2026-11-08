from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- controls (/pause + /cpause etc.) -----
BASE = ["pause", "resume", "skip", "end", "stop", "loop", "queue"]      # /stop = /end
CONTROLS = BASE + ["c" + b for b in BASE]


@bot.on_message(filters.command(CONTROLS) & filters.group)
async def controls(_, m):
    name = m.command[0].lower()
    channel = name.startswith("c") and name[1:] in BASE
    action = name[1:] if channel else name
    if action != "queue" and not await can_control(m):      # /queue is open to everyone
        return await m.reply_text(NOT_AUTH)
    pid = target(m, channel)
    if not pid:
        return await m.reply_text(NO_CHANNEL)
    try:
        if action == "pause":
            await vc_pause(pid); mark_pause(pid); await m.reply_text(" ʀυηηɪηɢ ѕσηɢ ɪѕ ᴘαυѕєᴅ")
        elif action == "resume":
            await vc_resume(pid); mark_resume(pid); await m.reply_text(" ᴛнє ᴘαυѕє ѕσηɢ ɪѕ ʀєѕυϻєᴅ")
        elif action == "skip":
            await next_track(pid, force=True)
        elif action in ("end", "stop"):
            await end_stream(pid, m.chat.id, m.from_user)
        elif action == "loop":
            loops[pid] = not loops.get(pid, False)
            await m.reply_text(f"↻ Loop {'ON' if loops[pid] else 'OFF'}")
        elif action == "queue":
            q = queues.get(pid, [])
            if not q:
                return await m.reply_text("ǫυєυє ɪѕ єϻᴘᴛʏ.")
            lines = [f"▷ {q[0]['title']}"] + [f"{i}. {t['title']}" for i, t in enumerate(q[1:], 1)]
            await m.reply_text(" **ǫυєυє**\n\n" + "\n".join(lines))
    except Exception as e:
        await m.reply_text(f"❌ {e}")
