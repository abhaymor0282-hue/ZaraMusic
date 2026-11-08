from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


@bot.on_message(filters.command("stats"))
async def stats(_, m):
    if not is_owner_or_sudo(m):
        return
    active = sum(1 for q in queues.values() if q)
    await m.reply_text(
        "📊 **Bot Stats**\n\n"
        f"🎧 Active voice chats: `{active}`\n"
        f"📡 Linked channels: `{len(channels)}`\n"
        f"👤 Bot users: `{len(known['users'])}`\n"
        f"👥 Groups: `{len(known['chats'])}`\n"
        f"📝 Logger: `{'ON' if settings.get('logger', True) else 'OFF'}`")
