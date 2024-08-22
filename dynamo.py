import aiohttp, os
from subprocess import call, STDOUT, Popen, PIPE
from packaging.version import Version

import statink, splatnet, nso
from database import UserDatabase
from loader import Loader
from tools.data import APP_VERSION

db = UserDatabase()
exempt_battle_ids = []

async def find_missing_battles(username: str, mode: str = 'latest', enable_loader: bool = True) -> tuple[list, list]:
    """Finds missing battles by comparing uploaded battles on Stat.ink with all battles on Splatnet"""
    # await splatnet.check_tokens_and_regenerate(username)
    loader = Loader(f"Finding missing battles for {username}...", detailed=False, enabled=enable_loader).start()
    bullet_token, g_token, stat_ink_api_key = db[username][2], db[username][3], db[username][5]
    uploaded_battles = await statink.fetch_uploaded_battles(stat_ink_api_key, mode)
    all_battles = await splatnet.fetch_battle_ids(bullet_token, g_token, mode)
    missing_battles = [i for i in all_battles if i not in uploaded_battles and i not in exempt_battle_ids]

    loader.stop()
    return missing_battles, all_battles

async def find_missing_jobs(username: str) -> tuple[list, dict]:
    """Finds missing jobs by comparing uploaded jobs on Stat.ink with all jobs on Splatnet"""
    # await splatnet.check_tokens_and_regenerate(username)
    loader = Loader(f"Finding missing jobs for {username}...", detailed=False).start()
    bullet_token, g_token, stat_ink_api_key = db[username][2], db[username][3], db[username][5]
    uploaded_jobs = await statink.fetch_uploaded_jobs(stat_ink_api_key)
    all_jobs = await splatnet.fetch_job_ids(bullet_token, g_token)
    missing_jobs = [i for i in all_jobs if i not in uploaded_jobs]
    loader.stop()
    return missing_jobs, all_jobs

async def upload_missing_battles(username: str, missing_battle_ids: list, all_battles: dict) -> None:
    """Uploads battles to stat.ink from the list of missing battle IDs"""
    for battle in missing_battle_ids:
        res = await statink.upload_battle(username, battle)
        exempt_battle_ids.append(battle)

async def upload_missing_jobs(username: str, missing_job_ids: list) -> None:
    """Uploads jobs to stat.ink from the list of missing job IDs"""
    # loader = Loader("Uploading missing jobs...", detailed=False).start()
    for job in missing_job_ids:
        await statink.upload_job(username, job)
    # loader.stop()

async def get_git_branch() -> str:
    process = Popen(["git", "branch", "--show-current"], stdout=PIPE)
    branch_name, branch_error = process.communicate()
    return branch_name.decode().strip()

async def check_if_git_installed() -> bool:
    """Checks if git is installed on the system"""
    return call(["git", "--version"], stdout=open(os.devnull, 'w'), stderr=STDOUT) == 0

async def check_if_git_repo() -> bool:
    """Checks if the current directory is a git repository"""
    return os.path.exists(".git")

async def is_dev(is_git: bool) -> bool:
    """Checks if the script is running on the dev branch"""
    if not is_git: return False
    branch = await get_git_branch()
    return branch == "dev"


async def check_for_updates() -> None:
    """Checks if there is an updated version of the script available on Github"""
    loader = Loader("Checking for updates...", detailed=False).start()
    url = "https://raw.githubusercontent.com/howlagon/dynamo/main/version"
    is_git = await check_if_git_installed() and await check_if_git_repo()
    if await is_dev(is_git):
        url = "https://raw.githubusercontent.com/howlagon/dynamo/dev/version"
        
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status != 200:
                loader.stop()
                print("Failed to check for updates!")
                return None
            latest_version = await r.text()
    
    loader.stop()
    if Version(APP_VERSION) >= Version(latest_version.strip()):
        return
        
    print(f"An updated version of Dynamo is available! (v{latest_version.strip()})")
    if is_git:
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

async def get_stat_ink_key(username) -> None:
    stat_ink_key = input("Enter the stat.ink API key you wish to use (or skip, not recommended): ")
    while len(stat_ink_key) != 43 and stat_ink_key.lower != "skip":
        stat_ink_key = input("Invalid API key. Please try again: ")
    
    if stat_ink_key.lower() == "skip":
        return None
    
    db = UserDatabase()
    await db.update(username, "statink_key", stat_ink_key)

async def login() -> None:
    """Uses nso.LoginManager to walk the user through the login process, then automatically adds the tokens to the database"""
    login_manager = nso.LoginManager()
    has_token = input("Do you have the session token of the user you want to login as? (y/N) ")
    if has_token.lower() in ['y', 'yes']:
        session_token = input("Enter the session token of the user: ")
        print("Logging in with the session token... (this may take a while)")
        username, session_token, bullet_token, g_token, user_data, _ = await login_manager.login_with_token(session_token)
    else: #unfortunate
        print('Please consider reading through the "Token Generation" section in the README before proceeding.')
        print('Log in to the following url, right click the "Select this account" button, copy the link address, and then paste it here.')
        data = input(login_manager.login_url + "\n")
        print("Logging in... (this may take a while)")
        username, session_token, bullet_token, g_token, user_data, _ = await login_manager.login(data)

    stat_ink_key = await get_stat_ink_key(username)

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
        modes = ["regular", "bankara", 'x', 'event', 'private'] 
    missing_battles, all_battles = [], {}
    loader = Loader(f"Finding missing battles for {username}...", detailed=False).start()
    for mode in modes:
        loader.update_description( f"Finding missing {mode} battles for {username}")
        a, b = await find_missing_battles(username, mode, enable_loader=False)
        missing_battles += a
        all_battles.update(b)
    loader.update_description(f"Finding missing battles for {username}...")
    loader.stop()
    del a, b
    missing_battle_ids = [all_battles[i] for i in missing_battles]
    if missing_battle_ids:
        await upload_missing_battles(username, missing_battle_ids, all_battles)

async def find_and_upload_missing_jobs(username: str) -> None:
    missing_jobs, all_jobs = await find_missing_jobs(username)
    missing_job_ids = [all_jobs[i] for i in missing_jobs]
    if missing_job_ids:
        await upload_missing_jobs(username, missing_job_ids)