from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


@bot.on_message(filters.command("leaderboard") & filters.group)
async def leaderboard(_, m):
    if not await is_group_admin(m):
        return await m.reply_text("🔒 ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴄᴀɴ ᴏɴʟʏ ʙᴇ ᴜꜱᴇᴅ ʙʏ ᴛʜᴇ ɢʀᴏᴜᴘ ᴏᴡɴᴇʀ/admins ᴏʀ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ.")
    data = plays.get(str(m.chat.id), {})
    if not data:
        return await m.reply_text("📊 ɴᴏʙᴏᴅʏ ʜᴀꜱ ᴘʟᴀʏᴇᴅ ᴀ ꜱᴏɴɢ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ ʏᴇᴛ.")
    top = sorted(data.items(), key=lambda kv: kv[1]["n"], reverse=True)[:5]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    lines = [f"{medals[i]} [{u['name']}](tg://user?id={user_id}) — `{u['n']}` songs"
             for i, (user_id, u) in enumerate(top)]
    total = sum(u["n"] for u in data.values())
    await m.reply_text(
        f"🏆 **Music Leaderboard**\n**{m.chat.title}**\n\n" + "\n".join(lines) +
        f"\n\n🎵 Total songs played: `{total}`")
