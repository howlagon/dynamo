import asyncio
import config, database, dynamo, splatnet, statink, nso, loader

db = database.UserDatabase()

class User:
    def __init__(self, username: str, sleep_time: int = 300, check_all: bool = True, check_vs: bool = True, check_salmon: bool = True) -> None:
        self.username: str = username
        self.bullet_token: str | None = None
        self.g_token: str | None = None
        self.statink_key: str | None = None

        self.check_all: bool = check_all
        self.sleep_time: int = sleep_time or config.params['refresh']
        
        self.loop = [
            self.check_tokens
        ]

        if check_vs:
            self.loop.append(self.find_and_upload_missing_battles)
        if check_salmon:
            self.loop.append(self.find_and_upload_missing_jobs)

    
    async def start(self) -> None:
        if self.statink_key is None:
            await self.set_statink_key()
        
        await self.mainloop()
        self.loader = loader.Loader(f"Sleeping for", count=self.sleep_time, timeout=1, units="seconds")
        self.loader.start()

    async def mainloop(self) -> None:
        for function in self.loop:
            await function()

    async def check_tokens(self) -> None:
        """Checks if the user has valid tokens"""
        await splatnet.check_tokens_and_regenerate(self.username)
    
    async def find_and_upload_missing_battles(self) -> None:
        await dynamo.find_and_upload_missing_battles(self.username, self.check_all)
        self.check_all = False
    
    async def find_and_upload_missing_jobs(self) -> None:
        await dynamo.find_and_upload_missing_jobs(self.username)
    
    async def set_tokens(self) -> None:
        """Sets the user's tokens in the database"""
        self.bullet_token, self.g_token = db[self.username][2], db[self.username][3]
    
    async def set_statink_key(self):
        """Sets the user's stat.ink API key in the database"""
        self.statink_key = db[self.username][5]