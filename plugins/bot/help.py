from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


assert len(_F5) == len(_F2) == 26


def font2(text):
    return "".join(_F2.get(c.lower(), c) for c in text)


# ---------- help page 2: Group / Info / Font ----------
def _hp_title(t):
    return f"<b><u>⦾ {f5(t)} :</u></b>\n\n"


def _hp_block(lines):
    return "<blockquote>" + "\n".join(f"➻ {c} : {f5(d)}" for c, d in lines) + "</blockquote>"


GROUP_HELP_TEXT = (
    _hp_title("Group commands")
    + "<blockquote>💮 " + f5("These are the available group management commands.") + "</blockquote>\n\n"
    + _hp_block([
        ("/pin", "pins a message in the group."),
        ("/pinned", "displays the pinned message in the group."),
        ("/unpin", "unpins the currently pinned message."),
        ("/staff", "displays the list of staff members."),
        ("/bots", "displays the list of bots in the group."),
        ("/settitle", "sets the title of the group."),
        ("/setdiscription", "sets the description of the group."),
        ("/setphoto", "sets the group photo."),
        ("/removephoto", "removes the group photo."),
        ("/zombies", "removes deleted accounts from the group."),
        ("/imposter on/off", "turns on or off the watcher for your group, which notifies about users "
                             "who change their name or username."),
    ])
)

GINFO_HELP_TEXT = (
    _hp_title("Info commands")
    + "<blockquote>💮 " + f5("Get the ids and details of users and groups.") + "</blockquote>\n\n"
    + _hp_block([
        ("/id", "get the current group id. If used by replying to a message, gets that user's id."),
        ("/info", "get information about a user."),
        ("/github &lt;username&gt;", "get information about a github user."),
    ])
)

HELP2_TEXT = HELP_TEXT

SUDO_HELP_TEXT = (
    "<u>‣ sᴜᴅᴏ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ :</u>\n\n"
    "<blockquote>"
    "➻ /sudo : ᴀᴅᴅ ᴀ ɴᴇᴡ sᴜᴅᴏ ᴜsᴇʀ ᴛᴏ ʙᴏᴛ.\n"
    "➻ /rmsudo : ʀᴇᴍᴏᴠᴇ ᴀ ᴜsᴇʀ ғʀᴏᴍ sᴜᴅᴏ ʟɪsᴛ.\n"
    "➻ /sudolist : ᴄʜᴇᴄᴋ ᴀʟʟ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ sᴜᴅᴏ ᴜsᴇʀs."
    "</blockquote>\n\n"
    "<blockquote>❏ ᴛʜᴇsᴇ ᴄᴏᴍᴍᴀɴᴅs ᴀʀᴇ ʜɪɢʜʟʏ sᴇɴsɪᴛɪᴠᴇ, ᴜsᴇ ᴡɪᴛʜ ᴄᴀʀᴇ.</blockquote>"
)

PLAY_HELP_TEXT = (
    "<u>⊚ ᴘʟᴀʏ &amp; ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ :</u>\n\n"
    "<blockquote>"
    "➻ /play : sᴛᴀʀᴛ ᴀᴜᴅɪᴏ sᴛʀᴇᴀᴍɪɴɢ ɪɴ ᴄʜᴀᴛ.\n"
    "➻ /vplay : sᴛᴀʀᴛ ᴠɪᴅᴇᴏ sᴛʀᴇᴀᴍɪɴɢ ɪɴ ᴄʜᴀᴛ.\n"
    "➻ /forceplay : ɪɴsᴛᴀɴᴛ ᴘʟᴀʏ (ᴏᴠᴇʀʀɪᴅᴇs ǫᴜᴇᴜᴇ)."
    "</blockquote>\n\n"
    "<u>⊚ ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ :</u>\n\n"
    "<blockquote>"
    "➻ /cplay : ᴀᴜᴅɪᴏ sᴛʀᴇᴀᴍ ɪɴ ʟɪɴᴋᴇᴅ ᴄʜᴀɴɴᴇʟ.\n"
    "➻ /vcplay : ᴠɪᴅᴇᴏ sᴛʀᴇᴀᴍ ɪɴ ʟɪɴᴋᴇᴅ ᴄʜᴀɴɴᴇʟ.\n"
    "➻ /cforceplay : ғᴏʀᴄᴇ sᴛʀᴇᴀᴍ ɪɴ ʟɪɴᴋᴇᴅ ᴄʜᴀɴɴᴇʟ.\n"
    "➻ /playchannel [ɪᴅ] : ᴄᴏɴɴᴇᴄᴛ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ."
    "</blockquote>"
)

AUTOPLAY_HELP_TEXT = (
    "<u>⊚ ᴀᴜᴛᴏᴘʟᴀʏ ᴄᴏɴᴛʀᴏʟ :</u>\n\n"
    "<blockquote>"
    "➻ /autoplay : ᴛᴏɢɢʟᴇ ᴛʜᴇ ᴀᴜᴛᴏᴘʟᴀʏ sᴇᴛᴛɪɴɢs ᴘᴀɴᴇʟ.\n"
    "➻ /askip : ᴘʟᴀʏ ᴛʜᴇ ɴᴇxᴛ ᴛʀᴀᴄᴋ ɪɴ ᴛʜᴇ ᴀᴜᴛᴏᴘʟᴀʏ ǫᴜᴇᴜᴇ."
    "</blockquote>\n\n"
    "<u>⊚ ᴡʜᴀᴛ ɪs ᴀᴜᴛᴏᴘʟᴀʏ?</u>\n\n"
    "<blockquote>"
    "💮 ᴀᴜᴛᴏᴘʟᴀʏ sᴇᴀᴍʟᴇssʟʏ ᴀᴅᴅs ʀᴇʟᴀᴛᴇᴅ ᴛʀᴀᴄᴋs ᴛᴏ ᴛʜᴇ ǫᴜᴇᴜᴇ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ᴘʟᴀʏʟɪsᴛ "
    "ғᴏʀ ɴᴏɴ-sᴛᴏᴘ ᴍᴜsɪᴄ."
    "</blockquote>\n\n"
    "<u>๏ ᴘᴀɴᴇʟ ᴏᴘᴛɪᴏɴs :</u>\n\n"
    "<blockquote>"
    "• ᴇɴᴀʙʟᴇ : ᴀᴄᴛɪᴠᴀᴛᴇ sᴍᴀʀᴛ ʀᴇᴄᴏᴍᴍᴇɴᴅᴀᴛɪᴏɴs.\n"
    "• ᴅɪsᴀʙʟᴇ : ᴅᴇᴀᴄᴛɪᴠᴀᴛᴇ sᴍᴀʀᴛ ʀᴇᴄᴏᴍᴍᴇɴᴅᴀᴛɪᴏɴs.\n"
    "• ᴄʟᴏsᴇ : ᴇxɪᴛ ᴛʜᴇ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ."
    "</blockquote>\n\n"
    "<u>๏ ɴᴏᴛᴇ : ʀᴇǫᴜɪʀᴇs ᴀᴛ ʟᴇᴀsᴛ ᴏɴᴇ ᴀᴄᴛɪᴠᴇ sᴏɴɢ ᴛᴏ ғᴜɴᴄᴛɪᴏɴ.</u>"
)

BLACKLIST_HELP_TEXT = (
    "<u>⊚ ʙʟᴀᴄᴋʟɪsᴛ :</u>\n\n"
    "<blockquote>💮 ʀᴇsᴛʀɪᴄᴛ sᴘᴇᴄɪғɪᴄ ᴄʜᴀᴛs ᴏʀ ᴜsᴇʀs ғʀᴏᴍ ᴜsɪɴɢ ᴛʜᴇ ʙʟᴀᴄᴋʟɪsᴛ.</blockquote>\n\n"
    "<u>‣ ᴄʜᴀᴛ ʙʟᴀᴄᴋʟɪsᴛ :</u>\n\n"
    "<blockquote>"
    "➻ /blacklistchat : [ᴄʜᴀᴛ ɪᴅ] ʙᴀɴ ᴀ ᴄʜᴀᴛ ғʀᴏᴍ ᴜsɪɴɢ ʙᴏᴛ.\n"
    "➻ /whitelistchat : [ᴄʜᴀᴛ ɪᴅ] ᴜɴʙᴀɴ ᴀ ʙʟᴀᴄᴋʟɪsᴛᴇᴅ ᴄʜᴀᴛ.\n"
    "➻ /blacklistedchat : sʜᴏᴡ ᴀʟʟ ʙʟᴀᴄᴋʟɪsᴛᴇᴅ ɢʀᴏᴜᴘs."
    "</blockquote>"
)

GBAN_HELP_TEXT = (
    "<u>⊚ ɢʟᴏʙᴀʟ ʙᴀɴ :</u>\n\n"
    "<blockquote>💮 ʀᴇsᴛʀɪᴄᴛ sᴘᴇᴄɪғɪᴄ ᴄʜᴀᴛs ᴏʀ ᴜsᴇʀs ғʀᴏᴍ ᴜsɪɴɢ ᴛʜᴇ ʙᴏᴛ ɢʟᴏʙᴀʟʟʏ.</blockquote>\n\n"
    "<u>‣ ᴜsᴇʀ ʙʟᴏᴄᴋ :</u>\n\n"
    "<blockquote>"
    "➻ /block : [ᴜsᴇʀɴᴀᴍᴇ/ɪᴅ] sᴛᴏᴘ ᴜsᴇʀ ғʀᴏᴍ ᴜsɪɴɢ ʙᴏᴛ.\n"
    "➻ /unblock : [ᴜsᴇʀɴᴀᴍᴇ/ɪᴅ] ᴀʟʟᴏᴡ ᴛʜᴇ ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀ.\n"
    "➻ /blockedusers : ᴠɪᴇᴡ ᴛʜᴇ ʟɪsᴛ ᴏғ ᴀʟʟ ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs."
    "</blockquote>"
)

GAME_HELP_TEXT = (
    "<u>⊚ " + f5("Identify") + " :</u>\n\n"
    "<blockquote>"
    "➻ /identify : " + f5("reply to a song / voice note / video to find its name.")
    + "</blockquote>"
)

CTRL_HELP_TEXT = (
    _hp_title("Music controls")
    + "<blockquote>💮 " + f5("Control the song that is playing. Admins and /auth users only (except /queue).") + "</blockquote>\n\n"
    + _hp_block([
        ("/pause", "pause the song."),
        ("/resume", "resume the song."),
        ("/skip", "play the next song."),
        ("/end , /stop", "stop the stream and clear the queue."),
        ("/loop", "turn loop on or off."),
        ("/queue", "show the queue (everyone)."),
        ("/forceplay &lt;song&gt;", "play now and replace the current song. /vforceplay for video."),
        ("/cpause /cresume /cskip /cend /cloop /cqueue", "same controls for the channel voice chat."),
    ])
)

OWNER_HELP_TEXT = (
    _hp_title("Owner commands")
    + "<blockquote>💮 " + f5("Only the bot owner can use these.") + "</blockquote>\n\n"
    + _hp_block([
        ("/logger on|off", "turn the play logger on or off."),
        ("/leave &lt;chat id&gt;", "say goodbye and leave a group (or /leave inside the group)."),
        ("/stats", "bot statistics (owner and sudo users)."),
    ])
)

HELP2_PAGES = {"grouphelp": GROUP_HELP_TEXT, "ginfohelp": GINFO_HELP_TEXT, "sudohelp": SUDO_HELP_TEXT, "playhelp": PLAY_HELP_TEXT, "autoplayhelp": AUTOPLAY_HELP_TEXT,
               "blacklisthelp": BLACKLIST_HELP_TEXT, "gbanhelp": GBAN_HELP_TEXT, "ctrlhelp": CTRL_HELP_TEXT, "ownerhelp": OWNER_HELP_TEXT, "gamehelp": GAME_HELP_TEXT}


def help2_markup(from_start):
    n = int(from_start)
    return IKM([
        [Btn(f5("˹Group˼"), GREEN, callback_data=f"grouphelp:{n}"),
         Btn(f5("˹Info˼"), BLUE, callback_data=f"ginfohelp:{n}")],
        [Btn("˹ᴘʟᴀʏ˼", RED, callback_data=f"playhelp:{n}"),
         Btn("˹ᴀᴜᴛᴏᴘʟᴀʏ˼", GREEN, callback_data=f"autoplayhelp:{n}"),
         Btn("˹sᴜᴅᴏ˼", BLUE, callback_data=f"sudohelp:{n}")],
        [Btn("˹ʙ-ʟɪsᴛ˼", BLUE, callback_data=f"blacklisthelp:{n}"),
         Btn("˹ɢ-ʙᴀɴ˼", RED, callback_data=f"gbanhelp:{n}")],
        [Btn(f" {f5('˹Back˼')}", RED, key="back2", callback_data=f"help:{n}"),
         Btn(f"{f5('˹Next˼')} ", BLUE, key="next2", callback_data=f"help3:{n}")],      # page 3: Identify / Music / Owner
    ])


def help3_markup(from_start):
    n = int(from_start)
    return IKM([
        [Btn(f5("˹Identify˼"), BLUE, callback_data=f"gamehelp:{n}"),
         Btn(f5("˹Music˼"), RED, callback_data=f"ctrlhelp:{n}"),
         Btn(f5("˹Owner˼"), GREEN, callback_data=f"ownerhelp:{n}")],
        [Btn(f" {f5('˹Back˼')}", BLUE, key="back3", callback_data=f"help2:{n}")],
    ])


@bot.on_callback_query(filters.regex(r"^(help2|help3|grouphelp|ginfohelp|sudohelp|playhelp|autoplayhelp|blacklisthelp|gbanhelp|gamehelp|ctrlhelp|ownerhelp):[01]$"))
async def help2_home(_, cq):
    key, n = cq.data.split(":")
    if key == "help2":                                   # page 2 (opened with the Next button)
        await edit_any(cq.message, HELP2_TEXT, help2_markup(n == "1"), ParseMode.HTML)
    elif key == "help3":                                 # page 3: Identify / Music / Owner (opened with the Next button of page 2)
        await edit_any(cq.message, HELP2_TEXT, help3_markup(n == "1"), ParseMode.HTML)
    else:                                                # a help page; Identify / Music / Owner go back to page 3, the rest to page 2
        back = "help3" if key in ("gamehelp", "ctrlhelp", "ownerhelp") else "help2"
        await edit_any(cq.message, HELP2_PAGES[key],
                       IKM([[Btn(f"◁ {f5('Back')}", RED, key="backhelp", callback_data=f"{back}:{n}")]]), ParseMode.HTML)
    await cq.answer()
