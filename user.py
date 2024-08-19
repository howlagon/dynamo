import asyncio
import database, dynamo, splatnet, statink, nso

db = database.UserDatabase()

class User:
    def __init__(self, username: str, sleep_time: int = 300) -> None:
        self.username: str = username
        self.status: str | None = None
        self.bullet_token: str | None = None
        self.g_token: str | None = None
        self.statink_key: str | None = None

        self.missing_battles: list = []

        self.check_all: bool = False
        self.sleep_time: int = sleep_time
    
    async def start(self) -> None:
        await self.set_statink_key()
    
    async def mainloop(self) -> None:
        await self.check_tokens()
        await self.find_missing_battles()
        await self.upload_missing_battles()
        asyncio.sleep(self.sleep_time)

    async def check_tokens(self) -> None:
        """Checks if the user has valid tokens"""
        self.status = "Checking tokens..."
        if not await splatnet.check_tokens(self.username):             
            self.status = "Regenerating tokens..."
            await splatnet.generate_tokens(self.username)
            self.status = "Checking tokens..."
            return await splatnet.check_tokens(self.username)
        await self.set_tokens()
        await self.set_statink_key()
    
    async def find_missing_battles(self) -> None:
        self.status = "Finding missing battles..."
        modes = ["latest"]
        if self.check_all: 
            modes = ["regular", "bankara", 'x', 'event', 'private']
            self.check_all = False
        missing_battles, all_battles = [], []
        for mode in modes:
            _mb = await dynamo.find_missing_battles(self.username, mode)
            missing_battles += _mb[0]
            all_battles += _mb[1]
        self.status = None
        self.missing_battles = missing_battles
        
    async def upload_missing_battles(self) -> None:
        self.status = "Uploading missing battles..."
        await dynamo.upload_missing_battles(self.username, self.missing_battles)
        self.status = None
    
    async def set_tokens(self) -> None:
        """Sets the user's tokens in the database"""
        self.status = "Setting tokens..."
        self.bullet_token, self.g_token = db[self.username][2], db[self.username][3]
        self.status = None
    
    async def set_statink_key(self):
        """Sets the user's stat.ink API key in the database"""
        self.status = "Setting stat.ink key..."
        self.statink_key = db[self.username][5]
        self.status = None