from core import *
from player import *
import core as _core, player as _player
globals().update({k: v for _m in (_core, _player) for k, v in vars(_m).items() if not k.startswith("__")})


import plugins
plugins.load_all()


async def main():
    await bot.start()
    await assistant.start()
    await call.start()
    print("Music bot running")
    if LOGGER_ID:
        try:
            await bot.send_message(LOGGER_ID, f"✅ **{BOT_NAME}** started and logger is active.")
        except Exception as e:
            print("Logger group not reachable:", e)
    from pytgcalls import idle
    await idle()


if __name__ == "__main__":
    LOOP.run_until_complete(main())
