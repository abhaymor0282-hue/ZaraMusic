import importlib

# Every plugin file below is imported once at start-up; importing it registers its commands.
# To add a new command: make a new .py file in one of these folders and add its name here.
PLUGINS = [
    "plugins.bot.start",
    "plugins.bot.help",
    "plugins.play.channel",
    "plugins.play.play",
    "plugins.play.controls",
    "plugins.play.autoplay",
    "plugins.admins.auth",
    "plugins.admins.moderation",
    "plugins.admins.joinrequests",
    "plugins.play.seek",
    "plugins.misc.closemsg",
    "plugins.tools.ping",
    "plugins.tools.leaderboard",
    "plugins.sudo.logger",
    "plugins.sudo.blacklist",
    "plugins.sudo.leave",
    "plugins.sudo.block",
    "plugins.sudo.sudoers",
    "plugins.sudo.stats",
    "plugins.misc.welcome",
    "plugins.admins.adminlist",
    "plugins.admins.groupmgmt",
    "plugins.admins.imposter",
    "plugins.tools.info",
    "plugins.sudo.broadcast",
    "plugins.play.buttons",
    "plugins.tools.identify",
    "plugins.tools.mood",
    "plugins.sudo.emoji",
]


def load_all():
    for name in PLUGINS:
        importlib.import_module(name)
