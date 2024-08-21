import os, json, asyncio, traceback
import config
from tools.data import APP_VERSION
from signal import SIGINT, SIGTERM

first_time_setup = False
if __name__ == "__main__":
    print(f"{'Freaky ' if config.params['freaky'] else ''}Dynamo v{APP_VERSION}")
    if not os.path.exists('config.json'):
        first_time_setup = True
        print("Config file not found! Generating one now.")
        asyncio.run(config.generate_config_py())

# import dynamo, splatnet, nso
import user
from dynamo import get_users

async def main():
    usernames = await get_users()
    users: list[user.User] = [user.User(u) for u in usernames]
    if not usernames:
        print("No users found in the database. Please add some before running the program.")
        return

    while True:
        for u in users:
            await asyncio.create_task(u.start())
        await asyncio.sleep(delay=config.params['refresh'])
        for u in users:
            u.loader.stop()
            del u.loader

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        traceback.print_exc()
    finally:
        os._exit(0)