# Music Bot

Telegram music bot (Pyrogram + PyTgCalls). Start it with `python main.py`.

## Folders
```
main.py            start file
core.py            env variables, clients, storage, buttons, helpers
player.py          search, download, queue, playback engine, shared helpers
plugins/
  __init__.py      list of all plugins (add a new file's name here)
  bot/             start, help
  play/            play, end, controls (pause/resume), autoplay, seek, channel play, player buttons
  admins/          auth, moderation (ban/mute/warn), join requests, adminlist, group management, imposter watcher
  sudo/            logger, blacklist, leave, block, sudo users, stats, broadcast, button emoji
  tools/           ping, leaderboard, id/info/github, identify, mood
  misc/            welcome, close button
```

## Variables (set them in Heroku Config Vars / Railway Variables, never in the code)
`API_ID`, `API_HASH`, `BOT_TOKEN`, `SESSION_STRING`, `OWNER_ID`, `LOGGER_ID`, `SHRUTI_API_KEY`,
`SUPPORT_URL`, `UPDATE_URL`, `DEV_NAME`, `DEV_LINK`, `BOT_NAME`, `START_IMG`, `MONGO_URL`
