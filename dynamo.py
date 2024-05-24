import statink, splatnet, nso, asyncio
from database import UserDatabase
from loader import Loader

db = UserDatabase()

async def find_missing_battles(username: str) -> list:
    await splatnet.check_tokens_and_regenerate(username)
    loader = Loader(f"Finding missing battles for {username}...", detailed=False).start()
    bullet_token, gtoken, stat_ink_api_key = db[username][2], db[username][3], db[username][5]
    uploaded_battles = await statink.fetch_uploaded_battles(stat_ink_api_key)
    all_battles = await splatnet.fetch_battle_ids(bullet_token, gtoken, 'latest')
    missing_battles = [i for i in all_battles if i not in uploaded_battles]
    loader.stop()
    return missing_battles, all_battles

async def upload_missing_battles(username, missing_battle_ids: list) -> None:
    loader = Loader("Uploading missing battles...", detailed=False).start()
    for battle in missing_battle_ids:
        await statink.upload_battle(username, battle)
    loader.stop()

async def main(username: str) -> None:
    missing_battles, all_battles = await find_missing_battles(username)
    missing_battle_ids = [all_battles[i] for i in missing_battles]
    if missing_battle_ids:
        await upload_missing_battles(username, missing_battle_ids)
    else:
        print("No missing battles found!")

async def test(username):
    await splatnet.check_tokens_and_regenerate(username)
    bullet_token, gtoken = db[username][2], db[username][3]
    all_battles = await splatnet.fetch_battle_ids(bullet_token, gtoken, 'latest')
    missing_battle_ids = [all_battles[i] for i in all_battles]
    print("\n", missing_battle_ids)
    return 