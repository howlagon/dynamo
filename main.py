import os, json, asyncio
import config, data

first_time_setup = False
if __name__ == "__main__":
    print(f"{'Freaky ' if config.params['freaky'] else ''}Dynamo v{data.APP_VERSION}")
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

    for u in users:
        await u.start()

    while True:
        for u in users:
            await u.mainloop()
        await asyncio.sleep(300)

if __name__ == '__main__':
    asyncio.run(main())
    os._exit(0)