from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- ping + leaderboard -----
def fmt_uptime(sec):
    sec = int(sec)
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    mi, s = divmod(sec, 60)
    return " ".join(p for p in (f"{d}d" if d else "", f"{h}h" if h else "", f"{mi}m" if mi else "", f"{s}s") if p)


@bot.on_message(filters.command("ping"))
async def ping(_, m):
    t0 = time.perf_counter()
    tmp = await m.reply_text("🏓 Pinging...")
    ms = int((time.perf_counter() - t0) * 1000)
    uname = await bot_username()
    gb = 1024 ** 3
    if psutil:
        vm, disk = psutil.virtual_memory(), psutil.disk_usage("/")
        ram = f"{vm.used / gb:.2f} / {vm.total / gb:.2f} GB"
        cpu = f"{psutil.cpu_percent(None):.2f}%"
        dsk = f"{disk.used / gb:.2f} / {disk.total / gb:.2f} GB"
    else:
        ram = cpu = dsk = "N/A"
    dev = f"[{DEV_NAME}]({DEV_LINK})" if DEV_LINK else DEV_NAME
    caption = (
        f"• **ᴘᴏɴɢ:** `{ms}ms`\n\n"
        f"• [{BOT_NAME}](https://t.me/{uname}) **sᴛᴀᴛɪsᴛɪᴄs :**\n\n"
        f"• **ᴜᴘᴛɪᴍᴇ:** `{fmt_uptime(time.time() - START_TIME)}`\n"
        f"• **ʀᴀᴍ :** `{ram}`\n"
        f"• **ᴄᴘᴜ :** `{cpu}`\n"
        f"• **ᴅɪsᴋ :** `{dsk}`\n"
        f"• **ʟɪʙʀᴀʀʏ :** `PYROGRAM`\n"
        f"• **ᴅᴇᴠᴇʟᴏᴘᴇᴅ ʙʏ :** {dev}"
    )
    markup = IKM([[Btn("sᴜᴘᴘᴏʀᴛ", BLUE, key="pingsupport", url=SUPPORT_URL)]])
    try:
        await tmp.delete()
    except Exception:
        pass
    img = PING_IMG or START_IMG
    if img:
        try:
            return await m.reply_photo(img, caption=caption, reply_markup=markup)
        except Exception:
            pass
    await m.reply_text(caption, reply_markup=markup, **NO_PREVIEW)
