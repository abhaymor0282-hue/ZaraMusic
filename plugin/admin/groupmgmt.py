from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


def cmd_text(m):
    """Text after the command, or the text of the replied-to message."""
    parts = (m.text or m.caption or "").split(None, 1)
    t = parts[1].strip() if len(parts) > 1 else ""
    if not t and m.reply_to_message:
        t = (m.reply_to_message.text or m.reply_to_message.caption or "").strip()
    return t


def view_markup(msg):
    try:
        return IKM([[Btn(f5("View message"), BLUE, key="viewmsg", url=msg.link)]])
    except Exception:
        return None


@bot.on_message(filters.command("pin") & filters.group)
async def pin_cmd(_, m):
    if not await has_right(m, "can_pin_messages"):
        return await deny(m)
    r = m.reply_to_message
    if not r:
        return await m.reply_text(f5("Reply to a message to pin it. Use /pin loud to notify everyone."), parse_mode=HTML)
    loud = any(a.lower() in ("loud", "notify") for a in m.command[1:])
    try:
        await bot.pin_chat_message(m.chat.id, r.id, disable_notification=not loud)
    except Exception as e:
        return await fail(m, e)
    await m.reply_text("📌 " + f5("Pinned the message."), parse_mode=HTML, reply_markup=view_markup(r))


@bot.on_message(filters.command("unpin") & filters.group)
async def unpin_cmd(_, m):
    if not await has_right(m, "can_pin_messages"):
        return await deny(m)
    try:
        r = m.reply_to_message
        if not r:
            r = (await bot.get_chat(m.chat.id)).pinned_message
        if not r:
            return await m.reply_text(f5("There is no pinned message."), parse_mode=HTML)
        await bot.unpin_chat_message(m.chat.id, r.id)
    except Exception as e:
        return await fail(m, e)
    await m.reply_text("📍 " + f5("Unpinned the message."), parse_mode=HTML)


@bot.on_message(filters.command("pinned") & filters.group)
async def pinned_cmd(_, m):
    try:
        pm = (await bot.get_chat(m.chat.id)).pinned_message
    except Exception as e:
        return await fail(m, e)
    if not pm:
        return await m.reply_text(f5("There is no pinned message in this group."), parse_mode=HTML)
    text = "📌 " + f5("Pinned message")
    try:
        await bot.send_message(m.chat.id, text, parse_mode=HTML, reply_to_message_id=pm.id,
                               reply_markup=view_markup(pm))
    except Exception:
        await m.reply_text(text, parse_mode=HTML, reply_markup=view_markup(pm))


@bot.on_message(filters.command("settitle") & filters.group)
async def settitle_cmd(_, m):
    if not await has_right(m, "can_change_info"):
        return await deny(m)
    title = cmd_text(m)
    if not title:
        return await m.reply_text(f5("Usage:") + " <code>/settitle new title</code>", parse_mode=HTML)
    try:
        await bot.set_chat_title(m.chat.id, title[:128])
    except Exception as e:
        return await fail(m, e)
    await m.reply_text("✅ " + f5("Group title updated."), parse_mode=HTML)


@bot.on_message(filters.command(["setdiscription", "setdescription"]) & filters.group)
async def setdesc_cmd(_, m):
    if not await has_right(m, "can_change_info"):
        return await deny(m)
    desc = cmd_text(m)
    if not desc:
        return await m.reply_text(f5("Usage:") + " <code>/setdiscription new description</code>", parse_mode=HTML)
    try:
        await bot.set_chat_description(m.chat.id, desc[:255])
    except Exception as e:
        return await fail(m, e)
    await m.reply_text("✅ " + f5("Group description updated."), parse_mode=HTML)


@bot.on_message(filters.command("setphoto") & filters.group)
async def setphoto_cmd(_, m):
    if not await has_right(m, "can_change_info"):
        return await deny(m)
    r = m.reply_to_message
    is_img = bool(r and (r.photo or (r.document and (r.document.mime_type or "").startswith("image/"))))
    if not is_img:
        return await m.reply_text(f5("Reply to a photo to set it as the group photo."), parse_mode=HTML)
    path = None
    try:
        path = await r.download()
        await bot.set_chat_photo(m.chat.id, photo=path)
    except Exception as e:
        return await fail(m, e)
    finally:
        if path and os.path.exists(path):
            os.remove(path)
    await m.reply_text("✅ " + f5("Group photo updated."), parse_mode=HTML)


@bot.on_message(filters.command("removephoto") & filters.group)
async def removephoto_cmd(_, m):
    if not await has_right(m, "can_change_info"):
        return await deny(m)
    try:
        await bot.delete_chat_photo(m.chat.id)
    except Exception as e:
        return await fail(m, e)
    await m.reply_text("✅ " + f5("Group photo removed."), parse_mode=HTML)


@bot.on_message(filters.command("zombies") & filters.group)
async def zombies_cmd(_, m):
    if not await has_right(m, "can_restrict_members"):
        return await deny(m)
    status = await m.reply_text("🔎 " + f5("Searching for deleted accounts..."), parse_mode=HTML)
    found = []
    try:
        async for mem in bot.get_chat_members(m.chat.id):
            if mem.user.is_deleted and mem.status != ChatMemberStatus.OWNER:
                found.append(mem.user.id)
    except Exception as e:
        if not found:
            return await status.edit_text("❌ " + (f5("I need the admin right to see the members.")
                                                  if isinstance(e, ChatAdminRequired) else html.escape(str(e))[:200]),
                                          parse_mode=HTML)
    if not found:
        return await status.edit_text("✅ " + f5("No deleted accounts found in this group."), parse_mode=HTML)
    await status.edit_text("🧹 " + f5(f"Removing {len(found)} deleted accounts..."), parse_mode=HTML)
    removed = 0
    for user_id in found:
        for _try in range(2):
            try:
                await bot.ban_chat_member(m.chat.id, user_id)
                await bot.unban_chat_member(m.chat.id, user_id)      # kick only, they are not banned for good
                removed += 1
                break
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except ChatAdminRequired:
                return await status.edit_text("❌ " + f5("I need the 'Ban Users' admin right to do this."), parse_mode=HTML)
            except Exception:
                break
        await asyncio.sleep(0.3)
    await status.edit_text("✅ " + f5(f"Removed {removed} deleted accounts from this group."), parse_mode=HTML)
