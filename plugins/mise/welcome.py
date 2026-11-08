from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ----- welcome message: /welcome on|off, only the newest welcome stays in the chat -----
welcomedb: dict = load("welcome.json", {"off": {}, "last": {}})   # off: chat_id -> True | last: chat_id -> message id
_welcome_locks: dict = {}
WELCOME_TEXT = (
    "╭━━━「 🌷 ᴡᴇʟᴄᴏᴍᴇ 🌷 」\n"
    "┃\n"
    "┃ ✦ ɴᴀᴍᴇ : {name}\n"
    "┃ ✦ ᴜꜱᴇʀɴᴀᴍᴇ : {username}\n"
    "┃ ✦ ᴜꜱᴇʀ ɪᴅ : {id}\n"
    "┃\n"
    "┃ 💗 ᴇɴᴊᴏʏ ʏᴏᴜʀ ꜱᴛᴀʏ !\n"
    "┃ 🤍 ʙᴇ ᴀᴄᴛɪᴠᴇ &amp; ʀᴇꜱᴘᴇᴄᴛ ᴇᴠᴇʀʏᴏɴᴇ\n"
    "╰━━━━━━━━━━━━━━━━")
WELCOME_BG = os.getenv("WELCOME_BG", "welcome_bg.jpg")   # banner template: its centre circle gets the profile photo
WL_DIR = os.path.join(DOWNLOAD_DIR, "welcome")
_WB_CX, _WB_CY, _WB_R = 800, 248, 183                    # circle of the 1600x500 template: centre x, centre y, radius


def welcome_text(u):
    name = clean_name(u)
    return WELCOME_TEXT.format(
        name=html.escape(name), username=f"@{html.escape(u.username)}" if u.username else "ɴᴏᴛ ꜱᴇᴛ", id=u.id)


def build_welcome_image(pfp_path, name, out):
    """Template banner with the profile photo (or a coloured letter) pasted into its circle."""
    bg = Image.open(WELCOME_BG).convert("RGB")
    cx, cy = int(_WB_CX * bg.width / 1600), int(_WB_CY * bg.height / 500)    # works for other template sizes too
    r = int(_WB_R * bg.width / 1600)
    d = 2 * r
    av = _avatar(pfp_path, name, d)
    big = Image.new("L", (d * 4, d * 4), 0)                                   # 4x mask = smooth circle edge
    ImageDraw.Draw(big).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    mask = big.resize((d, d), getattr(Image, "Resampling", Image).LANCZOS)
    bg.paste(av, (cx - r, cy - r), mask)
    bg.save(out, quality=92)


async def welcome_pic(cid, u):
    """Banner file with the user's photo; no profile photo -> the bot's own photo. None = send text only."""
    if not Image or not os.path.exists(WELCOME_BG):
        return None, []
    os.makedirs(WL_DIR, exist_ok=True)
    mine = os.path.join(WL_DIR, f"{cid}_{u.id}.jpg")
    out = os.path.join(WL_DIR, f"{cid}_{u.id}_banner.jpg")
    pfp = await _profile_pic(u.id, mine)
    if not pfp:
        botpic = os.path.join(WL_DIR, "bot.jpg")
        if not (os.path.exists(botpic) and os.path.getsize(botpic) > 0):
            await _profile_pic("me", botpic)
        pfp = botpic if os.path.exists(botpic) and os.path.getsize(botpic) > 0 else None
    await asyncio.get_running_loop().run_in_executor(None, build_welcome_image, pfp, clean_name(u), out)
    return out, [mine, out]


_welcome_recent: dict = {}      # (chat_id, user_id) -> time: the same person is never welcomed twice (service msg + member update)
WELCOME_KEEP = 45               # seconds: welcomes sent within this time stay together (people who join together)


def _old_welcomes(cid):
    """Stored welcome messages of this chat as [[message id, time], ...] (old files stored a single id)."""
    v = welcomedb.setdefault("last", {}).get(str(cid))
    if not v:
        return []
    if isinstance(v, int):
        return [[v, 0]]
    return [list(x) if isinstance(x, (list, tuple)) else [x, 0] for x in v]


async def send_welcome(cid, u):
    """Welcome ONE member. Works for small and big groups (called from both join events)."""
    if u.is_bot or u.is_deleted or welcomedb.setdefault("off", {}).get(str(cid)):
        return
    now = time.time()
    k = (cid, u.id)
    if now - _welcome_recent.get(k, 0) < 30:
        return
    _welcome_recent[k] = now
    if len(_welcome_recent) > 2000:
        for kk in [kk for kk, t in _welcome_recent.items() if now - t > 120]:
            _welcome_recent.pop(kk, None)
    lock = _welcome_locks.setdefault(cid, asyncio.Lock())
    async with lock:                                        # joins are welcomed one after another
        keep, drop = [], []
        for mid, t in _old_welcomes(cid):
            (keep if time.time() - t < WELCOME_KEEP else drop).append([mid, t])
        if drop:                                            # only older welcomes are removed, a group that joined together all stay
            try:
                await bot.delete_messages(cid, [x[0] for x in drop])
            except Exception:
                pass
        welcomedb["last"][str(cid)] = keep
        text = welcome_text(u)
        uname = await bot_username()
        markup = IKM([[Btn("ᴧᴅᴅ ϻє ɪη ʏσυʀ ɢʀσυᴘ 💗", GREEN, key="addme", url=f"https://t.me/{uname}?startgroup=true")]])
        pic, files = None, []
        try:
            pic, files = await welcome_pic(cid, u)
        except Exception as e:
            print("welcome banner failed:", e)
            pic = None
        sent = None
        try:
            try:
                if pic:
                    sent = await bot.send_photo(cid, pic, caption=text, parse_mode=ParseMode.HTML, reply_markup=markup)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception as e:
                print("welcome photo failed:", e)
            if sent is None:                                # no banner / banner failed: plain text welcome
                sent = await bot.send_message(cid, text, parse_mode=ParseMode.HTML, reply_markup=markup)
        except Exception as e:
            print("welcome send failed:", e)
            return
        finally:
            for f in files:
                try:
                    os.remove(f)
                except OSError:
                    pass
        welcomedb["last"][str(cid)].append([sent.id, time.time()])
        save("welcome.json", welcomedb)


@bot.on_message(filters.new_chat_members & filters.group, group=5)
async def welcome_new(_, m):
    """Small groups: Telegram sends the 'X joined' service message. EVERY new member is welcomed."""
    for u in (m.new_chat_members or []):
        await send_welcome(m.chat.id, u)


@bot.on_chat_member_updated(group=5)
async def welcome_member_update(_, u):
    """Big groups (no join service message) and joins through invite links / approved requests."""
    if u.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    old, new = u.old_chat_member, u.new_chat_member
    if not new or not new.user:
        return
    if new.status not in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED):
        return
    if new.status == ChatMemberStatus.RESTRICTED and getattr(new, "is_member", True) is False:
        return
    if old and old.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        return                                              # was already inside (only a permission change)
    if old and old.status == ChatMemberStatus.RESTRICTED and getattr(old, "is_member", False):
        return
    await send_welcome(u.chat.id, new.user)


@bot.on_message(filters.command("welcome") & filters.group)
async def welcome_cmd(_, m):
    cid = m.chat.id
    uid_ = m.from_user.id if m.from_user else 0
    anon_admin = bool(m.sender_chat and m.sender_chat.id == cid)       # admin posting anonymously
    if not (anon_admin or (uid_ and ((OWNER_ID and uid_ == OWNER_ID) or await is_admin_id(cid, uid_)))):
        return await m.reply_text(" σηʟʏ ɢʀσυᴘ αᴅϻɪηѕ ᴄαη υѕє ᴛнɪѕ.")
    arg = m.command[1].lower() if len(m.command) > 1 else ""
    off = welcomedb.setdefault("off", {})
    if arg == "off":
        off[str(cid)] = True
        save("welcome.json", welcomedb)
        return await m.reply_text(" ωєʟᴄσϻє ϻєѕѕαɢє ɪѕ ησω σғғ.")
    if arg == "on":
        off.pop(str(cid), None)
        save("welcome.json", welcomedb)
        return await m.reply_text(" ωєʟᴄσϻє ϻєѕѕαɢє ɪѕ ησω ση.")
    await m.reply_text(f"ωєʟᴄσϻє ɪѕ ᴄυʀʀєηᴛʟʏ {'σғғ' if off.get(str(cid)) else 'ση'}.\nυѕαɢє: /welcome ση  σʀ  /welcome σғғ")
