from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


@bot.on_message(filters.command(["auth", "unauth"]) & filters.group)
async def auth_cmd(_, m):
    name = m.command[0].lower()
    if not (is_owner_or_sudo(m) or await is_group_admin(m)):
        return await m.reply_text(" `/auth` αηᴅ `/unauth` ᴄαη σηʟʏ вє υѕєᴅ вʏ ɢʀσυᴘ αᴅϻɪηѕ.")
    user = await resolve_target(m)
    if not user:
        return await m.reply_text(
            f"υѕαɢє: ʀєᴘʟʏ ᴛσ ѕσϻєσηє'ѕ ϻєѕѕαɢє ωɪᴛн `/{name}`\nσʀ `/{name} @username` / `/{name} <user id>`")
    if user.is_bot:
        return await m.reply_text(" ᴛнє вσᴛ ᴄαηησᴛ вє αυᴛнσʀɪᴢєᴅ.")
    g = authed.setdefault(str(m.chat.id), {})
    key = str(user.id)
    if name == "auth":
        if key in g:
            return await m.reply_text(f"{user_link(user)} ɪѕ αʟʀєαᴅʏ ɪη ᴛнє αυᴛн ʟɪѕᴛ..")
        g[key] = clean_name(user)
        save("auth.json", authed)
        return await m.reply_text(f" {user_link(user)} нαѕ вєєη αυᴛнσʀɪᴢєᴅ.\nᴛнєʏ ᴄαη ησω υѕє ᴄσηᴛʀσʟѕ ʟɪᴋє ѕᴋɪᴘ.")
    if key not in g:
        return await m.reply_text(f"{user_link(user)} ɪѕ ησᴛ ɪη ᴛнє αυᴛн ʟɪѕᴛ.")
    del g[key]
    save("auth.json", authed)
    await m.reply_text(f" {user_link(user)} нαѕ вєєη ʀєϻσᴠєᴅ ғʀσϻ ᴛнє αυᴛн ʟɪѕᴛ.")


@bot.on_message(filters.command("authlist") & filters.group)
async def authlist(_, m):
    g = authed.get(str(m.chat.id), {})
    if not g:
        return await m.reply_text(" ᴛнє αυᴛн ʟɪѕᴛ ɪѕ єϻᴘᴛʏ.\nɢʀσυᴘ αᴅϻɪηѕ ᴄαη αʟωαʏѕ υѕє ᴛнє ᴄσηᴛʀσʟѕ.")
    lines = [f"{i}. [{n}](tg://user?id={u})" for i, (u, n) in enumerate(g.items(), 1)]
    await m.reply_text(
        f" **ᴧυᴛн υѕєʀѕ**\n**{m.chat.title}**\n\n" + "\n".join(lines) +
        "\n\nɢʀσυᴘ αᴅϻɪηѕ ᴄαη αʟωαʏѕ υѕє ᴛнє ᴄσηᴛʀσʟѕ, ωнєᴛнєʀ αυᴛнσʀɪᴢєᴅ σʀ ησᴛ..")
