from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- custom emoji on buttons (owner only) -----
def _emoji_ids(msg):
    ids = []
    if not msg:
        return ids
    st = getattr(msg, "sticker", None)
    if st and getattr(st, "custom_emoji_id", None):
        ids.append(str(st.custom_emoji_id))
    for e in (getattr(msg, "entities", None) or getattr(msg, "caption_entities", None) or []):
        cid = getattr(e, "custom_emoji_id", None)
        if cid:
            ids.append(str(cid))
    return ids


@bot.on_message(filters.command("emojiid"))
async def emojiid_cmd(_, m):
    if not (OWNER_ID and m.from_user and m.from_user.id == OWNER_ID):
        return
    ids = _emoji_ids(m.reply_to_message) or _emoji_ids(m)
    if not ids:
        return await m.reply_text("Reply to a message that has a premium (custom) emoji or a custom-emoji sticker with /emojiid.",
                                  parse_mode=ParseMode.DISABLED)
    await m.reply_text("\n".join(ids), parse_mode=ParseMode.DISABLED)


@bot.on_message(filters.command("btnemoji"))
async def btnemoji_cmd(_, m):
    if not (OWNER_ID and m.from_user and m.from_user.id == OWNER_ID):
        return
    args = m.command[1:]
    if not args:
        rows = [f"{k} -> {v}" for k, v in sorted(BTN_EMOJI.items())] or ["(none set)"]
        return await m.reply_text(
            "Custom emoji on buttons\n\n/btnemoji <button> (reply to a premium emoji / custom-emoji sticker, or add the emoji id)\n"
            "/btnemoji <button> off (remove)   /btnemoji <button> none (no emoji)\n"
            "/btnemoji all (emoji) = one emoji on EVERY button; a button with its own emoji keeps it.\n\nButton keys: help, help2, help3, grouphelp, ginfohelp, playhelp, autoplayhelp, "
            "sudohelp, blacklisthelp, gbanhelp, gamehelp, ctrlhelp, ownerhelp, "
            "support, update, addme, next1 (Next button of help page 1), back3 (Back button of the last help page). back1 / back2 / back3 (Back of help page 1 / 2 / 3), next1 / next2 (Next of page 1 / 2), backhelp (Back button inside every help detail page), pingsupport (Support button of /ping; uses 'support' if not set). Player: noop (progress), autoplay, resume, pause, loop, skip, stop.\n\nSet now:\n" + "\n".join(rows), parse_mode=ParseMode.DISABLED)
    key = args[0].lower()
    if len(args) > 1 and args[1].lower() in ("none", "hide"):      # keep this button without emoji even if "all" is set
        BTN_EMOJI[key] = ""
        save("btnemoji.json", BTN_EMOJI)
        return await m.reply_text(f"'{key}' will have no emoji.", parse_mode=ParseMode.DISABLED)
    if len(args) > 1 and args[1].lower() in ("off", "remove", "del"):
        BTN_EMOJI.pop(key, None)
        save("btnemoji.json", BTN_EMOJI)
        return await m.reply_text(f"Removed the emoji from '{key}'.", parse_mode=ParseMode.DISABLED)
    ids = _emoji_ids(m.reply_to_message) or _emoji_ids(m)
    if not ids and len(args) > 1 and args[1].isdigit():
        ids = [args[1]]
    if not ids:
        return await m.reply_text("Reply to a premium emoji / custom-emoji sticker, or send the emoji id after the button name.",
                                  parse_mode=ParseMode.DISABLED)
    BTN_EMOJI[key] = ids[0]
    save("btnemoji.json", BTN_EMOJI)
    note = "" if _EMOJI_OK[0] else "\n(This Pyrogram has no custom emoji button support: install Kurigram or Pyrogram-Mod.)"
    await m.reply_text(f"Saved: '{key}' now shows that emoji. Open the menu again to see it.{note}", parse_mode=ParseMode.DISABLED)
