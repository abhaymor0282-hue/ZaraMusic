from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


@bot.on_message(filters.command(["sudo", "rmsudo", "sudolist"]))
async def sudo_cmd(_, m):
    if not is_owner(m):                                     # only the bot owner manages sudo users
        return
    name = m.command[0].lower()
    if name == "sudolist":
        if not sudoers:
            return await m.reply_text("📋 ᴛʜᴇ sᴜᴅᴏ ʟɪsᴛ ɪs ᴇᴍᴘᴛʏ.")
        lines = [f"{i}. [{n}](tg://user?id={u}) (`{u}`)" for i, (u, n) in enumerate(sudoers.items(), 1)]
        return await m.reply_text(f"👑 **sᴜᴅᴏ ᴜsᴇʀs** ({len(sudoers)})\n\n" + "\n".join(lines))
    user = await resolve_target(m)
    if not user:
        return await m.reply_text(
            f"υѕαɢє: ʀєᴘʟʏ ᴛσ ѕσϻєσηє'ѕ ϻєѕѕαɢє ωɪᴛн `/{name}`\nσʀ `/{name} @username` / `/{name} <user id>`")
    if user.is_bot:
        return await m.reply_text("🤖 ᴀ ʙᴏᴛ ᴄᴀɴɴᴏᴛ ʙᴇ ᴀ sᴜᴅᴏ ᴜsᴇʀ.")
    key = str(user.id)
    if name == "sudo":
        if user.id == OWNER_ID:
            return await m.reply_text("👑 ʏᴏᴜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ.")
        if key in sudoers:
            return await m.reply_text(f"{user_link(user)} ɪs ᴀʟʀᴇᴀᴅʏ ɪɴ ᴛʜᴇ sᴜᴅᴏ ʟɪsᴛ.")
        sudoers[key] = clean_name(user)
        save("sudo.json", sudoers)
        return await m.reply_text(
            f"✅ {user_link(user)} ɪs ɴᴏᴡ ᴀ **sᴜᴅᴏ ᴜsᴇʀ**.\n"
            "ᴛʜᴇʏ ᴄᴀɴ ᴜsᴇ `/broadcast`, `/auth`, `/unauth` ᴀɴᴅ `/stats`.")
    if key not in sudoers:
        return await m.reply_text(f"{user_link(user)} ɪs ɴᴏᴛ ɪɴ ᴛʜᴇ sᴜᴅᴏ ʟɪsᴛ.")
    del sudoers[key]
    save("sudo.json", sudoers)
    await m.reply_text(f"🗑 {user_link(user)} ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ᴛʜᴇ sᴜᴅᴏ ʟɪsᴛ.")
