import asyncio, html, json, os, random, re, threading, time
import requests
import aiohttp
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters, raw
from pyrogram.enums import ChatType, ChatMemberStatus, ChatMembersFilter, ParseMode
from pyrogram.errors import (FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid, ChannelPrivate,
                             UserAlreadyParticipant, InviteRequestSent, UserBannedInChannel, ChatAdminRequired)
from pyrogram.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as _IKB, ChatPermissions
from pytgcalls import PyTgCalls, filters as fl
from pytgcalls.types import MediaStream
from yt_dlp import YoutubeDL


# ---------- coloured buttons ----------
# Telegram (Bot API 9.4+) can colour inline buttons: blue / green / red.
# Needs a Pyrogram fork that supports it (e.g. Pyrogram-Mod, Kurigram). On plain Pyrogram the
# colour is skipped silently and the buttons look normal, so the bot never crashes.
BLUE, GREEN, RED = "blue", "green", "red"
_STYLE = {}
try:                                                   # Pyrogram-Mod: KeyboardButtonStyle(bg_primary=True ...)
    from pyrogram.types import KeyboardButtonStyle as _KBS
    _STYLE = {BLUE: _KBS(bg_primary=True), GREEN: _KBS(bg_success=True), RED: _KBS(bg_danger=True)}
except ImportError:
    try:                                               # Kurigram style: enums.ButtonStyle
        from pyrogram.enums import ButtonStyle as _BS
        _STYLE = {BLUE: getattr(_BS, "PRIMARY", None), GREEN: getattr(_BS, "SUCCESS", None),
                  RED: getattr(_BS, "DANGER", None)}
    except ImportError:
        _STYLE = {}


# Newer Pyrogram versions replaced `disable_web_page_preview=True` with `link_preview_options`.
try:
    from pyrogram.types import LinkPreviewOptions as _LPO
    NO_PREVIEW = {"link_preview_options": _LPO(is_disabled=True)}
except ImportError:
    NO_PREVIEW = {"disable_web_page_preview": True}


BTN_EMOJI: dict = {}          # button key -> custom (premium) emoji id; filled from btnemoji.json, set with /btnemoji
_BTN_FALLBACK = {"pingsupport": "support"}      # no own emoji set -> use this key's emoji
_EMOJI_OK = [True]            # turns False if this Pyrogram has no icon_custom_emoji_id support


def _btn_key(text, kw):
    cd = kw.get("callback_data")
    if isinstance(cd, str) and cd:
        return re.split(r"[:|]", cd)[0].lower()          # "grouphelp:0" -> "grouphelp"
    return "url:" + str(text).lower()


def Btn(text, color=None, emoji=None, key=None, **kw):
    """InlineKeyboardButton with an optional colour (BLUE / GREEN / RED) and optional custom emoji icon."""
    extra = {}
    st = _STYLE.get(color)
    if st is not None:
        extra["style"] = st
    k = key or _btn_key(text, kw)
    while k not in BTN_EMOJI and k in _BTN_FALLBACK:
        k = _BTN_FALLBACK[k]
    eid = emoji or (BTN_EMOJI[k] if k in BTN_EMOJI else BTN_EMOJI.get("all"))   # own emoji, else the "all" default
    if eid and _EMOJI_OK[0]:
        extra["icon_custom_emoji_id"] = str(eid)
    while True:
        try:
            return _IKB(text, **extra, **kw)
        except TypeError:                              # this Pyrogram does not know that option: drop it and retry
            if "icon_custom_emoji_id" in extra:
                _EMOJI_OK[0] = False
                extra.pop("icon_custom_emoji_id")
            elif "style" in extra:
                _STYLE.clear()
                extra.pop("style")
            else:
                raise


try:                                            # only used by /ping (RAM / CPU / disk)
    import psutil
    psutil.cpu_percent(None)                    # prime the counter so the first /ping isn't 0%
except ImportError:
    psutil = None

START_TIME = time.time()

# One event loop for everything: Pyrogram clients bind to the loop that exists
# when they are created, so create it first and run main() on this same loop.
LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)

_missing = [k for k in ("API_ID", "API_HASH", "BOT_TOKEN", "SESSION_STRING") if not os.getenv(k)]
if _missing:
    raise SystemExit("Missing environment variables: " + ", ".join(_missing) + " (set them in Railway/Render > Variables)")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION = os.getenv("SESSION_STRING")          # assistant account string session
YT_API_KEY = os.getenv("YOUTUBE_API_KEY")       # optional, only used for search
API_URL = os.getenv("SHRUTI_API_URL", "https://api.shrutibots.in")            # new URL (old .site URLs are being shut down)
API_URL_BACKUP = os.getenv("SHRUTI_API_URL_BACKUP", "https://api.shrutibots.site")  # old URL, only a temporary backup
SHRUTI_API_KEY = os.getenv("SHRUTI_API_KEY", "")  # get it from @SHRUTIAPIBOT
DATA_DIR = os.getenv("DATA_DIR", ".")           # Railway: mount a Volume at /data and set DATA_DIR=/data
START_IMG = os.getenv("START_IMG")              # image URL or file path for /start banner
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/your_support_chat")
UPDATE_URL = os.getenv("UPDATE_URL", "").strip()   # updates channel for the /start "Update" button: https://t.me/xyz or @xyz
if UPDATE_URL and not UPDATE_URL.startswith("http"):
    UPDATE_URL = "https://t.me/" + UPDATE_URL.lstrip("@")
BOT_NAME = os.getenv("BOT_NAME", "Premium Music")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))      # your Telegram user id
LOGGER_ID = int(os.getenv("LOGGER_ID", "0"))    # logger group id (-100...), bot must be a member
PING_IMG = os.getenv("PING_IMG")                # image URL or file path for /ping (falls back to START_IMG)
DEV_NAME = os.getenv("DEV_NAME", "Owner")       # shown as "Developed by" in /ping
DEV_LINK = os.getenv("DEV_LINK", "").strip()    # channel link/username shown on "Developed by": https://t.me/AlexaFamily or @AlexaFamily
if DEV_LINK and not DEV_LINK.startswith("http"):
    DEV_LINK = "https://t.me/" + DEV_LINK.lstrip("@")

bot = Client("musicbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client("assistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION)
call = PyTgCalls(assistant)

queues: dict[int, list] = {}    # play_id (group or channel) -> tracks
origins: dict[int, int] = {}    # play_id -> chat where cards are sent
loops: dict[int, bool] = {}
history: dict[int, list] = {}   # play_id -> already played tracks (for the ⏮️ button), newest last
autoplay: dict[int, bool] = {}  # play_id -> autoplay on/off (plays related songs when the queue runs out)
progress_tasks: dict[int, "asyncio.Task"] = {}   # play_id -> task refreshing the progress button

# ---------- storage ----------
# Default: JSON files in DATA_DIR. If MONGO_URL is set (MongoDB Atlas free tier, or Railway's MongoDB),
# everything is stored in MongoDB instead, so nothing is lost when Railway redeploys (no Volume needed).
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL") or os.getenv("MONGO_URI")
_col = None
if MONGO_URL:
    try:
        from pymongo import MongoClient
        _client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=8000)
        _client.admin.command("ping")
        _col = _client[os.getenv("MONGO_DB", "musicbot")]["kv"]
        print("Storage: MongoDB")
    except Exception as e:
        print("MongoDB not reachable, using local files instead:", e)
        _col = None
_writer = ThreadPoolExecutor(max_workers=1)     # one worker = writes stay in order and the bot never waits for the DB


def _write_db(name, text):
    try:
        _col.replace_one({"_id": name}, {"_id": name, "data": text}, upsert=True)
    except Exception as e:
        print("db save error:", name, e)


def load(name, default):
    if _col is not None:
        try:
            doc = _col.find_one({"_id": name})
            if doc:
                return json.loads(doc["data"])
        except Exception as e:
            print("db load error:", name, e)
    try:
        with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(name, data):
    if _col is not None:
        _writer.submit(_write_db, name, json.dumps(data, ensure_ascii=False))
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


BTN_EMOJI.update(load("btnemoji.json", {}))
channels: dict = load("channels.json", {})  # group_id -> linked channel_id
settings: dict = load("settings.json", {"logger": True})
_t = load("tracked.json", {"users": [], "chats": []})
known = {"users": set(_t.get("users", [])), "chats": set(_t.get("chats", []))}
plays: dict = load("plays.json", {})        # group_id -> {user_id: {"n": songs played, "name": display name}}
authed: dict = load("auth.json", {})        # group_id -> {user_id: display name}  (users allowed to control playback)
blocked_users: dict = load("blocked_users.json", {})   # user id -> display name  (globally banned from the bot)
blacklisted: dict = load("blacklist.json", {})   # chat/user id -> title  (blocked from using the bot)
sudoers: dict = load("sudo.json", {})       # user_id -> display name  (sudo users: only /broadcast, /auth, /stats)


def save_known():
    save("tracked.json", {k: list(v) for k, v in known.items()})
