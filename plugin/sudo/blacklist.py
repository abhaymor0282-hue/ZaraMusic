from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- blacklist (owner only): blocked chats/users cannot use the bot at all -----
def is_blacklisted(chat_id=None, user_id=None):
    return ((chat_id is not None and str(chat_id) in blacklisted)
            or (user_id is not None and (str(user_id) in blacklisted or str(user_id) in blocked_users)))


@bot.on_message(filters.all, group=-3)
async def blacklist_gate_msg(_, m):
    if m.from_user and OWNER_ID and m.from_user.id == OWNER_ID:      # the owner can always use the bot (to /whitelistchat)
        return
    if is_blacklisted(m.chat.id if m.chat else None, m.from_user.id if m.from_user else None):
        m.stop_propagation()


@bot.on_callback_query(group=-3)
async def blacklist_gate_cb(_, cq):
    if OWNER_ID and cq.from_user.id == OWNER_ID:
        return
    if is_blacklisted(cq.message.chat.id if cq.message else None, cq.from_user.id):
        try:
            await cq.answer("🚫 ᴛʜɪs ᴄʜᴀᴛ ᴏʀ ᴜsᴇʀ ɪs ʙʟᴀᴄᴋʟɪsᴛᴇᴅ.", show_alert=True)
        except Exception:
            pass
        cq.stop_propagation()


@bot.on_chat_join_request(group=-3)
async def blacklist_gate_join(_, r):
    if is_blacklisted(r.chat.id, r.from_user.id):
        r.stop_propagation()


@bot.on_chat_member_updated(group=-3)
async def blacklist_gate_member(_, u):
    if not is_blacklisted(u.chat.id):
        return
    try:                                                    # bot was added to a blacklisted chat: leave again
        new = u.new_chat_member
        if new and new.user and new.user.is_self and new.status in (ChatMemberStatus.MEMBER,
                                                                      ChatMemberStatus.ADMINISTRATOR):
            await bot.leave_chat(u.chat.id)
    except Exception:
        pass
    u.stop_propagation()


@bot.on_message(filters.command(["blacklistchat", "whitelistchat", "blacklistedchat"]))
async def blacklist_cmd(_, m):
    if not is_owner(m):
        return
    name = m.command[0].lower()
    if name == "blacklistedchat":
        if not blacklisted:
            return await m.reply_text("📋 ɴᴏ ᴄʜᴀᴛs ᴀʀᴇ ʙʟᴀᴄᴋʟɪsᴛᴇᴅ.")
        lines = [f"{i}. {t} (`{c}`)" for i, (c, t) in enumerate(blacklisted.items(), 1)]
        return await m.reply_text(f"🚫 **ʙʟᴀᴄᴋʟɪsᴛᴇᴅ ᴄʜᴀᴛs** ({len(blacklisted)})\n\n" + "\n".join(lines))
    if len(m.command) > 1:
        arg = m.command[1]
    elif m.chat.type != ChatType.PRIVATE:                   # no id given inside a group: use this group
        arg = str(m.chat.id)
    else:
        arg = ""
    if not re.fullmatch(r"-?\d+", arg):
        return await m.reply_text(f"υѕαɢє: `/{name} <chat id>`\nᴇxᴀᴍᴘʟᴇ: `/{name} -1001234567890`")
    cid = int(arg)
    key = str(cid)
    if name == "whitelistchat":
        if key not in blacklisted:
            return await m.reply_text("ᴛʜɪs ᴄʜᴀᴛ ɪs ɴᴏᴛ ɪɴ ᴛʜᴇ ʙʟᴀᴄᴋʟɪsᴛ.")
        title = blacklisted.pop(key)
        save("blacklist.json", blacklisted)
        return await m.reply_text(f"✅ **{title}** (`{cid}`) ʜᴀs ʙᴇᴇɴ ᴡʜɪᴛᴇʟɪsᴛᴇᴅ. ɪᴛ ᴄᴀɴ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ ᴀɢᴀɪɴ.")
    # blacklistchat
    if OWNER_ID and cid == OWNER_ID:
        return await m.reply_text("👑 ʏᴏᴜ ᴄᴀɴɴᴏᴛ ʙʟᴀᴄᴋʟɪsᴛ ʏᴏᴜʀsᴇʟғ.")
    if key in blacklisted:
        return await m.reply_text("ᴛʜɪs ᴄʜᴀᴛ ɪs ᴀʟʀᴇᴀᴅʏ ʙʟᴀᴄᴋʟɪsᴛᴇᴅ.")
    title = key
    try:
        chat = await bot.get_chat(cid)
        title = chat.title or f"{chat.first_name or ''} {chat.last_name or ''}".strip() or key
    except Exception:
        pass
    blacklisted[key] = title
    save("blacklist.json", blacklisted)
    queues.pop(cid, None)                                   # stop anything playing there
    history.pop(cid, None)
    autoplay.pop(cid, None)
    loops.pop(cid, None)
    try:
        await call.leave_call(cid)
    except Exception:
        pass
    known["chats"].discard(cid)
    known["users"].discard(cid)
    save_known()
    if cid < 0:                                             # group/channel: say goodbye and leave
        try:
            await bot.send_message(cid, "🚫 ᴛʜɪs ᴄʜᴀᴛ ʜᴀs ʙᴇᴇɴ ʙʟᴀᴄᴋʟɪsᴛᴇᴅ ʙʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ. ʟᴇᴀᴠɪɴɢ...")
        except Exception:
            pass
        try:
            await bot.leave_chat(cid)
        except Exception:
            pass
    await m.reply_text(f"🚫 **{title}** (`{cid}`) ʜᴀs ʙᴇᴇɴ ʙʟᴀᴄᴋʟɪsᴛᴇᴅ.\nɪᴛ ᴄᴀɴ ɴᴏ ʟᴏɴɢᴇʀ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ.")
