from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


@bot.on_message(filters.command(["block", "unblock", "blockedusers"]))
async def block_cmd(_, m):
    if not is_owner(m):
        return
    name = m.command[0].lower()
    if name == "blockedusers":
        if not blocked_users:
            return await m.reply_text("📋 ɴᴏ ᴜsᴇʀs ᴀʀᴇ ʙʟᴏᴄᴋᴇᴅ.")
        lines = [f"{i}. [{n}](tg://user?id={u}) (`{u}`)" for i, (u, n) in enumerate(blocked_users.items(), 1)]
        return await m.reply_text(f"🚫 **ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs** ({len(blocked_users)})\n\n" + "\n".join(lines))
    user = await resolve_target(m)
    uid_, uname_ = None, None
    if user:
        uid_, uname_ = user.id, clean_name(user)
        if user.is_bot:
            return await m.reply_text("🤖 ᴀ ʙᴏᴛ ᴄᴀɴɴᴏᴛ ʙᴇ ʙʟᴏᴄᴋᴇᴅ.")
    elif len(m.command) > 1 and re.fullmatch(r"\d+", m.command[1]):    # numeric id the bot has never seen
        uid_ = int(m.command[1])
        uname_ = str(uid_)
    if uid_ is None:
        return await m.reply_text(
            f"υѕαɢє: ʀєᴘʟʏ ᴛσ ѕσϻєσηє'ѕ ϻєѕѕαɢє ωɪᴛн `/{name}`\nσʀ `/{name} @username` / `/{name} <user id>`")
    key = str(uid_)
    shown = f"[{uname_}](tg://user?id={uid_})"
    if name == "unblock":
        if key not in blocked_users:
            return await m.reply_text(f"{shown} ɪs ɴᴏᴛ ɪɴ ᴛʜᴇ ʙʟᴏᴄᴋ ʟɪsᴛ.")
        del blocked_users[key]
        save("blocked_users.json", blocked_users)
        return await m.reply_text(f"✅ {shown} ʜᴀs ʙᴇᴇɴ ᴜɴʙʟᴏᴄᴋᴇᴅ. ᴛʜᴇʏ ᴄᴀɴ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ ᴀɢᴀɪɴ.")
    if OWNER_ID and uid_ == OWNER_ID:
        return await m.reply_text("👑 ʏᴏᴜ ᴄᴀɴɴᴏᴛ ʙʟᴏᴄᴋ ʏᴏᴜʀsᴇʟғ.")
    if key in blocked_users:
        return await m.reply_text(f"{shown} ɪs ᴀʟʀᴇᴀᴅʏ ʙʟᴏᴄᴋᴇᴅ.")
    blocked_users[key] = uname_
    save("blocked_users.json", blocked_users)
    await m.reply_text(f"🚫 {shown} ʜᴀs ʙᴇᴇɴ ʙʟᴏᴄᴋᴇᴅ.\nᴛʜᴇʏ ᴄᴀɴ ɴᴏ ʟᴏɴɢᴇʀ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ ᴀɴʏᴡʜᴇʀᴇ.")
