from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


# ======================================================================
# /mood  (mood buttons -> language buttons -> 5 songs of that mood are queued)
# ======================================================================
MOOD_COUNT = int(os.getenv("MOOD_COUNT", "5"))          # songs queued per /mood
MOODS = {                                               # key -> (button label, {language: [search queries]})
    "sad": ("😢 Sad", {
        "hindi": ["arijit singh sad songs", "bollywood sad songs", "dard bhare hindi gaane", "hindi heartbreak songs", "atif aslam sad songs", "jubin nautiyal sad songs"],
        "punjabi": ["punjabi sad songs", "sad punjabi songs jass manak", "punjabi dard bhare gaane", "punjabi heartbreak songs"],
        "english": ["english sad songs", "sad english songs heartbreak", "adele sad songs", "lewis capaldi songs", "sam smith sad songs"]}),
    "romantic": ("❤️ Romantic", {
        "hindi": ["hindi romantic songs", "arijit singh romantic songs", "bollywood love songs", "jubin nautiyal romantic songs", "atif aslam love songs"],
        "punjabi": ["punjabi romantic songs", "punjabi love songs", "diljit dosanjh romantic songs", "ap dhillon love songs"],
        "english": ["english romantic songs", "english love songs", "ed sheeran love songs", "taylor swift love songs", "bruno mars romantic songs"]}),
    "party": ("🎉 Party", {
        "hindi": ["bollywood party songs", "hindi dance songs", "bollywood club songs", "badshah party songs", "honey singh party songs"],
        "punjabi": ["punjabi party songs", "punjabi bhangra songs", "diljit dosanjh party songs", "punjabi dj songs"],
        "english": ["english party songs", "english dance hits", "club hits english", "dua lipa party songs", "the weeknd party songs"]}),
    "chill": ("😌 Chill / Lofi", {
        "hindi": ["hindi lofi songs", "bollywood lofi", "hindi chill songs", "arijit singh lofi", "slowed reverb hindi songs"],
        "punjabi": ["punjabi lofi songs", "punjabi chill songs", "punjabi slowed reverb songs"],
        "english": ["english lofi songs", "chill english songs", "lofi hip hop", "chill pop songs", "acoustic chill english"]}),
    "gym": ("💪 Gym / Workout", {
        "hindi": ["hindi gym songs", "bollywood workout songs", "hindi motivational songs", "hindi rap workout songs", "emiway gym songs"],
        "punjabi": ["punjabi gym songs", "punjabi workout songs", "sidhu moose wala motivational songs", "punjabi high energy songs"],
        "english": ["english gym songs", "workout motivation songs", "gym rap songs", "eminem workout songs", "high energy workout songs"]}),
    "travel": ("🚗 Travel", {
        "hindi": ["hindi travel songs", "bollywood road trip songs", "hindi driving songs", "yeh jawaani hai deewani travel songs"],
        "punjabi": ["punjabi road trip songs", "punjabi travel songs", "punjabi driving songs"],
        "english": ["english road trip songs", "english travel songs", "best driving songs english", "road trip playlist english"]}),
    "devotional": ("🙏 Devotional", {
        "hindi": ["hindi bhajan", "shree ram bhajan", "hanuman chalisa bhajan", "krishna bhajan", "shiv bhajan", "aarti songs hindi"],
        "punjabi": ["punjabi shabad", "gurbani shabad kirtan", "waheguru simran shabad", "punjabi dharmik songs"],
        "english": ["english worship songs", "christian worship songs english", "gospel songs english", "hillsong worship songs"]}),
    "sleep": ("😴 Sleep", {
        "hindi": ["hindi sleep songs", "soft hindi songs for sleep", "relaxing hindi songs", "hindi lullaby songs"],
        "punjabi": ["punjabi soft songs", "relaxing punjabi songs", "punjabi calm songs"],
        "english": ["sleep music english songs", "soft english songs for sleep", "relaxing piano music sleep", "calm acoustic songs"]}),
    "attitude": ("🔥 Attitude", {
        "hindi": ["hindi attitude songs", "bollywood swag songs", "hindi rap songs attitude", "divine attitude songs", "badshah attitude songs"],
        "punjabi": ["punjabi attitude songs", "sidhu moose wala attitude songs", "karan aujla attitude songs", "punjabi swag songs"],
        "english": ["english attitude songs", "english rap swag songs", "drake songs", "kanye west songs", "bad girl attitude english songs"]}),
    "retro": ("🎸 Retro", {
        "hindi": ["old hindi songs", "kishore kumar songs", "mohammad rafi songs", "lata mangeshkar songs", "90s bollywood songs", "r d burman songs"],
        "punjabi": ["old punjabi songs", "purane punjabi gaane", "gurdas maan old songs", "kuldeep manak songs"],
        "english": ["70s english hits", "80s english hits", "90s english hits", "classic english rock songs", "queen greatest hits"]}),
}
MOOD_LANGS = {"hindi": "🇮🇳 Hindi", "punjabi": "🌾 Punjabi", "english": "🇬🇧 English", "mix": "🎧 Mix"}
MOOD_ALIASES = {"lofi": "chill", "workout": "gym", "love": "romantic", "bhajan": "devotional", "old": "retro",
                "road": "travel", "swag": "attitude", "dance": "party", "dukhi": "sad", "gana": "party"}
_mood_busy: set = set()


def _mood_markup():
    keys = list(MOODS)
    cols = (BLUE, GREEN, RED)                               # all three colours, rotating
    rows = [[Btn(MOODS[k][0], cols[(i + j) % 3], key="mood_" + k, callback_data=f"mood:{k}") for j, k in enumerate(keys[i:i + 2])]
            for i in range(0, len(keys), 2)]
    rows.append([Btn("ᴄʟσѕє", RED, callback_data="moodclose")])
    return IKM(rows)


def _mood_lang_markup(mood):
    row1 = [Btn(MOOD_LANGS["hindi"], BLUE, key="moodgo_hindi", callback_data=f"moodgo:{mood}:hindi"),
            Btn(MOOD_LANGS["punjabi"], GREEN, key="moodgo_punjabi", callback_data=f"moodgo:{mood}:punjabi")]
    row2 = [Btn(MOOD_LANGS["english"], RED, key="moodgo_english", callback_data=f"moodgo:{mood}:english"),
            Btn(MOOD_LANGS["mix"], BLUE, key="moodgo_mix", callback_data=f"moodgo:{mood}:mix")]
    return IKM([row1, row2, [Btn(f"◁ {f5('Back')}", RED, callback_data="moodmenu")]])


def _mood_queries(mood, lang):
    """MOOD_COUNT different search queries (mix = a bit of every language, best first)."""
    pools = MOODS[mood][1]
    if lang == "mix":
        qs = []
        for lg in ("hindi", "english", "punjabi"):
            lst = pools[lg][:]
            random.shuffle(lst)
            qs += lst[:2]
        random.shuffle(qs)
        return qs[:MOOD_COUNT]
    lst = pools[lang][:]
    random.shuffle(lst)
    return lst[:MOOD_COUNT]


async def _mood_find(mood, lang):
    """Searches the queries, returns [track meta] (no duplicates, a failed search is skipped)."""
    loop = asyncio.get_running_loop()
    qs = _mood_queries(mood, lang)
    res = await asyncio.gather(*[loop.run_in_executor(None, search, q) for q in qs], return_exceptions=True)
    out, seen = [], set()
    for r in res:
        if isinstance(r, dict) and r.get("link") and r["link"] not in seen:
            seen.add(r["link"])
            out.append(r)
    return out


async def _mood_play(chat_id, user, mood, lang, status):
    """Adds the songs of a mood to the queue. `status` is the message that shows progress."""
    label = MOODS[mood][0]
    lang_label = MOOD_LANGS[lang]
    try:
        metas = await _mood_find(mood, lang)
        if not metas:
            return await status.edit_text("❌ " + f5("No songs found for this mood. Try again."))
        name = re.sub(r"[\[\]()`*_~|]", "", f"{user.first_name or ''} {user.last_name or ''}".strip()).strip() or "User"
        added = 0
        for meta in metas:
            prefetch(meta["link"], False) if added == 0 else None
            track = dict(meta, video=False, channel=False, by=user_link(user), by_id=user.id, by_name=name)
            try:
                await add_to_queue(chat_id, chat_id, track)
                added += 1
            except AssistantBanned:
                return await reply_banned(status, chat_id)
            except Exception as e:
                if added == 0:
                    hint = "\nɪѕ ᴛнє ᴠᴄ ση ɪη ᴛнє ɢʀσυᴘ? ɪѕ ᴛнє αѕѕɪѕᴛαηᴛ ɪη ᴛнє ɢʀσυᴘ?"
                    return await status.edit_text(play_fail_text(e, hint))
                break
        await status.edit_text(f"{label} · {lang_label}\n" + f5(f"{added} songs added to the queue."))
        t = asyncio.create_task(delete_after(status, 10))
        _bg_tasks.add(t)
        t.add_done_callback(_bg_tasks.discard)
    except Exception as e:
        print("mood error:", type(e).__name__, e)
        try:
            await status.edit_text("❌ " + f5("Something went wrong. Try again."))
        except Exception:
            pass
    finally:
        _mood_busy.discard(chat_id)


@bot.on_message(filters.command("mood") & filters.group)
async def mood_cmd(_, m):
    if len(m.command) == 1:
        return await m.reply_text("🎵 " + f5("Choose your mood") + " :", reply_markup=_mood_markup())
    mood = m.command[1].lower()
    mood = MOOD_ALIASES.get(mood, mood)
    lang = m.command[2].lower() if len(m.command) > 2 else "mix"
    if mood not in MOODS:
        return await m.reply_text("❌ " + f5("Unknown mood. Moods: ") + ", ".join(MOODS) + "\n" + f5("Example: ") + "/mood sad english")
    if lang not in MOOD_LANGS:
        return await m.reply_text("❌ " + f5("Language must be: ") + "hindi, punjabi, english, mix")
    if m.chat.id in _mood_busy:
        return await m.reply_text("⏳ " + f5("A mood playlist is being added. Wait a moment."))
    _mood_busy.add(m.chat.id)
    status = await m.reply_text(f"{MOODS[mood][0]} · {MOOD_LANGS[lang]}\n" + f5("Finding songs..."))
    await _mood_play(m.chat.id, m.from_user, mood, lang, status)


@bot.on_callback_query(filters.regex(r"^(mood:[a-z]+|moodmenu|moodclose|moodgo:[a-z]+:[a-z]+)$"))
async def mood_buttons(_, cq):
    data = cq.data
    if data == "moodclose":
        try:
            await cq.message.delete()
        except Exception:
            pass
        return await cq.answer()
    if data == "moodmenu":
        await cq.message.edit_text("🎵 " + f5("Choose your mood") + " :", reply_markup=_mood_markup())
        return await cq.answer()
    parts = data.split(":")
    mood = parts[1]
    if mood not in MOODS:
        return await cq.answer()
    if parts[0] == "mood":                                  # step 2: pick the language
        await cq.message.edit_text(f"{MOODS[mood][0]}\n" + f5("Choose a language") + " :", reply_markup=_mood_lang_markup(mood))
        return await cq.answer()
    lang = parts[2]
    if lang not in MOOD_LANGS:
        return await cq.answer()
    chat_id = cq.message.chat.id
    if chat_id in _mood_busy:
        return await cq.answer("A mood playlist is being added. Wait a moment.", show_alert=True)
    _mood_busy.add(chat_id)
    await cq.answer()
    await cq.message.edit_text(f"{MOODS[mood][0]} · {MOOD_LANGS[lang]}\n" + f5("Finding songs..."))
    await _mood_play(chat_id, cq.from_user, mood, lang, cq.message)
