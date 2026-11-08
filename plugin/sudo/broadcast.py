from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- tracking (for broadcast) -----
@bot.on_message(filters.all, group=-1)
async def track(_, m):
    try:
        if m.chat.type == ChatType.PRIVATE:
            key = "users"
        elif m.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            key = "chats"
        else:
            return
        if m.chat.id not in known[key]:
            known[key].add(m.chat.id)
            save_known()
    except Exception:
        pass


# ----- broadcast (owner only) -----
BC_FLAGS = {"-users", "-groups", "-forward"}


BC_EMOJI_FALLBACK = os.getenv("BC_EMOJI_FALLBACK", "1") == "1"   # premium emoji dropped on copy -> forward instead


def _count_custom(ents):
    return sum(1 for e in ents or [] if getattr(getattr(e, "type", None), "name", str(getattr(e, "type", ""))) == "CUSTOM_EMOJI")


def _custom_emoji_count(msg):
    """How many premium (custom) emoji a message / caption carries."""
    return _count_custom(getattr(msg, "entities", None)) + _count_custom(getattr(msg, "caption_entities", None))


def _shift_entities(entities, shift):
    """Entities of the command message re-based to the broadcast text (offsets are UTF-16 units, like Telegram's)."""
    import copy as _copy
    out = []
    for e in entities or []:
        if e.offset >= shift:
            n = _copy.copy(e)
            n.offset = e.offset - shift
            out.append(n)
    return out


_BC_BTN = re.compile(r"^\s*btn\s*:\s*(.+)$", re.I)


def _utf16_len(t):
    return len(t.encode("utf-16-le")) // 2


def _bc_split_buttons(text):
    """Trailing lines like  btn: Text | https://link  (several buttons in one row: Text | link && Text | link).
    Returns (text without those lines, keyboard or None, error text or None)."""
    lines = text.split("\n")
    rows = []
    while lines and (not lines[-1].strip() or _BC_BTN.match(lines[-1])):
        ln = lines.pop()
        mt = _BC_BTN.match(ln)
        if not mt:
            continue
        row = []
        for part in mt.group(1).split("&&"):
            label, _, url = part.rpartition("|")
            label, url = label.strip(), url.strip()
            if not label or not re.fullmatch(r"(https?://|tg://)\S+", url):
                return text, None, ln.strip()[:70]
            row.append(Btn(label[:60], url=url))
        rows.insert(0, row)
    return "\n".join(lines).rstrip(), (IKM(rows) if rows else None), None


async def _bc_forward(cid, reply):
    """A forward always keeps the photo AND its text exactly as in the post."""
    ids = [reply.id]
    if getattr(reply, "media_group_id", None):                      # album: forward every photo of it, not just one
        try:
            ids = [x.id for x in await reply.get_media_group()] or ids
        except Exception:
            pass
    return await bot.forward_messages(cid, reply.chat.id, ids)


async def bc_send(cid, reply, text, forward, entities=None, state=None, kb=None):
    state = state if state is not None else {}
    while True:
        try:
            if reply:
                if forward or state.get("emoji_forward"):
                    await _bc_forward(cid, reply)
                    if forward and text:                      # /broadcast -forward <text> : the text follows the forwarded photo(s)
                        await bot.send_message(cid, text, entities=entities or None)
                    return
                sent = None
                try:
                    if getattr(reply, "media_group_id", None):          # album: copy all photos with their caption
                        await bot.copy_media_group(cid, reply.chat.id, reply.id)
                        return
                    wp = getattr(reply, "web_page", None)
                    if reply.text and wp and getattr(wp, "url", None):
                        # link post: the photo on top is the link preview -> rebuild it so photo + text both go
                        try:
                            from pyrogram.types import LinkPreviewOptions as _LP
                            pv = {"link_preview_options": _LP(is_disabled=False, url=wp.url, show_above_text=True,
                                                              prefer_large_media=True)}
                        except Exception:
                            pv = {"disable_web_page_preview": False}
                        sent = await bot.send_message(cid, reply.text, entities=reply.entities or None,
                                                      reply_markup=kb, **pv)
                    else:
                        sent = await reply.copy(cid, reply_markup=kb) if kb else await reply.copy(cid)
                except FloodWait:
                    raise
                except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid, ChannelPrivate):
                    raise
                except Exception as e:
                    # copy failed (caption too long for a bot, link preview, etc.): do not lose the post
                    state.setdefault("copy_err", f"{type(e).__name__}: {e}"[:150])
                    print("broadcast copy failed ->", type(e).__name__, e)
                    if kb:                                                   # buttons: send text + keep the photo via forward
                        await _bc_forward(cid, reply)
                        state["btn_emoji_dropped"] = True
                        return
                    await _bc_forward(cid, reply)
                    return
                # photo/video went but its text did not -> redo as a forward so both are there
                if (getattr(reply, "caption", None) or getattr(reply, "text", None)) and not (
                        getattr(sent, "caption", None) or getattr(sent, "text", None)):
                    try:
                        await sent.delete()
                    except Exception:
                        pass
                    await _bc_forward(cid, reply)
                    return
                want = _custom_emoji_count(reply)
                if kb and want and _custom_emoji_count(sent) < want:
                    state["btn_emoji_dropped"] = True        # a forward cannot carry buttons: keep the copy
                elif BC_EMOJI_FALLBACK and want and _custom_emoji_count(sent) < want:
                    # Telegram dropped the premium emoji (a normal bot may not send them): forward this one instead
                    state["emoji_forward"] = True
                    try:
                        await sent.delete()
                    except Exception:
                        pass
                    await _bc_forward(cid, reply)
            else:
                sent = await bot.send_message(cid, text, entities=entities or None, reply_markup=kb)
                want = _count_custom(entities)
                if want and _custom_emoji_count(sent) < want:
                    state["text_emoji_dropped"] = True
            return
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)


async def run_broadcast(status, targets, reply, text, forward, entities=None, kb=None):
    ok = fail = removed = 0
    state = {}
    for key, cid in targets:
        try:
            await bc_send(cid, reply, text, forward, entities, state, kb)
            ok += 1
        except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid, ChannelPrivate):
            known[key].discard(cid)
            removed += 1
        except Exception as e:
            fail += 1
            state.setdefault("err", f"{type(e).__name__}: {e}"[:150])
            print("broadcast failed for", cid, "->", type(e).__name__, e)
        await asyncio.sleep(0.3)
    save_known()
    note = ""
    if fail and state.get("err"):
        note += "\n\n⚠️ ʟᴀꜱᴛ ᴇʀʀᴏʀ: `" + state["err"] + "`"
    if state.get("btn_emoji_dropped"):
        note += "\n\nℹ️ ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏᴊɪ ᴡᴇʀᴇ ꜱʜᴏᴡɴ ᴀꜱ ɴᴏʀᴍᴀʟ ᴇᴍᴏᴊɪ (ʙᴜᴛᴛᴏɴꜱ ᴄᴀɴ'ᴛ ʙᴇ ꜱᴇɴᴛ ᴡɪᴛʜ ᴀ ꜰᴏʀᴡᴀʀᴅ)."
    elif state.get("emoji_forward"):
        note += ("\n\nℹ️ ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏᴊɪ ᴄᴀɴɴᴏᴛ ʙᴇ ᴄᴏᴘɪᴇᴅ ʙʏ ᴀ ɴᴏʀᴍᴀʟ ʙᴏᴛ, ꜱᴏ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡᴀꜱ ꜱᴇɴᴛ "
                "ᴡɪᴛʜ ᴛʜᴇ ꜰᴏʀᴡᴀʀᴅ ᴛᴀɢ ᴛᴏ ᴋᴇᴇᴘ ᴛʜᴇᴍ.")
    elif state.get("text_emoji_dropped"):
        note += ("\n\nℹ️ ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏᴊɪ ᴡᴇʀᴇ ꜱʜᴏᴡɴ ᴀꜱ ɴᴏʀᴍᴀʟ ᴇᴍᴏᴊɪ (ᴀ ʙᴏᴛ ɴᴇᴇᴅꜱ ᴀ ꜰʀᴀɢᴍᴇɴᴛ ᴜꜱᴇʀɴᴀᴍᴇ ᴛᴏ ꜱᴇɴᴅ ᴛʜᴇᴍ). "
                "ʀᴇᴘʟʏ ᴛᴏ ᴛʜᴇ ᴍᴇꜱꜱᴀɢᴇ ᴡɪᴛʜ `/broadcast -forward` ᴛᴏ ᴋᴇᴇᴘ ᴛʜᴇᴍ.")
    await status.edit_text(
        "📢 **Broadcast complete**\n\n"
        f"✅ Sent: `{ok}`\n❌ Failed: `{fail}`\n🗑 Removed (blocked/left): `{removed}`" + note)


@bot.on_message(filters.command("broadcast"))
async def broadcast(_, m):
    await _broadcast_impl(m)


async def _broadcast_impl(m):
    if not is_owner_or_sudo(m):
        return
    raw = m.text.split(None, 1)
    rest = raw[1] if len(raw) > 1 else ""
    flags = set()
    while rest:
        parts = rest.split(None, 1)
        if parts[0].lower() in BC_FLAGS:
            flags.add(parts[0].lower())
            rest = parts[1] if len(parts) > 1 else ""
        else:
            break
    reply = m.reply_to_message
    rest_full = rest
    kb = None
    if rest:
        rest, kb, bad = _bc_split_buttons(rest)
        if bad:
            return await m.reply_text("❌ ʙᴀᴅ ʙᴜᴛᴛᴏɴ ʟɪɴᴇ: `" + bad + "`\nᴜꜱᴇ: `btn: ᴛᴇxᴛ | https://link`")
    if not reply and not rest:
        return await m.reply_text(
            "📢 **Broadcast**\n\n"
            "`/broadcast <text>` - ꜱᴇɴᴅ ᴛᴇxᴛ\n"
            "ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴡɪᴛʜ `/broadcast` - ᴄᴏᴘʏ (ɴᴏ ꜰᴏʀᴡᴀʀᴅ ᴛᴀɢ)\n"
            "ʀᴇᴘʟʏ ᴡɪᴛʜ `/broadcast -forward` - ᴡɪᴛʜ ꜰᴏʀᴡᴀʀᴅ ᴛᴀɢ\n\n"
            "ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏᴊɪ / ꜱᴛɪᴄᴋᴇʀꜱ ꜱᴛᴀʏ ɪɴ ꜰᴏʀᴡᴀʀᴅ ᴍᴏᴅᴇ. ɪɴ ᴄᴏᴘʏ ᴍᴏᴅᴇ ᴛʜᴇʏ ꜱᴛᴀʏ ᴛᴏᴏ, ᴏʀ ᴛʜᴇ ʙᴏᴛ ꜰᴀʟʟꜱ ʙᴀᴄᴋ ᴛᴏ ꜰᴏʀᴡᴀʀᴅ.\n\n"
            "ʙᴜᴛᴛᴏɴꜱ: ᴀᴅᴅ ʟɪɴᴇꜱ ᴀᴛ ᴛʜᴇ ᴇɴᴅ ᴏꜰ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ: `btn: ᴛᴇxᴛ | https://link`\n"
            "ᴏɴᴇ ʟɪɴᴇ = ᴏɴᴇ ʀᴏᴡ, ꜱᴀᴍᴇ ʀᴏᴡ: `btn: ᴀ | ʟɪɴᴋ && ʙ | ʟɪɴᴋ`. ᴡᴏʀᴋꜱ ᴡɪᴛʜ ᴛᴇxᴛ ᴀɴᴅ ᴄᴏᴘʏ, ɴᴏᴛ `-forward`.\n\n"
            "ꜰʟᴀɢꜱ: `-users` (ᴜꜱᴇʀꜱ ᴏɴʟʏ), `-groups` (ɢʀᴏᴜᴘꜱ ᴏɴʟʏ), `-forward`\n"
            "ᴅᴇꜰᴀᴜʟᴛ: ʙᴏᴛʜ ᴜꜱᴇʀꜱ ᴀɴᴅ ɢʀᴏᴜᴘꜱ.")
    forward = "-forward" in flags
    if forward and not reply:
        return await m.reply_text("❌ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴜꜱᴇ `-forward`.")
    if forward and kb:
        return await m.reply_text("❌ ʙᴜᴛᴛᴏɴꜱ ᴄᴀɴ'ᴛ ʙᴇ ᴀᴅᴅᴇᴅ ᴛᴏ ᴀ ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴍᴇꜱꜱᴀɢᴇ. ʀᴇᴍᴏᴠᴇ `-forward` (ᴄᴏᴘʏ ᴍᴏᴅᴇ ᴋᴇᴇᴘꜱ ʙᴜᴛᴛᴏɴꜱ).")
    only_users, only_groups = "-users" in flags, "-groups" in flags
    targets = []
    if only_users or not only_groups:
        targets += [("users", c) for c in known["users"] if str(c) not in blacklisted]
    if only_groups or not only_users:
        targets += [("chats", c) for c in known["chats"] if str(c) not in blacklisted]
    if not targets:
        return await m.reply_text("ɴᴏ ᴛᴀʀɢᴇᴛꜱ ꜰᴏᴜɴᴅ.")
    status = await m.reply_text(
        f"📢 ʙʀᴏᴀᴅᴄᴀꜱᴛ ꜱᴛᴀʀᴛᴇᴅ: `{len(targets)}` ᴄʜᴀᴛꜱ "
        f"({'forward' if forward else 'copy' if reply else 'text'})...")
    ents = None
    if (not reply or forward) and rest and m.entities:                   # /broadcast <text>: keep bold / links / premium emoji
        ents = _shift_entities(m.entities, _utf16_len(m.text[:len(m.text) - len(rest_full)]))
        ents = [e for e in ents if e.offset + e.length <= _utf16_len(rest)] or None   # drop links of the btn: lines
    asyncio.create_task(run_broadcast(status, targets, reply, rest, forward, ents, kb))
