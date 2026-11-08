from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- moderation: ban / mute / warn -----
WARN_LIMIT = int(os.getenv("WARN_LIMIT", "3"))   # warns before the user is banned automatically
warns: dict = load("warns.json", {})             # group_id -> {user_id: warn count}
MOD_CMDS = ["ban", "dban", "unban", "mute", "dmute", "unmute", "warn", "dwarn", "unwarn"]
_bot_id = None


async def can_restrict(m):
    """Bot owner, group owner, or an admin that has the 'Ban Users' right."""
    if m.from_user is None:                                   # anonymous admin posts as the group itself
        return bool(m.sender_chat and m.sender_chat.id == m.chat.id)
    if OWNER_ID and m.from_user.id == OWNER_ID:
        return True
    try:
        mem = await bot.get_chat_member(m.chat.id, m.from_user.id)
    except Exception:
        return False
    if mem.status == ChatMemberStatus.OWNER:
        return True
    return (mem.status == ChatMemberStatus.ADMINISTRATOR
            and mem.privileges is not None and bool(mem.privileges.can_restrict_members))


async def mod_target(m):
    """(user, reason): the replied-to user, or @username / id as first argument. The rest is the reason."""
    args = m.command[1:]
    if m.reply_to_message and m.reply_to_message.from_user:
        return m.reply_to_message.from_user, " ".join(args)
    if args:
        arg = int(args[0]) if args[0].lstrip("-").isdigit() else args[0]
        try:
            return await bot.get_users(arg), " ".join(args[1:])
        except Exception:
            return None, ""
    return None, ""


def mod_text(user, title, label, admin, reason, extra=""):
    text = (f"<b>{_mention_html(user.id, disp_name(user))} ɪѕ {title}.</b>\n\n"
            f"<b>{label} :-</b> {admin}\n"
            f"<b>ʀєαѕση :-</b> {html.escape(reason) if reason else 'ησ ʀєαѕση ɢɪᴠєη'}")
    return text + (f"\n<b>ωαʀηѕ :-</b> {extra}" if extra else "")


MOD_BTN = {"ban": "Unban User", "mute": "Unmute User", "warn": "Remove Warn"}


def mod_markup(action, chat_id, user_id):
    return IKM([[Btn(MOD_BTN[action], GREEN, callback_data=f"modundo:{action}:{chat_id}:{user_id}")]])


@bot.on_message(filters.command(MOD_CMDS) & filters.group)
async def moderation(_, m):
    global _bot_id
    cmd = m.command[0].lower()
    delete = cmd in ("dban", "dmute", "dwarn")
    action = cmd[1:] if delete else cmd
    if not await can_restrict(m):
        return await m.reply_text(f" σηʟʏ ɢʀσυᴘ αᴅϻɪηѕ ωɪᴛн ᴛнє 'вαη υѕєʀѕ' ʀɪɢнᴛ ᴄαη υѕє /{cmd}.")
    if delete and not (m.reply_to_message and m.reply_to_message.from_user):
        return await m.reply_text(f"υѕαɢє: ʀєᴘʟʏ ᴛσ ᴛнє ϻєѕѕαɢє ʏσυ ωαηᴛ ᴛσ ᴅєʟєᴛє ωɪᴛн `/{cmd} <reason>`")
    user, reason = await mod_target(m)
    if not user:
        return await m.reply_text(
            f"υѕαɢє: ʀєᴘʟʏ ᴛσ α υѕєʀ ωɪᴛн `/{cmd} <reason>`\nor `/{cmd} @username <reason>` / `/{cmd} <user id>`")
    if _bot_id is None:
        _bot_id = (await bot.get_me()).id
    if user.id == _bot_id:
        return await m.reply_text(" ɪ ᴄαη'ᴛ ᴅσ ᴛнαᴛ ᴛσ ϻʏѕєʟғ.")
    if action in ("ban", "mute", "warn") and (user.id == OWNER_ID or await is_admin_id(m.chat.id, user.id)):
        return await m.reply_text(f" I can't {action} an admin.")

    admin = _mention_html(m.from_user.id, disp_name(m.from_user)) if m.from_user else "Anonymous Admin"
    chat_id = m.chat.id
    key, ukey = str(chat_id), str(user.id)
    markup = None
    try:
        if delete:
            try:
                await m.reply_to_message.delete()
            except Exception:
                pass                                          # no delete right: still do the action
        if action == "ban":
            await bot.ban_chat_member(chat_id, user.id)
            text = mod_text(user, "banned", "Ban by", admin, reason)
            markup = mod_markup("ban", chat_id, user.id)
        elif action == "unban":
            await bot.unban_chat_member(chat_id, user.id)
            text = mod_text(user, "unbanned", "Unban by", admin, reason)
        elif action == "mute":
            await bot.restrict_chat_member(chat_id, user.id, ChatPermissions())   # no permissions = muted
            text = mod_text(user, "muted", "Mute by", admin, reason)
            markup = mod_markup("mute", chat_id, user.id)
        elif action == "unmute":
            perms = (await bot.get_chat(chat_id)).permissions or ChatPermissions(can_send_messages=True)
            await bot.restrict_chat_member(chat_id, user.id, perms)               # back to the group's default
            text = mod_text(user, "unmuted", "Unmute by", admin, reason)
        elif action == "warn":
            g = warns.setdefault(key, {})
            g[ukey] = g.get(ukey, 0) + 1
            if g[ukey] >= WARN_LIMIT:
                await bot.ban_chat_member(chat_id, user.id)
                text = mod_text(user, "warned and banned", "Warn by", admin, reason,
                                f"{g[ukey]}/{WARN_LIMIT} (limit reached)")
                g.pop(ukey, None)
                markup = mod_markup("ban", chat_id, user.id)
            else:
                text = mod_text(user, "warned", "Warn by", admin, reason, f"{g[ukey]}/{WARN_LIMIT}")
                markup = mod_markup("warn", chat_id, user.id)
            save("warns.json", warns)
        else:                                                                     # unwarn
            g = warns.setdefault(key, {})
            if not g.get(ukey):
                return await m.reply_text(f"{_mention_html(user.id, disp_name(user))} has no warns.",
                                          parse_mode=ParseMode.HTML)
            g[ukey] -= 1
            left = g[ukey]
            if not left:
                g.pop(ukey, None)
            save("warns.json", warns)
            text = mod_text(user, "unwarned", "Unwarn by", admin, reason, f"{left}/{WARN_LIMIT}")
    except ChatAdminRequired:
        return await m.reply_text(" ϻαᴋє ϻє αη αᴅϻɪη ωɪᴛн ᴛнє 'вαη υѕєʀѕ' ʀɪɢнᴛ ғɪʀѕᴛ.")
    except Exception as e:
        return await m.reply_text(f" ғαɪʟєᴅ: {e}")
    await m.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


@bot.on_callback_query(filters.regex(r"^modundo:"))
async def mod_undo(_, cq):
    """Unban User / Unmute User / Remove Warn buttons under the moderation messages."""
    _, action, chat_s, user_s = cq.data.split(":")
    chat_id, user_id = int(chat_s), int(user_s)
    clicker = cq.from_user
    ok = bool(OWNER_ID) and clicker.id == OWNER_ID
    if not ok:
        try:
            mem = await bot.get_chat_member(chat_id, clicker.id)
            ok = mem.status == ChatMemberStatus.OWNER or (
                mem.status == ChatMemberStatus.ADMINISTRATOR
                and mem.privileges is not None and bool(mem.privileges.can_restrict_members))
        except Exception:
            ok = False
    if not ok:
        return await cq.answer("σηʟʏ αᴅϻɪηѕ ωɪᴛн ᴛнє 'вαη υѕєʀѕ' ʀɪɢнᴛ ᴄαη υѕє ᴛнɪѕ вυᴛᴛση.", show_alert=True)
    try:
        user = await bot.get_users(user_id)
    except Exception:
        return await cq.answer("Could not find this user.", show_alert=True)
    by = _mention_html(clicker.id, disp_name(clicker))
    try:
        if action == "ban":
            await bot.unban_chat_member(chat_id, user_id)
            text = mod_text(user, "unbanned", "Unban by", by, "")
        elif action == "mute":
            perms = (await bot.get_chat(chat_id)).permissions or ChatPermissions(can_send_messages=True)
            await bot.restrict_chat_member(chat_id, user_id, perms)
            text = mod_text(user, "unmuted", "υηϻυᴛє вʏ", by, "")
        else:                                                   # warn
            g = warns.setdefault(str(chat_id), {})
            if not g.get(str(user_id)):
                await cq.answer("ᴛнɪѕ υѕєʀ нαѕ ησ ωαʀηѕ ʟєғᴛ.", show_alert=True)
                return await cq.message.edit_reply_markup(None)
            g[str(user_id)] -= 1
            left = g[str(user_id)]
            if not left:
                g.pop(str(user_id), None)
            save("warns.json", warns)
            text = mod_text(user, "unwarned", "Unwarn by", by, "", f"{left}/{WARN_LIMIT}")
    except ChatAdminRequired:
        return await cq.answer("ϻαᴋє ϻє αη αᴅϻɪη ωɪᴛн ᴛнє 'вαη υѕєʀѕ' ʀɪɢнᴛ ғɪʀѕᴛ.", show_alert=True)
    except Exception as e:
        return await cq.answer(f"Failed: {e}"[:190], show_alert=True)
    try:
        await cq.message.edit_text(text.replace("\n<b>ʀєαѕση :-</b> ησ ʀєαѕση ɢɪᴠєη", ""), parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await cq.answer("ᴅσηє ")


@bot.on_callback_query(filters.regex(r"^unbanast:"))
async def unban_assistant(_, cq):
    """Unban Assistant button: bot owner, group owner or an admin with the 'Ban Users' right."""
    pid = int(cq.data.split(":")[1])
    ok = bool(OWNER_ID) and cq.from_user.id == OWNER_ID
    if not ok:
        try:
            mem = await bot.get_chat_member(pid, cq.from_user.id)
            ok = mem.status == ChatMemberStatus.OWNER or (
                mem.status == ChatMemberStatus.ADMINISTRATOR
                and mem.privileges is not None and mem.privileges.can_restrict_members)
        except Exception:
            ok = False
    if not ok:
        return await cq.answer("Only admins with the 'Ban Users' right can unban the assistant.", show_alert=True)
    try:
        _, aid = await assistant_info()
        await bot.unban_chat_member(pid, aid)
    except ChatAdminRequired:
        return await cq.answer("Give the bot the 'Ban Users' admin right so it can unban the assistant.", show_alert=True)
    except Exception as e:
        return await cq.answer(f"Failed to unban: {e}"[:190], show_alert=True)
    joined.discard(pid)
    try:
        await ensure_assistant(pid)                 # let it rejoin right away
    except Exception:
        pass                                        # it will retry on the next /play
    me = _player._assistant_me                  # live value (player.py changes it, so do not use a copy)
    name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "Assistant"
    by = _mention_html(cq.from_user.id, cq.from_user.first_name or "Admin")
    try:
        await cq.message.edit_text(
            f"<b>✅ {_mention_html(me.id, name)} Assistant has been unbanned by {by}.</b>\n"
            "Play the song again.", parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await cq.answer("Assistant unbanned ✅")
