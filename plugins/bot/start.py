from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


_owner_html = None


async def owner_mention():
    """Clickable owner name for 'Powered By' (opens the owner's profile)."""
    global _owner_html
    if _owner_html:
        return _owner_html
    if OWNER_ID:
        try:
            u = await bot.get_users(OWNER_ID)
            name = f"{u.first_name or ''} {u.last_name or ''}".strip() or DEV_NAME
            if u.username:                                  # t.me link opens the profile for EVERYONE
                _owner_html = f'<a href="https://t.me/{u.username}">{html.escape(name)}</a>'
            else:
                _owner_html = _mention_html(u.id, name)
            return _owner_html
        except Exception:                                   # owner never started the bot: link by id, don't cache
            if DEV_LINK:
                return f'<a href="{html.escape(DEV_LINK)}">{html.escape(DEV_NAME)}</a>'
            return _mention_html(OWNER_ID, DEV_NAME)
    if DEV_LINK:
        return f'<a href="{html.escape(DEV_LINK)}">{html.escape(DEV_NAME)}</a>'
    return html.escape(DEV_NAME)


async def start_text(user=None):
    """user = the person who pressed /start (or Back): greeted by name at the top, clickable."""
    hey = ""
    if user:
        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "User"
        hey = f"<b>ʜєʏ</b> {_mention_html(user.id, name)}\n\n"
    return (
        hey +
        "<blockquote><b><u>✦ ɢʀєєᴛɪηɢѕ ✦</u></b></blockquote>\n\n"
        "<blockquote expandable>ʏσυ αʀє υѕɪηɢ  <b>˹ " + font4(BOT_NAME) + " ˼</b>\n"
        "ᴛнє υʟᴛɪϻαᴛє ᴅєѕᴛɪηαᴛɪση ғσʀ нɪɢн-ǫυαʟɪᴛʏ ѕᴛʀєαϻɪηɢ.\n"
        "✦ ѕϻσσᴛн ϻυѕɪᴄ ɪη ᴠσɪᴄє ᴄнαᴛѕ\n"
        "✦ ᴄʀʏѕᴛαʟ-ᴄʟєαʀ αυᴅɪσ &amp; нᴅ ᴠɪᴅєσ\n"
        "✦ ɢʀσυᴘ + ᴄнαηηєʟ ᴘʟαʏ\n"
        "✦ ᴘєʀѕσηαʟ ғαᴠσυʀɪᴛєѕ</blockquote>\n\n"
        "<blockquote>ᴄʟɪᴄᴋ <b>нєʟᴘ &amp; ᴄσϻϻαηᴅѕ</b> ᴛσ ѕєє αʟʟ ᴄσϻϻαηᴅѕ.</blockquote>\n\n"
        "<blockquote><b>ᴘσωєʀєᴅ вʏ :-</b> " + await owner_mention() + "</blockquote>"
    )


START_ANIM_FRAMES = [
    "🔵 <b>ᴅɪηɢ ᴅσηɢ</b> 🔵",
    "🟢 <b>ᴅɪηɢ ᴅσηɢ</b> 🟢",
    "🔴 <b>ᴅɪηɢ ᴅσηɢ</b> 🔴",
    "💞💖💝❣️",
    "💞💖💝",
    "💞💖",
    "💞",
]
START_ANIM_DELAY = 0.25         # seconds between frames (fast)


async def start_animation(m):
    """Ding Dong (bold, blue/green/red) -> emojis vanishing one by one, then the message is deleted."""
    try:
        msg = await m.reply_text(START_ANIM_FRAMES[0], parse_mode=ParseMode.HTML)
    except Exception:
        return
    try:
        for frame in START_ANIM_FRAMES[1:]:
            await asyncio.sleep(START_ANIM_DELAY)
            try:
                await msg.edit_text(frame, parse_mode=ParseMode.HTML)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception:
                pass
        await asyncio.sleep(START_ANIM_DELAY)
    finally:
        try:
            await msg.delete()
        except Exception:
            pass


@bot.on_message(filters.command("start"))
async def start(_, m):
    if m.chat.type != ChatType.PRIVATE:
        return await m.reply_text(f"✦ **{BOT_NAME}** ɪѕ αʟɪᴠє! ѕᴛαʀᴛ ϻє ɪη ᴘʀɪᴠαᴛє ғσʀ /help.")
    await start_animation(m)
    markup = await start_markup()
    if START_IMG:
        try:
            return await m.reply_photo(START_IMG, caption=await start_text(m.from_user), parse_mode=ParseMode.HTML,
                                      reply_markup=markup)
        except Exception:
            pass
    await m.reply_text(await start_text(m.from_user), reply_markup=markup, parse_mode=ParseMode.HTML, **NO_PREVIEW)


@bot.on_message(filters.command("help"))
async def help_cmd(_, m):
    await m.reply_text(HELP_TEXT, reply_markup=help_markup(False), parse_mode=ParseMode.HTML, **NO_PREVIEW)


ADMIN_HELP_TEXT = (
    "**ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅꜱ**\n\n"
    "/warn :- ᴡᴀʀɴ ᴛʜᴇ ᴜꜱᴇʀ\n"
    "/unwarn :- ʀᴇᴍᴏᴠᴇ ᴛʜᴇ ᴜꜱᴇʀ ᴡᴀʀɴ\n"
    "/dwarn :- ᴅᴇʟᴇᴛᴇ ᴛʜᴇ ᴍᴇꜱꜱᴀɢᴇ ᴀɴᴅ ᴡᴀʀɴ ᴛʜᴇ ᴜꜱᴇʀ\n\n"
    "/ban :- ʙᴀɴ ᴛʜᴇ ᴜꜱᴇʀ\n"
    "/unban :- ᴜɴʙᴀɴ ᴛʜᴇ ᴜꜱᴇʀ\n"
    "/dban :- ᴅᴇʟᴇᴛᴇ ᴛʜᴇ ᴍᴇꜱꜱᴀɢᴇ ᴀɴᴅ ʙᴀɴ ᴛʜᴇ ᴜꜱᴇʀ\n\n"
    "/mute :- ᴍᴜᴛᴇ ᴛʜᴇ ᴜꜱᴇʀ\n"
    "/unmute :- ᴜɴᴍᴜᴛᴇ ᴛʜᴇ ᴜꜱᴇʀ\n"
    "/dmute :- ᴅᴇʟᴇᴛᴇ ᴛʜᴇ ᴍᴇꜱꜱᴀɢᴇ ᴀɴᴅ ᴍᴜᴛᴇ ᴛʜᴇ ᴜꜱᴇʀ\n\n"
    "ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ'ꜱ ᴍᴇꜱꜱᴀɢᴇ, ᴏʀ ᴜꜱᴇ /ban ʀᴇᴀꜱᴏɴ."
)


AUTOAPPROVE_HELP_TEXT = (
    "<b><u>⦾ ᴀᴜᴛᴏᴀᴘᴘʀᴏᴠᴇ :</u></b>\n\n"
    "<blockquote>💮 ᴄᴏɴᴛʀᴏʟ ʜᴏᴡ ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛꜱ ᴀʀᴇ ʜᴀɴᴅʟᴇᴅ ɪɴ ᴛʜɪꜱ ᴄʜᴀᴛ.</blockquote>\n\n"
    "<blockquote>"
    "➻ /autoapprove : ᴛᴏɢɢʟᴇ ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴀʟ ᴏꜰ ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛꜱ.\n"
    "➻ /approveall : ᴀᴘᴘʀᴏᴠᴇ ᴀʟʟ ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛꜱ.\n"
    "➻ /capproveall : ᴀᴘᴘʀᴏᴠᴇ ᴀʟʟ ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛꜱ ɪɴ ᴛʜᴇ ʟɪɴᴋᴇᴅ ᴄʜᴀɴɴᴇʟ.\n"
    "➻ /pendingall : ʟɪꜱᴛ ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛꜱ ᴡɪᴛʜ ᴀᴄᴄᴇᴘᴛ/ᴅᴇᴄʟɪɴᴇ ʙᴜᴛᴛᴏɴꜱ.\n"
    "➻ /pendingcount : ꜱʜᴏᴡ ʜᴏᴡ ᴍᴀɴʏ ʀᴇǫᴜᴇꜱᴛꜱ ᴀʀᴇ ᴘᴇɴᴅɪɴɢ.\n"
    "➻ /clearpending : ᴅᴇᴄʟɪɴᴇ &amp; ᴄʟᴇᴀʀ ᴀʟʟ ᴘᴇɴᴅɪɴɢ ʀᴇǫᴜᴇꜱᴛꜱ."
    "</blockquote>"
)


AUTH_HELP_TEXT = (
    "<b><u>⦾ ᴀᴜᴛʜ :</u></b>\n\n"
    "<blockquote>💮 ᴄᴏɴᴛʀᴏʟ ᴡʜᴏ ᴄᴀɴ ᴜꜱᴇ ᴛʜᴇ ᴘʟᴀʏʙᴀᴄᴋ ᴄᴏɴᴛʀᴏʟꜱ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</blockquote>\n\n"
    "<blockquote>"
    "➻ /auth : ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ ᴛᴏ ᴀʟʟᴏᴡ ᴛʜᴇᴍ.\n"
    "➻ /unauth : ʀᴇᴍᴏᴠᴇ ᴛʜᴇɪʀ ᴀᴄᴄᴇꜱꜱ.\n"
    "➻ /authlist : ʟɪꜱᴛ ᴏꜰ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜꜱᴇʀꜱ."
    "</blockquote>\n\n"
    "<blockquote>ɢʀᴏᴜᴘ ᴀᴅᴍɪɴꜱ ᴀʟᴡᴀʏꜱ ʜᴀᴠᴇ ᴀᴄᴄᴇꜱꜱ, ᴡʜᴇᴛʜᴇʀ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴏʀ ɴᴏᴛ.</blockquote>"
)

INFO_HELP_TEXT = (
    "<b><u>⦾ ɪɴꜰᴏ :</u></b>\n\n"
    "<blockquote>💮 ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ ᴀɴᴅ ɢʀᴏᴜᴘ ꜱᴛᴀᴛꜱ.</blockquote>\n\n"
    "<blockquote>"
    "➻ /ping : ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ (ᴜᴘᴛɪᴍᴇ, ʀᴀᴍ, ᴄᴘᴜ, ᴅɪꜱᴋ).\n"
    "➻ /leaderboard : ᴛᴏᴘ 5 ʟɪꜱᴛᴇɴᴇʀꜱ ᴏꜰ ᴛʜɪꜱ ɢʀᴏᴜᴘ (ᴀᴅᴍɪɴꜱ ᴏɴʟʏ).\n"
    "➻ /welcome ᴏɴ|ᴏꜰꜰ : ᴛᴜʀɴ ᴛʜᴇ ᴡᴇʟᴄᴏᴍᴇ ᴍᴇꜱꜱᴀɢᴇ ᴏɴ/ᴏꜰꜰ (ᴀᴅᴍɪɴꜱ).\n"
    "➻ /adminlist : ꜱʜᴏᴡ ᴛʜᴇ ɢʀᴏᴜᴘ ᴏᴡɴᴇʀ ᴀɴᴅ ᴀᴅᴍɪɴꜱ.\n"
    "➻ /bots : ʟɪꜱᴛ ᴀʟʟ ʙᴏᴛꜱ ɪɴ ᴛʜᴇ ɢʀᴏᴜᴘ."
    "</blockquote>"
)

CHANNEL_HELP_TEXT = (
    "<b><u>⦾ ᴄʜᴀɴɴᴇʟ ᴠᴄ :</u></b>\n\n"
    "<blockquote>💮 ᴘʟᴀʏ ᴍᴜꜱɪᴄ ɪɴ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴏꜰ ᴀ ʟɪɴᴋᴇᴅ ᴄʜᴀɴɴᴇʟ.</blockquote>\n\n"
    "<blockquote>"
    "➻ /playchannel &lt;ɪᴅ/@ᴜꜱᴇʀɴᴀᴍᴇ&gt; : ᴄᴏɴɴᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ.\n"
    "➻ /cplay : ᴘʟᴀʏ ᴀᴜᴅɪᴏ ɪɴ ᴄʜᴀɴɴᴇʟ ᴠᴄ.\n"
    "➻ /vcplay : ᴘʟᴀʏ ᴠɪᴅᴇᴏ ɪɴ ᴄʜᴀɴɴᴇʟ ᴠᴄ.\n"
    "➻ /cpause /cresume /cskip /cend (/cstop) /cloop /cqueue : ᴄʜᴀɴɴᴇʟ ᴄᴏɴᴛʀᴏʟꜱ.\n"
    "➻ /cseek &lt;ꜱᴇᴄ&gt; : ꜱᴇᴇᴋ ꜰᴏʀᴡᴀʀᴅ ʙʏ ᴛʜɪꜱ ᴍᴀɴʏ ꜱᴇᴄᴏɴᴅꜱ.\n"
    "➻ /cseekback &lt;ꜱᴇᴄ&gt; : ꜱᴇᴇᴋ ʙᴀᴄᴋᴡᴀʀᴅ."
    "</blockquote>"
)

BCAST_HELP_TEXT = (
    "<b><u>⦾ ʙ-ᴄᴀꜱᴛ :</u></b>\n\n"
    "<blockquote>💮 ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀꜱ ᴀɴᴅ ɢʀᴏᴜᴘꜱ. (ʙᴏᴛ ᴏᴡɴᴇʀ ᴏɴʟʏ)</blockquote>\n\n"
    "<blockquote>"
    "➻ /broadcast &lt;ᴛᴇxᴛ&gt; : ꜱᴇɴᴅ ᴛᴇxᴛ.\n"
    "➻ ʀᴇᴘʟʏ ᴡɪᴛʜ /broadcast : ᴄᴏᴘʏ ᴀ ᴍᴇꜱꜱᴀɢᴇ (ɴᴏ ꜰᴏʀᴡᴀʀᴅ ᴛᴀɢ).\n"
    "➻ ʀᴇᴘʟʏ ᴡɪᴛʜ /broadcast -forward : ᴡɪᴛʜ ꜰᴏʀᴡᴀʀᴅ ᴛᴀɢ.\n"
    "➻ ꜰʟᴀɢꜱ : -users, -groups, -forward\n"
    "➻ ʙᴜᴛᴛᴏɴꜱ : ᴀᴅᴅ ʟɪɴᴇꜱ ᴀᴛ ᴛʜᴇ ᴇɴᴅ - btn: ᴛᴇxᴛ | https://link\n"
    "</blockquote>"
)

SEEK_HELP_TEXT = "<b>ꜱᴇᴇᴋ ꜱᴛʀᴇᴀᴍ :</b>\n\n<blockquote>• /seek [ꜱᴇᴄᴏɴᴅꜱ] : ɢᴏᴇꜱ ꜰᴏʀᴡᴀʀᴅ ɪɴ ᴛʜᴇ ꜱᴛʀᴇᴀᴍ.\n• /seekback [ꜱᴇᴄᴏɴᴅꜱ] : ꜱᴇᴇᴋꜱ ʙᴀᴄᴋᴡᴀʀᴅ.</blockquote>"

MOOD_HELP_TEXT = (
    "<b>ᴍᴏᴏᴅ ᴍᴜꜱɪᴄ :</b>\n\n<blockquote>"
    "• /mood : ᴍᴏᴏᴅ ʙᴜᴛᴛᴏɴꜱ ᴋʜᴜʟᴛᴇ ʜᴀɪɴ, ᴍᴏᴏᴅ ᴀᴜʀ ʟᴀɴɢᴜᴀɢᴇ ᴄʜᴜɴᴏ\n"
    "• /mood sad : ꜱᴀᴅ ɢᴀᴀɴᴇ (ʟᴀɴɢᴜᴀɢᴇ ᴍɪx)\n"
    "• /mood party english : ᴘᴀʀᴛʏ ɪɴ ᴇɴɢʟɪꜱʜ\n\n"
    "ᴍᴏᴏᴅ : sad, romantic, party, chill, gym, travel, devotional, sleep, attitude, retro\n"
    "ʟᴀɴɢᴜᴀɢᴇ : hindi, punjabi, english, mix</blockquote>"
)

HELP_PAGES = {                                      # callback prefix -> (text, parse mode)
    "adminhelp": (ADMIN_HELP_TEXT, None),
    "autohelp": (AUTOAPPROVE_HELP_TEXT, ParseMode.HTML),
    "authhelp": (AUTH_HELP_TEXT, ParseMode.HTML),
    "infohelp": (INFO_HELP_TEXT, ParseMode.HTML),
    "chhelp": (CHANNEL_HELP_TEXT, ParseMode.HTML),
    "bchelp": (BCAST_HELP_TEXT, ParseMode.HTML),
    "seekhelp": (SEEK_HELP_TEXT, ParseMode.HTML),
    "moodhelp": (MOOD_HELP_TEXT, ParseMode.HTML),
}


def help_markup(from_start):
    """Help page buttons. from_start = opened from the /start card, so it also gets a Back button."""
    n = int(from_start)
    rows = [
        [Btn("˹ᴧᴅϻɪηѕ˼", RED, callback_data=f"adminhelp:{n}"),
         Btn("˹ᴧυᴛσαᴘᴘʀσᴠє˼", BLUE, callback_data=f"autohelp:{n}"),
         Btn("˹ᴧυᴛн˼", GREEN, callback_data=f"authhelp:{n}")],
        [Btn("˹ɪηғσ˼", GREEN, callback_data=f"infohelp:{n}"),
         Btn("˹ᴄнαηηєʟ ᴠᴄ˼", RED, callback_data=f"chhelp:{n}"),
         Btn("˹в-ᴄᴧѕᴛ˼", BLUE, callback_data=f"bchelp:{n}")],
        [Btn("˹ѕєєᴋ˼", GREEN, callback_data=f"seekhelp:{n}"),
         Btn("˹ᴍσσᴅ˼", BLUE, callback_data=f"moodhelp:{n}")],
    ]
    bottom = []
    if from_start:
        bottom.append(Btn(" вαᴄᴋ", RED, key="back1", callback_data="home"))
    bottom.append(Btn(f"{f5('Next')} ▷", BLUE, key="next1", callback_data=f"help2:{n}"))      # page 2: Group / Info
    rows.append(bottom)
    return IKM(rows)


@bot.on_callback_query(filters.regex(r"^(help|home|help:[01]|(adminhelp|autohelp|authhelp|infohelp|chhelp|bchelp|seekhelp|moodhelp):[01])$"))
async def help_home(_, cq):
    data = cq.data
    page = HELP_PAGES.get(data.split(":")[0])
    if data == "home":
        await edit_any(cq.message, await start_text(cq.from_user), await start_markup(), ParseMode.HTML)
    elif page:                                      # one of the help pages: edit this message in place
        text, pm = page
        await edit_any(cq.message, text, IKM([[Btn(" ˹вαᴄᴋ˼", RED, key="backhelp", callback_data="help:" + data.split(":")[1])]]), pm)
    else:                                           # "help" (from the /start card) or "help:<0|1>"
        from_start = data == "help" or data.endswith(":1")
        await edit_any(cq.message, HELP_TEXT, help_markup(from_start), ParseMode.HTML)
    await cq.answer()
