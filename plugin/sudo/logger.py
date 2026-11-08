from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


@bot.on_message(filters.command("logger"))
async def logger_toggle(_, m):
    if not is_owner(m):
        return
    if len(m.command) < 2 or m.command[1].lower() not in ("on", "off"):
        state = "ON" if settings.get("logger", True) else "OFF"
        return await m.reply_text(f"ʟᴏɢɢᴇʀ ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ **{state}**.\nᴜꜱᴀɢᴇ: `/logger on` ᴏʀ `/logger off`")
    settings["logger"] = m.command[1].lower() == "on"
    save("settings.json", settings)
    await m.reply_text(f"✅ Logger {'ON' if settings['logger'] else 'OFF'}")
