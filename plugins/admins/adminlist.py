from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- /adminlist and /bots (everyone can use them) -----
_FONT = dict(zip("abcdefghijklmnopqrstuvwxyz", "αвᴄᴅєғɢнɪᴊᴋʟϻησᴘǫʀѕᴛυᴠωχʏᴢ"))      # same font as the rest of the bot


def bot_font(text):
    return "".join(_FONT.get(c.lower(), c) for c in text)


def _full_name(u):
    """Display name in the bot font (Latin letters only; other alphabets stay as they are)."""
    name = f"{u.first_name or ''} {u.last_name or ''}".strip() or ("Deleted Account" if u.is_deleted else "User")
    return bot_font(name)


def _pages(first, lines, limit=3500):
    """Splits a long list into several messages (Telegram allows 4096 characters per message)."""
    pages, cur = [], first
    for ln in lines:
        if len(cur) + len(ln) + 1 > limit:
            pages.append(cur)
            cur = ln
        else:
            cur += "\n" + ln
    pages.append(cur)
    return pages


def _uname(u):
    return f"@{html.escape(u.username)}" if u.username else "—"


@bot.on_message(filters.command(["adminlist", "staff"]) & filters.group)
async def adminlist_cmd(_, m):
    """Group owner on top, then every admin (bots are marked with a robot)."""
    owner, admins = None, []
    try:
        async for mem in bot.get_chat_members(m.chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
            if mem.status == ChatMemberStatus.OWNER:
                owner = mem
            else:
                admins.append(mem)
    except Exception as e:
        return await m.reply_text(f" ғαɪʟєᴅ: {e}")
    if owner:
        title = html.escape(bot_font(owner.custom_title or "owner"))
        owner_line = f"{_mention_html(owner.user.id, _full_name(owner.user))} ({title})"
    else:
        owner_line = "—"
    lines = [f"{i}) {'🤖 ' if a.user.is_bot else ''}{_mention_html(a.user.id, _full_name(a.user))}, "
             f"{_uname(a.user)} ({html.escape(bot_font(a.custom_title or 'admin'))})"
             for i, a in enumerate(admins, 1)] or ["—"]
    head = f"<b>👑 ɢʀσυᴘ σωηєʀ :-</b> {owner_line}\n\n<b>🛡 ɢʀσυᴘ αᴅϻɪηѕ :-</b>"
    for page in _pages(head, lines):
        await m.reply_text(page, parse_mode=ParseMode.HTML, **NO_PREVIEW)


@bot.on_message(filters.command("bots") & filters.group)
async def bots_cmd(_, m):
    """Every bot in the group (the bot must be an admin to see them all)."""
    found = []
    try:
        async for mem in bot.get_chat_members(m.chat.id, filter=ChatMembersFilter.BOTS):
            if mem.user.is_bot:
                found.append(mem.user)
    except Exception as e:
        return await m.reply_text(f" ғαɪʟєᴅ: {e}")
    if not found:
        return await m.reply_text(" ησ вσᴛѕ ғσυηᴅ ɪη ᴛнɪѕ ɢʀσυᴘ.")
    lines = [f"{i}) {_uname(u) if u.username else _mention_html(u.id, _full_name(u))}"
             for i, u in enumerate(found, 1)]
    for page in _pages(f"<b>🤖 ᴛσᴛᴀʟ вσᴛѕ :-</b> {len(found)}\n", lines):
        await m.reply_text(page, parse_mode=ParseMode.HTML, **NO_PREVIEW)
