import os, json, asyncio
import config, data

if __name__ == "__main__":
    print(f"{'Freaky ' if config.params['freaky'] else ''}Dynamo v{data.APP_VERSION}")
    if not os.path.exists('config.json'):
        print("Config file not found! Generating one now.")
        asyncio.run(config.generate_config_py())

import dynamo, nso

# if __name__ == "__main__":
#     print(f"{'Freaky ' if config.params['freaky'] else ''}Dynamo v{data.APP_VERSION}")
#     try:
#         asyncio.run(dynamo.main('howlagon'))
#     except KeyboardInterrupt:
#         print("a")
#         os._exit(1)
#     os._exit(0)
# os._exit(0)    

# from splatnet import graphql, view_battle
# from database import UserDatabase

# db = UserDatabase()

async def main():
    print(f"{'Freaky ' if config.params['freaky'] else ''}Dynamo v{data.APP_VERSION}")

if __name__ == '__main__':
    asyncio.run(main())
    os._exit(0)