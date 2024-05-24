import aiohttp
import aiosqlite
import asyncio
import nest_asyncio
from os.path import exists
from time import time

from config import params

nest_asyncio.apply()

class Cache:
    cache = {}
    """ formatted as 
    cache = {
        (bullet_token, g_token, query): {
            'data': data,
            'expires': timestamp
        }
    }
    """
    @staticmethod
    async def graphql(bullet_token: str, g_token: str, query: str, expires_after: int = 0, return_json: bool = False) -> aiohttp.ClientResponse | dict:
        from splatnet import graphql
        await Cache.purge()
        if (bullet_token, g_token, query) in Cache.cache:
            if Cache.cache[(bullet_token, g_token, query)]['expires'] > time() or Cache.cache[(bullet_token, g_token, query)]['expires'] == -1:
                return Cache.cache[(bullet_token, g_token, query)]['data']
        
        data = await graphql(bullet_token, g_token, query, return_json=return_json)
        expires = int(time()) + (expires_after if expires_after != 0 else params['refresh']) 
        Cache.cache[(bullet_token, g_token, query)] = {
            'data': data,
            'expires': int(time()) + expires
        }
        return data
    
    async def view_battle(vsResultId, bullet_token: str, gtoken: str):
        from splatnet import view_battle
        await Cache.purge()
        if (vsResultId, gtoken) in Cache.cache:
            if Cache.cache[(vsResultId, gtoken)]['expires'] > time() or Cache.cache[(vsResultId, gtoken)]['expires'] == -1:
                return Cache.cache[(vsResultId, gtoken)]['data']
        
        data = await view_battle(vsResultId, bullet_token, gtoken)
        expires = int(time()) + params['refresh']
        Cache.cache[(vsResultId, gtoken)] = {
            'data': data,
            'expires': int(time()) + expires
        }
        return data
    
    async def purge() -> None:
        for key in Cache.cache:
            if Cache.cache[key]['expires'] < time():
                del Cache.cache[key]

class Database:
    async def __aenter__(self) -> aiosqlite.Connection:
        self.database = await aiosqlite.connect(self.database_name)
        return self.database
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            await self.database.commit()
        except:
            pass
    
    def __del__(self):
        try:
            asyncio.run(self.database.close())
        except:
            pass
    
    def __len__(self):
        return asyncio.run(self.length())
    
    def __contains__(self, battle_id):
        return asyncio.run(self.contains(battle_id))
    
    def __delitem__(self, battle_id):
        return asyncio.run(self.delete(battle_id))
    
    async def length(self):
        async with self as database:
            async with database.execute(f"SELECT * FROM {self.table_name}") as cursor:
                return len(await cursor.fetchall())
    
    async def list(self):
        async with self as database:
            async with database.execute(f"SELECT * FROM {self.table_name}") as cursor:
                return await cursor.fetchall()
    
    async def contains(self, battle_id):
        async with self as database:
            async with database.execute(f"SELECT * FROM {self.table_name} WHERE id=?", (battle_id,)) as cursor:
                return await cursor.fetchone() is not None
    
    async def delete(self, battle_id):
        async with self as database:
            if battle_id in self:
                await database.execute(f"DELETE FROM {self.table_name} WHERE id=?", (battle_id,)) 
            await database.commit()
    
    async def close(self):
        await self.database.close()
            
class UserDatabase(Database):
    def __init__(self): 
        self.database_name = "main.db"
        self.table_name = "users"
        self.schema = '("nickname" TEXT PRIMARY KEY UNIQUE NOT NULL, "session_token" TEXT NOT NULL, "bullet_token" TEXT NOT NULL, "g_token" TEXT NOT NULL, "user_data" TEXT NOT NULL, "statink_key" TEXT)'
        if not exists(self.database_name):
            asyncio.run(self.create_table())
    
    def __contains__(self, battle_id):
        return asyncio.run(self.contains(battle_id))
    
    def __delitem__(self, battle_id):
        return asyncio.run(self.delete(battle_id))

    def __getitem__(self, nickname):
        return asyncio.run(self.get(nickname))
    
    def __setitem__(self, nickname, data: dict) -> None:
        asyncio.run(self.set(nickname, data))
    
    async def get(self, nickname):
        async with self as database:
            async with database.execute(f"SELECT * FROM {self.table_name} WHERE nickname=?", (nickname,)) as cursor:
                return await cursor.fetchone()
    
    async def set(self, nickname, data: dict) -> None:
        async with self as database:
            session_token = data['session_token'] if 'session_token' in data else (await self.get(nickname))[1] if nickname in self else None
            bullet_token = data['bullet_token'] if 'bullet_token' in data else (await self.get(nickname))[2] if nickname in self else None
            g_token = data['g_token'] if 'g_token' in data else (await self.get(nickname))[3] if nickname in self else None
            user_data = data['user_data'] if 'user_data' in data else (await self.get(nickname))[4] if nickname in self else None
            statink_key = data['statink_key'] if 'statink_key' in data else (await self.get(nickname))[5] if nickname in self else None
            if nickname in self:
                await database.execute(f"UPDATE {self.table_name} SET session_token=?, bullet_token=?, g_token=?, user_data=?, statink_key=? WHERE nickname=?", (session_token, bullet_token, g_token, user_data, statink_key, nickname,))
            else:
                await database.execute(f"INSERT INTO {self.table_name} VALUES (?, ?, ?, ?, ?, ?)", (nickname, session_token, bullet_token, g_token, user_data, statink_key,))
            await database.commit()

    async def contains(self, nickname):
        async with self as database:
            async with database.execute(f"SELECT * FROM {self.table_name} WHERE nickname=?", (nickname,)) as cursor:
                return await cursor.fetchone() is not None

    async def create_table(self):
        async with self as database:
            await database.execute(f"CREATE TABLE {self.table_name} {self.schema}")
            await database.commit()
