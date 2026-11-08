from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- join requests: autoapprove / approveall / pending ----- (admins, group owner, bot owner only)
autoappr: dict = load("autoapprove.json", {})   # chat_id -> True while auto-approval is on
JR_CMDS = ["autoapprove", "approveall", "capproveall", "pendingall", "pendingcount", "clearpending"]
JR_DENIED = " σηʟʏ ɢʀσυᴘ αᴅϻɪηѕ, ᴛнє ɢʀσυᴘ σωηєʀ σʀ ᴛнє вσᴛ σωηєʀ ᴄαη υѕє ᴛнɪѕ."


async def jr_pending(chat_id, limit=10):
    """(total pending, [(user_id, name), ...]) for a chat."""
    peer = await bot.resolve_peer(chat_id)
    r = await bot.invoke(raw.functions.messages.GetChatInviteImporters(
        peer=peer, offset_date=0, offset_user=raw.types.InputUserEmpty(), limit=limit, requested=True))
    users = {u.id: u for u in r.users}
    out = []
    for imp in r.importers:
        u = users.get(imp.user_id)
        name = f"{u.first_name or ''} {u.last_name or ''}".strip() if u else ""
        out.append((imp.user_id, name or "User"))
    return r.count, out


async def jr_all(chat_id, approve):
    peer = await bot.resolve_peer(chat_id)
    await bot.invoke(raw.functions.messages.HideAllChatJoinRequests(peer=peer, approved=approve))


@bot.on_message(filters.command(JR_CMDS) & filters.group)
async def join_requests(_, m):
    cmd = m.command[0].lower()
    if not await is_group_admin(m):
        return await m.reply_text(JR_DENIED)
    chat_id = m.chat.id
    try:
        if cmd == "autoapprove":
            key = str(chat_id)
            arg = m.command[1].lower() if len(m.command) > 1 else ""
            on = (arg == "on") if arg in ("on", "off") else not autoappr.get(key)
            if on:
                autoappr[key] = True
            else:
                autoappr.pop(key, None)
            save("autoapprove.json", autoappr)
            return await m.reply_text(
                f" ᴧυᴛσ-αᴘᴘʀσᴠє ɪѕ ησω **{'ση' if on else 'σғғ'}** ɪη ᴛнɪѕ ᴄнαᴛ."
                + ("\nηєω ᴊσɪη ʀєǫυєѕᴛѕ ωɪʟʟ вє αᴘᴘʀσᴠєᴅ αυᴛσϻαᴛɪᴄαʟʟʏ." if on else ""))

        if cmd == "capproveall":
            target = channels.get(str(chat_id))                  # channel connected with /playchannel
            if not target:
                try:
                    lc = (await bot.get_chat(chat_id)).linked_chat   # or the group's linked channel
                    target = lc.id if lc else None
                except Exception:
                    target = None
            if not target:
                return await m.reply_text(NO_CHANNEL)
            is_bot_owner = bool(OWNER_ID) and m.from_user is not None and m.from_user.id == OWNER_ID
            if not is_bot_owner and not (m.from_user and await is_admin_id(target, m.from_user.id)):
                return await m.reply_text(" ʏσυ ϻυѕᴛ вє αη αᴅϻɪη σғ ᴛнє ʟɪηᴋєᴅ ᴄнαηηєʟ ᴛσσ.")
            chat_id = target

        total, items = await jr_pending(chat_id)
        if cmd == "pendingcount":
            return await m.reply_text(f" ᴘєηᴅɪηɢ ᴊσɪη ʀєǫυєѕᴛѕ: **{total}**")
        if not total:
            return await m.reply_text("ησ ᴘєηᴅɪηɢ ᴊσɪη ʀєǫυєѕᴛѕ.")

        if cmd == "pendingall":
            lines = [f"{i}. {_mention_html(uid, name)} (<code>{uid}</code>)" for i, (uid, name) in enumerate(items, 1)]
            rows = [[Btn(f" ᴧᴄᴄєᴘᴛ{i}", GREEN, key="jr_accept", callback_data=f"jr:a:{chat_id}:{uid}"),
                     Btn(f" ᴅєᴄʟɪηє {i}", RED, key="jr_decline", callback_data=f"jr:d:{chat_id}:{uid}")]
                    for i, (uid, _) in enumerate(items, 1)]
            return await m.reply_text(
                f"<b>ᴘєηᴅɪηɢ ᴊσɪη ʀєǫυєѕᴛѕ ({len(items)} σғ {total} ѕнσωη)</b>\n\n" + "\n".join(lines),
                parse_mode=ParseMode.HTML, reply_markup=IKM(rows))

        approve = cmd in ("approveall", "capproveall")
        await jr_all(chat_id, approve)
        await m.reply_text(f"{' ᴧᴘᴘʀσᴠєᴅ' if approve else ' ᴅєᴄʟɪηєᴅ αηᴅ ᴄʟєαʀєᴅ'} **{total}** ᴘєηᴅɪηɢ ᴊσɪη ʀєǫυєѕᴛ(ѕ).")
    except ChatAdminRequired:
        await m.reply_text(" ϻαᴋє ϻє αη αᴅϻɪη ωɪᴛн ᴛнє 'ɪηᴠɪᴛє υѕєʀѕ ᴠɪα ʟɪηᴋ' ʀɪɢнᴛ ғɪʀѕᴛ.")
    except Exception as e:
        await m.reply_text(f" ғαɪʟєᴅ: {e}")


@bot.on_callback_query(filters.regex(r"^jr:[ad]:"))
async def jr_button(_, cq):
    _, act, chat_s, uid_s = cq.data.split(":")
    chat_id, uid = int(chat_s), int(uid_s)
    is_bot_owner = bool(OWNER_ID) and cq.from_user.id == OWNER_ID
    if not is_bot_owner and not await is_admin_id(chat_id, cq.from_user.id):
        return await cq.answer("σηʟʏ αᴅϻɪηѕ ᴄαη υѕє ᴛнєѕє вυᴛᴛσηѕ.", show_alert=True)
    try:
        if act == "a":
            await bot.approve_chat_join_request(chat_id, uid)
        else:
            await bot.decline_chat_join_request(chat_id, uid)
    except Exception as e:
        return await cq.answer(f"ғαɪʟєᴅ: {e}"[:190], show_alert=True)
    old = cq.message.reply_markup.inline_keyboard if cq.message.reply_markup else []
    rows = [r for r in old if not any((b.callback_data or "").endswith(f":{chat_id}:{uid}") for b in r)]
    try:
        if rows:
            await cq.message.edit_reply_markup(IKM(rows))
        else:
            await cq.message.edit_text(" αʟʟ ʟɪѕᴛєᴅ ᴊσɪη ʀєǫυєѕᴛѕ αʀє нαηᴅʟєᴅ.")
    except Exception:
        pass
    await cq.answer("ᴧᴘᴘʀσᴠєᴅ " if act == "a" else "ᴅєᴄʟɪηєᴅ ")


JR_DM = os.getenv("JR_DM", "1") != "0"           # set JR_DM=0 to turn the join-request DM off


def jr_dm_text(user, chat_title, approved):
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "User"
    status = ("✅ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ᴡᴀꜱ ᴀᴘᴘʀᴏᴠᴇᴅ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ. ᴡᴇʟᴄᴏᴍᴇ ᴀʙᴏᴀʀᴅ! 🥳" if approved else
              "⏳ ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ᴀ ʙɪᴛ, ᴀɴ ᴀᴅᴍɪɴ ᴡɪʟʟ ʀᴇᴠɪᴇᴡ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ꜱᴏᴏɴ.")
    return (
        f"<b>ʜᴇʏ</b> {_mention_html(user.id, name)} 💞\n\n"
        f"<blockquote>ʏᴏᴜ ꜱᴇɴᴅ ʀᴇǫᴜᴇꜱᴛ ᴛᴏ <b>{html.escape(chat_title or 'ᴛʜᴇ ɢʀᴏᴜᴘ')}</b></blockquote>\n\n"
        f"<blockquote>{status}</blockquote>\n\n"
        f"<blockquote>🎧 ᴡʜɪʟᴇ ʏᴏᴜ ᴡᴀɪᴛ, ᴍᴇᴇᴛ <b>{font4(BOT_NAME)}</b> - ꜱᴍᴏᴏᴛʜ ᴍᴜꜱɪᴄ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛꜱ. "
        "ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴏᴡɴ ɢʀᴏᴜᴘ ᴛᴏᴏ! ✨</blockquote>\n\n"
        "<b>ꜰᴏʀ ꜰᴇᴀᴛᴜʀᴇꜱ, ᴛʜᴇɴ /start</b> 👈"
    )


@bot.on_chat_join_request()
async def auto_approve(_, r):
    approved = False
    try:
        _, aid = await assistant_info()
        if r.from_user.id == aid:                                # the assistant's own join is handled in ensure_assistant
            return
        if autoappr.get(str(r.chat.id)):
            await bot.approve_chat_join_request(r.chat.id, r.from_user.id)
            approved = True
    except Exception:
        pass
    if not JR_DM or r.from_user.is_bot:
        return
    try:                                                         # DM the requester (allowed via user_chat_id even if they never started the bot)
        await bot.send_message(getattr(r, "user_chat_id", None) or r.from_user.id,
                               jr_dm_text(r.from_user, r.chat.title, approved),
                               reply_markup=await start_markup(), parse_mode=ParseMode.HTML, **NO_PREVIEW)
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception:
        pass
