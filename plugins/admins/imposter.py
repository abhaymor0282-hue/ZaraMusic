from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- imposter watcher: tells the group when someone changes their name or username -----
imposter_chats: dict = load("imposter.json", {})         # group_id -> True (watcher on)
imposter_seen: dict = load("imposter_users.json", {})    # group_id -> {user_id: [full name, username]}


@bot.on_message(filters.command("imposter") & filters.group)
async def imposter_cmd(_, m):
    if not await has_right(m):
        return await deny(m)
    cid = str(m.chat.id)
    arg = m.command[1].lower() if len(m.command) > 1 else ""
    if arg in ("on", "enable", "yes"):
        imposter_chats[cid] = True
        save("imposter.json", imposter_chats)
        return await m.reply_text("🕵 " + f5("Imposter watcher is now ON. I will tell you when someone changes "
                                             "their name or username."), parse_mode=HTML)
    if arg in ("off", "disable", "no"):
        imposter_chats.pop(cid, None)
        save("imposter.json", imposter_chats)
        return await m.reply_text("🕵 " + f5("Imposter watcher is now OFF."), parse_mode=HTML)
    now = "ON" if imposter_chats.get(cid) else "OFF"
    await m.reply_text(f"🕵 {f5('Imposter watcher is')} <b>{f5(now)}</b>.\n" + f5("Use /imposter on or /imposter off."),
                       parse_mode=HTML)


@bot.on_message(filters.group, group=-2)
async def imposter_watch(_, m):
    try:
        u = m.from_user
        cid = str(m.chat.id)
        if not u or u.is_bot or not imposter_chats.get(cid):
            return
        new = [disp_name(u) if (u.first_name or u.last_name) else "", u.username or ""]
        g = imposter_seen.setdefault(cid, {})
        old = g.get(str(u.id))
        if old == new:
            return
        g[str(u.id)] = new
        save("imposter_users.json", imposter_seen)
        if not old:                                          # first time we see this user: just remember
            return
        rows = [f"<b>{f5('User')} :-</b> {_mention_html(u.id, new[0] or 'User')} (<code>{u.id}</code>)"]
        if old[0] != new[0]:
            rows.append(f"<b>{f5('Name')} :-</b> {html.escape(old[0] or '—')} ➜ {html.escape(new[0] or '—')}")
        if old[1] != new[1]:
            rows.append(f"<b>{f5('Username')} :-</b> {'@' + html.escape(old[1]) if old[1] else '—'} ➜ "
                        f"{'@' + html.escape(new[1]) if new[1] else '—'}")
        await m.reply_text(f"🕵 <b>{f5('Imposter alert')}</b>\n\n" + "\n".join(rows), parse_mode=HTML, **NO_PREVIEW)
    except Exception:
        pass
