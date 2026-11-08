from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


@bot.on_message(filters.command("playchannel") & filters.group)
async def playchannel(_, m):
    if len(m.command) < 2:
        return await m.reply_text("υѕαɢє: `/playchannel -100xxxxxxxxxx` σʀ `/playchannel @username`")
    arg = m.command[1]
    arg = int(arg) if arg.lstrip("-").isdigit() else arg
    chat = None
    for client in (bot, assistant):
        try:
            chat = await client.get_chat(arg)
            break
        except Exception:
            continue
    if not chat or chat.type != ChatType.CHANNEL:
        return await m.reply_text(" ᴄнαηηєʟ ησᴛ ғσυηᴅ. αᴅᴅ ᴛнє вσᴛ/αѕѕɪѕᴛαηᴛ ᴛσ ᴛнє ᴄнαηηєʟ αηᴅ ᴄнєᴄᴋ ᴛнє ɪᴅ/υѕєʀηαϻє.")
    channels[str(m.chat.id)] = chat.id
    save("channels.json", channels)
    await m.reply_text(
        f" Channel connected: **{chat.title}**\n"
        "ɴσω υѕє /cplay (αυᴅɪσ) σʀ /vcplay (ᴠɪᴅєσ).\n"
        "ᴛнє αѕѕɪѕᴛαηᴛ αᴄᴄσυηᴛ ϻυѕᴛ вє αη αᴅϻɪη ɪη ᴛнє ᴄнαηηєʟ (ϻαηαɢє ᴠɪᴅєσ ᴄнαᴛѕ) αηᴅ ᴛнє ᴄнαηηєʟ'ѕ ᴠᴄ ϻυѕᴛ вє ση.")
