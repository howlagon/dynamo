import os, json, asyncio, traceback, argparse
import config, user, loader
from tools.data import APP_VERSION
from signal import SIGINT, SIGTERM

first_time_setup = False
if __name__ == "__main__":
    print(f"{'Freaky ' if config.params['freaky'] else ''}Dynamo v{APP_VERSION}")
    if not os.path.exists('config.json'):
        first_time_setup = True
        print("Config file not found! Generating one now.")
        asyncio.run(config.generate_config_py())

from dynamo import get_users, check_for_updates, login, get_stat_ink_key

def parse_args():
    parser = argparse.ArgumentParser(description="Dynamo")
    parser.add_argument("-m", "--monitor", action="store", dest="monitor_time", required=False, nargs="?",
                        help="Monitoring mode, every X seconds (default 300)", const=300)
    parser.add_argument("-s", "--skip-update", action="store_false", dest="check_updates", required=False,
                        help="Skip update checking")
    parser.add_argument("-u", "--user", dest="username", action="store", required=False, nargs="?",
                        help="Specify a single user to monitor")
    parser.add_argument("-sb", "--skip-battles", action="store_false", dest="check_vs", required=False,
                        help="Skip checking multiplayer battles")
    parser.add_argument("-ssr", "--skip-salmon", action="store_false", dest="check_salmon", required=False,
                        help="Skip checking Salmon Run jobs")
    parser.add_argument("-l", "--login", action="store_true", dest="login", required=False,
                        help="Add a new user account")
    parser.add_argument("-t", "--disable-threads", action="store_false", dest="threaded", required=False,
                        help="Disable threading (disables loading animations)")
    parser.add_argument("-k", "--set-key", action="store", dest="set_key", required=False, nargs="?",
                        help="Set stat.ink key for user")
    return parser.parse_args()

async def main():
    parsed = parse_args()
    config.params['threaded'] = parsed.threaded
    if parsed.check_updates:
        await check_for_updates()
    
    if parsed.login:
        await login()
        return
    
    if parsed.set_key is not None:
        key = await get_stat_ink_key(parsed.set_key)
        if key is not None:
            usr = user.User(parsed.set_key)
            await usr.set_statink_key(key)
        return


    if parsed.username is not None:
        usernames = [parsed.username]
    else:
        usernames = await get_users()
    users: list[user.User] = [
        user.User(u, sleep_time=0 if parsed.monitor_time is None else parsed.monitor_time,
                  check_vs=parsed.check_vs, check_salmon=parsed.check_salmon) for u in usernames
        ]
    if not usernames:
        print("No users found in the database. Please run `python main.py -l` to add a user.")
        return
    if len(usernames) > 1:
        config.params['threaded'] = False
        config.params['print_end'] = '\n'
    print(f"Users: {', '.join(usernames)}")

    if parsed.monitor_time is None:
        await asyncio.gather(*[u.start() for u in users])
        return
    
    config.params['refresh'] = int(parsed.monitor_time)
    while True:
        for u in users:
            await asyncio.create_task(u.start())
        if parsed.monitor_time is None:
            break
        load = loader.Loader(desc=f"Sleeping for", count=config.params['refresh'], timeout=1, units="seconds")
        load.start()
        await asyncio.sleep(delay=config.params['refresh'])
        load.stop()
        del load

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        traceback.print_exc()
    else:
        print("Exiting... run `python main.py -M` to monitor.")
    finally:
        os._exit(0)