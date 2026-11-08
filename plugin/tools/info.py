from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- /id /info /github -----
def _row(label, value):
    return f"<b>{f5(label)} :-</b> {value}"


@bot.on_message(filters.command("id"))
async def id_cmd(_, m):
    rows = []
    if m.chat.type != ChatType.PRIVATE:
        rows.append(_row("Group id", f"<code>{m.chat.id}</code>"))
    if m.from_user:
        rows.append(_row("Your id", f"<code>{m.from_user.id}</code>"))
    r = m.reply_to_message
    if r:
        if r.from_user:
            rows.append(_row("Replied user id", f"<code>{r.from_user.id}</code>"))
        elif r.sender_chat:
            rows.append(_row("Replied chat id", f"<code>{r.sender_chat.id}</code>"))
        fwd = getattr(r, "forward_from", None)
        if fwd:
            rows.append(_row("Forwarded from id", f"<code>{fwd.id}</code>"))
        rows.append(_row("Message id", f"<code>{r.id}</code>"))
    else:
        rows.append(_row("Message id", f"<code>{m.id}</code>"))
    await m.reply_text("\n".join(rows), parse_mode=HTML)


@bot.on_message(filters.command("info"))
async def info_cmd(_, m):
    args = m.command[1:]
    try:
        if m.reply_to_message and m.reply_to_message.from_user:
            user = m.reply_to_message.from_user
        elif args:
            a = args[0]
            user = await bot.get_users(int(a) if a.lstrip("-").isdigit() else a)
        else:
            user = m.from_user
    except Exception:
        return await m.reply_text("❌ " + f5("User not found."), parse_mode=HTML)
    if not user:
        return await m.reply_text("❌ " + f5("User not found."), parse_mode=HTML)
    bio = ""
    try:
        bio = (await bot.get_chat(user.id)).bio or ""
    except Exception:
        pass
    rows = [_row("First name", html.escape(user.first_name or "—")),
            _row("Last name", html.escape(user.last_name or "—")),
            _row("User id", f"<code>{user.id}</code>"),
            _row("Username", f"@{html.escape(user.username)}" if user.username else "—"),
            _row("Mention", _mention_html(user.id, disp_name(user)))]
    if getattr(user, "dc_id", None):
        rows.append(_row("Dc id", str(user.dc_id)))
    if bio:
        rows.append(_row("Bio", html.escape(bio[:200])))
    flags = [n for n, k in (("Bot", "is_bot"), ("Premium", "is_premium"), ("Verified", "is_verified"),
                            ("Scam", "is_scam"), ("Fake", "is_fake"), ("Deleted", "is_deleted"))
             if getattr(user, k, False)]
    if flags:
        rows.append(_row("Tags", ", ".join(f5(f) for f in flags)))
    if m.chat.type != ChatType.PRIVATE:
        try:
            mem = await bot.get_chat_member(m.chat.id, user.id)
            rows.append(_row("Status in group", f5(mem.status.name.title())))
        except Exception:
            pass
    await m.reply_text(f"<b><u>⦾ {f5('User info')} :</u></b>\n\n<blockquote>" + "\n".join(rows) + "</blockquote>",
                       parse_mode=HTML, **NO_PREVIEW)


def _gh_fetch(name):
    r = requests.get(f"https://api.github.com/users/{name}", timeout=15,
                     headers={"User-Agent": "musicbot", "Accept": "application/vnd.github+json"})
    return r.status_code, (r.json() if r.status_code == 200 else {})


@bot.on_message(filters.command("github"))
async def github_cmd(_, m):
    name = m.command[1].lstrip("@") if len(m.command) > 1 else ""
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", name):
        return await m.reply_text(f5("Usage:") + " <code>/github username</code>", parse_mode=HTML)
    try:
        code, d = await asyncio.get_running_loop().run_in_executor(None, _gh_fetch, name)
    except Exception as e:
        return await m.reply_text("❌ " + html.escape(str(e))[:200], parse_mode=HTML)
    if code == 404:
        return await m.reply_text("❌ " + f5("GitHub user not found."), parse_mode=HTML)
    if code != 200:
        return await m.reply_text("❌ " + f5(f"GitHub error {code}. Try again later."), parse_mode=HTML)

    def val(k, n=200):
        return html.escape(str(d.get(k) or "—")[:n])

    rows = [_row("Name", val("name")), _row("Username", f"<code>{val('login')}</code>"),
            _row("Bio", val("bio")), _row("Company", val("company")), _row("Location", val("location")),
            _row("Blog", val("blog")), _row("Public repos", val("public_repos")),
            _row("Followers", val("followers")), _row("Following", val("following")),
            _row("Created", html.escape((d.get("created_at") or "—")[:10]))]
    caption = f"<b><u>⦾ {f5('Github info')} :</u></b>\n\n<blockquote>" + "\n".join(rows) + "</blockquote>"
    markup = IKM([[Btn(f5("Open profile"), BLUE, key="profile", url=d.get("html_url") or f"https://github.com/{name}")]])
    if d.get("avatar_url"):
        try:
            return await m.reply_photo(d["avatar_url"], caption=caption, parse_mode=HTML, reply_markup=markup)
        except Exception:
            pass
    await m.reply_text(caption, parse_mode=HTML, reply_markup=markup, **NO_PREVIEW)
