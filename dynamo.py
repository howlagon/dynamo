import aiohttp, os
from subprocess import call, STDOUT

import data, statink, splatnet, nso
from database import UserDatabase
from loader import Loader

db = UserDatabase()

async def find_missing_battles(username: str, mode: str = 'latest') -> tuple[list, list]:
    """Finds missing battles byh comparing uploaded battles on Stat.ink with all battles on Splatnet"""
    await splatnet.check_tokens_and_regenerate(username)
    loader = Loader(f"Finding missing battles for {username}...", detailed=False).start()
    bullet_token, g_token, stat_ink_api_key = db[username][2], db[username][3], db[username][5]
    uploaded_battles = await statink.fetch_uploaded_battles(stat_ink_api_key)
    all_battles = await splatnet.fetch_battle_ids(bullet_token, g_token, mode)
    missing_battles = [i for i in all_battles if i not in uploaded_battles]
    loader.stop()
    return missing_battles, all_battles

async def upload_missing_battles(username: str, missing_battle_ids: list) -> None:
    """Uploads battles to stat.ink from the list of missing battle IDs"""
    loader = Loader("Uploading missing battles...", detailed=False).start()
    for battle in missing_battle_ids:
        await statink.upload_battle(username, battle)
    loader.stop()

async def check_if_git_installed() -> bool:
    """Checks if git is installed on the system"""
    return call(["git", "--version"], stdout=open(os.devnull, 'w'), stderr=STDOUT) == 0

async def check_if_git_repo() -> bool:
    """Checks if the current directory is a git repository"""
    return os.path.exists(".git")

async def check_for_updates() -> None:
    """Checks if there is an updated version of the script available on Github"""
    loader = Loader("Checking for updates...", detailed=False).start()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://raw.githubusercontent.com/howlagon/dynamo/main/version") as r:
            if r.status != 200:
                loader.stop()
                print("Failed to check for updates!")
                return None
            latest_version = await r.text()
    
    loader.stop()
    if latest_version.strip() == data.APP_VERSION:
        return
    print(f"An updated version of Dynamo is available! (v{latest_version.strip()})")
    if await check_if_git_installed() and await check_if_git_repo():
        update = input("Would you like to update Dynamo? (Y/n): ")
        if update.lower() in ['y', 'yes', '', ' ']:
            call(["git", "pull"])
            print("Dynamo will now restart to apply the update.")
            os._exit(0)
        else:
            print("Run `git pull` to update Dynamo.")
    else:
        print("Please navigate to `https://github.com/howlagon/dynamo` to update Dynamo.")

async def check_login(username: str | None = None) -> bool:
    """Checks if the user exists in the database, or if the database is empty"""
    if username is None:
        return len(db) > 0
    return db[username] is not None

async def login() -> None:
    """Uses nso.LoginManager to walk the user through the login process, then automatically adds the tokens to the database"""
    login_manager = nso.LoginManager()
    has_token = input("Do you have the session token of the user you want to login as? (y/N) ")
    if has_token.lower() in ['y', 'yes']:
        session_token = input("Enter the session token of the user: ")
        login_manager.login_with_token(session_token)
        return
    print('Please consider reading through the "Token Generation" section in the README before proceeding.')
    print('Log in to the following url, right click the "Select this account" button, copy the link address, and then paste it here.')
    data = input(login_manager.login_url + "\n")
    username, session_token, bullet_token, g_token, user_data, stat_ink_key = await login_manager.login(data)
    db[username] = {
        'session_token': session_token,
        'bullet_token': bullet_token,
        'g_token': g_token,
        'user_data': user_data,
        'stat_ink_key': stat_ink_key
    }

async def get_users() -> list:
    """Returns a list of all users in the database"""
    return list([i[0] for i in await db.list()])

async def find_and_upload_missing_battles(username: str, check_all: bool = False) -> None:
    """Finds and uploads all missing battles in the latest battles, and other modes if it's the first time the user is running the script"""
    modes = ["latest"]
    if check_all:
        modes += ["regular", "bankara", 'xmatch', 'event', 'pbs'] 
    missing_battles, all_battles = [], []
    for mode in modes:
        a, b = await find_missing_battles(username, mode)
        missing_battles += a
        all_battles += b
    del a, b
    missing_battle_ids = [all_battles[i] for i in missing_battles]
    if missing_battle_ids:
        await upload_missing_battles(username, missing_battle_ids)
    else:
        print("No missing battles found!")