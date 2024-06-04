import os, json, asyncio
import config, data

first_time_setup = False
if __name__ == "__main__":
    print(f"{'Freaky ' if config.params['freaky'] else ''}Dynamo v{data.APP_VERSION}")
    if not os.path.exists('config.json'):
        first_time_setup = True
        print("Config file not found! Generating one now.")
        asyncio.run(config.generate_config_py())

import dynamo, splatnet, nso

async def precheck(username: str = None):
    await dynamo.check_for_updates()
    exists = await dynamo.check_login(username)
    if not exists:
        await dynamo.login()

async def main():
    await precheck()
    users = await dynamo.get_users()
    username = users[0]
    await splatnet.check_tokens_and_regenerate(username)

if __name__ == '__main__':
    asyncio.run(main())
    os._exit(0)