import aiohttp, json
import nso, utils
from database import UserDatabase
from loader import Loader

db = UserDatabase()

async def generate_tokens(nickname) -> dict:
    with Loader(f"Regenerating tokens for {nickname}..."):
        session_token = db[nickname][1]
        bullet_token, g_token = await nso.generate_new_tokens(session_token)
        await db.set(nickname, {'bullet_token': bullet_token, 'g_token': g_token})

async def check_tokens(nickname) -> bool:
    loader = Loader(f"Checking tokens for {nickname}...").start()
    bullet_token, gtoken = db[nickname][2], db[nickname][3]
    response = await graphql(bullet_token, gtoken, 'home')
    loader.stop()
    return response.status == 200

async def check_tokens_and_regenerate(nickname) -> bool:
    if not await check_tokens(nickname): 
        await generate_tokens(nickname)
        return await check_tokens(nickname)
    return True

async def graphql(bullet_token: str, gtoken: str, query: str = None, hash: str = None, return_json=False) -> aiohttp.ClientResponse | dict:
    assert (query or hash) and not (query and hash), "Must provide either a query or a hash, but not both"
    variables = None
    operationName = None
    match query.lower().replace('_', '').replace(' ', ''):
        case 'home':
            hash = '51fc56bbf006caf37728914aa8bc0e2c86a80cf195b4d4027d6822a3623098a8'
            variables = {
                'naCountry': 'US',
            }
        case 'latestbattlehistories' | 'latestbattles' | 'latest':
            hash = '58bf17200ca97b55d37165d44902067b617d635e9c8e08e6721b97e9421a8b67'
        case 'regularbattlehistories' | 'regularbattles' | 'regular' | 'turfwar' | 'turf':
            hash = 'e818519b50e877ac6aeaeaf19e0695356f28002ad4ccf77c1c4867ef0df9a6d7'
        case 'bankarabattlehistories' | 'bankarabattles' | 'bankara' | 'anarchy':
            hash = '7673fe37d5d5d81fa37d0b1cc02cffd7453a809ecc76b000c67d61aa51a39890'
        case 'xbattlehistories' | 'xbattles' | 'xmatch':
            hash = 'a175dc519f551c0bbeed04286194dc12b1a05e3117ab73f6743e5799e91f903a'
        case 'eventbattlehistories' | 'eventbattles' | 'event' | 'challengebattlehistories' | 'challengebattles':
            hash = 'a30281d08421b916902e4972f0d48d4d3346a92a68cbadcdb58b4e1a06273296'
        case 'privatebattlehistories' | 'privatebattles' | 'pbs' | 'private':
            hash = '3dd1b491b2b563e9dfc613e01f0b8e977e122d901bc17466743a82b7c0e6c33a'
        case 'coop' | 'salmon' | 'salmonrun' | 'sr':
            hash = '0f8c33970a425683bb1bdecca50a0ca4fb3c3641c0b2a1237aedfde9c0cb2b8f'
        case 'currentplayer':
            hash = '51fc56bbf006caf37728914aa8bc0e2c86a80cf195b4d4027d6822a3623098a8'
        case 'currentfest':
            hash = '980af9d079ce2a6fa63893d2cd1917b70a229a222b24bbf8201f48d814ff48f0' # old
        case 'playhistory':
            hash = '2a9302bdd09a13f8b344642d4ed483b9464f20889ac17401e993dfa5c2bb3607'
        case 'tournamentnotificationmainquery':
            hash = '93d0a1ccf461da6d23faea6340806f1b6b563f1c375b4a6a0ad35bc5f759f4b4'
            operationName = 'TournamentNotificationMainQuery'
        case 'useshowtournamentsupportnotificationbadgequery':
            hash = '8f40ba6c690211fa2d261a20be7accc063481d377146f7cfb793664ac056df5a'
            operationName = 'UseShowTournamentSupportNotificationBadgeQuery'
        case 'catalog':
            hash = '40b62e4734f22a6009f1951fc1d03366b14a70833cb96a9a46c0e9b7043c67ef'
        case 'gesotown' | 'shop' | 'splatnetshop':
            hash = 'd6f94d4c05a111957bcd65f8649d628b02bf32d81f26f1d5b56eaef438e55bab'
        case 'freshestfits' | 'fits' | 'myoutfits':
            hash = '5b32bb88c47222522d2bc3643b92759644f890a70189a0884ea2d456a8989342'
        case 'playhistory' | 'history':
            hash = '0a62c0152f27c4218cf6c87523377521c2cff76a4ef0373f2da3300079bf0388'
        case 'xranking' | 'xrankings' | 'xrank':
            hash = 'a5331ed228dbf2e904168efe166964e2be2b00460c578eee49fc0bc58b4b899c'
        case 'weaponstats' | 'weapons':
            hash = '974fad8a1275b415c3386aa212b07eddc3f6582686e4fef286ec4043cdf17135'
        case 'stages' | 'stagerecords' | 'stagestats':
            hash = 'c8b31c491355b4d889306a22bd9003ac68f8ce31b2d5345017cdd30a2c8056f3'
        case 'splatfest' | 'splatfests' | 'splatfeststats' | 'festrecords': 
            hash = 'c8660a636e73dcbf55c12932bc301b1c9db2aa9a78939ff61bf77a0ea8ff0a88'
        case 'cooprecord' | 'work':
            hash = '56f989a59643642e0799c90d3f6d0457f5f5f72d4444dfae87043c4a23d13043'
        case 'herorecord' | 'storymode' | 'story':
            hash = '71019ce4389463d9e2a71632e111eb453ca528f4f794aefd861dff23d9c18147'
        case 'highestscoretryresult' | 'sdodrhighscore':
            hash = 'ce1ed302f8cc7c050751fa73ac2a8ae96d4795b1e8a25d27b9cea574983e837b'
        case 'palettes' | 'sdodrpalettes':
            hash = '3464ece725b5f1620721d3a8415a21eeecaef71ed1a9a521199177e8f88b9984'
        case 'chips' | 'sdodrchips':
            hash = '4da51aad1d800c62b3b637b4aee16285734db5a081b0287ee6347bea611697b6'
        case 'defeatenemyrecords' | 'sdodrenemy':
            hash = '1eed33262150a80c5093892eec1ec098d41b9c67894a865da0fadaef6a2181f0'
        case 'settings': # used to get pfp?
            hash = '8473b5eb2c2048f74eb48b0d3e9779f44febcf3477479625b4dc23449940206b'
        case 'friends':
            hash = 'ea1297e9bb8e52404f52d89ac821e1d73b726ceef2fd9cc8d6b38ab253428fb3'
        case 'schedule' | 'schedules':
            hash = 'd49fb6adffe15e3e43ca1167397debfc580eede3ad2232d7e32062bc5487e7eb'
    body = {
        'extensions': {
            'persistedQuery': {
                'sha256Hash': hash,
                'version': 1
            }
        },
        'variables': variables if variables is not None else {}
    }
    if operationName is not None:
        body['operationName'] = operationName
    cookies = {
        '_gtoken': gtoken
    }
    return await process_request(bullet_token, json=body, cookies=cookies, return_json=return_json)

async def generate_headers(bullet_token: str, user_data: dict | None = None) -> dict:
    language = user_data['language'] if user_data is not None and user_data.get('language') else 'en-US'
    country = user_data['country'] if user_data is not None and user_data.get('country') else 'US'
    return {
		'Authorization':    f'Bearer {bullet_token}',
		'Accept-Language':  language,
		'User-Agent':       nso.USER_AGENT,
		'X-Web-View-Ver':   await nso.get_webview_version(),
		'Content-Type':     'application/json',
		'Accept':           '*/*',
		'Origin':           nso.SPLATNET_URL,
		'X-Requested-With': 'com.nintendo.znca',
		'Referer':          f'{nso.SPLATNET_URL}?lang={language}&na_country={country}&na_lang={language}',
		'Accept-Encoding':  'gzip, deflate'
	}

async def view_battle(vsResultId, bullet_token: str, gtoken: str):
    body = {
        'extensions': {
            'persistedQuery': {
                'sha256Hash': 'f893e1ddcfb8a4fd645fd75ced173f18b2750e5cfba41d2669b9814f6ceaec46',
                'version': 1
            }
        },
        'variables': {
            'vsResultId': vsResultId
        }
    }
    cookies = {
        '_gtoken': gtoken
    }
    return await process_request(bullet_token, json=body, cookies=cookies, return_json=True)

async def view_coop(coopHistoryDetailId: str, gtoken: str) -> dict:
    # unfinished
    body = {
        'extensions': {
            'persistedQuery': {
                'sha256Hash': '824a1e22c4ad4eece7ad94a9a0343ecd76784be4f77d8f6f563c165afc8cf602',
                'version': 1
            }
        },
        'variables': {
            'coopHistoryDetailId': coopHistoryDetailId
        }
    }
    cookies = {
        '_gtoken': gtoken
    }
    return await process_request(json=body, cookies=cookies)

async def process_request(bullet_token, **kwargs) -> aiohttp.ClientResponse:
    async with aiohttp.ClientSession() as session:
        async with session.post(f'https://api.lp1.av5ja.srv.nintendo.net/api/graphql', headers=kwargs['headers'] if 'headers' in kwargs else await generate_headers(bullet_token), json=kwargs['json'], cookies=kwargs['cookies']) as r:
            if kwargs.get('return_json') is not None and kwargs['return_json']:
                return await r.json()
            return r

async def fetch_battle_ids(bullet_token: str, g_token: str, modes: str | list) -> dict:
    loader = Loader("Fetching battle IDs...", detailed=True).start()
    if isinstance(modes, list) and any([i not in ['regular', 'bankara', 'x', 'event', 'private', 'latest'] for i in modes]):
        raise ValueError('Invalid mode(s) provided')
    elif isinstance(modes, str) and modes not in ['regular', 'bankara', 'x', 'event', 'private', 'all', 'latest']:
        raise ValueError('Invalid mode provided')
    if modes == 'all':
        modes = ['regular', 'bankara', 'x', 'event', 'private']
    elif isinstance(modes, str):
        modes = [modes]
    battle_ids = {}
    battle_histories = []
    battle_nodes = []
    for mode in modes:
        response = await graphql(bullet_token, g_token, f'{mode}BattleHistories', return_json=True)
        battle_nodes.extend(response['data'][f'{mode}BattleHistories']['historyGroups']['nodes'])
    for node in battle_nodes:
        battle_histories.extend(node['historyDetails']['nodes'])
    for battle in battle_histories:
        battle_id = await utils.decode_battle_id(battle['id'])
        battle_ids[battle_id] = battle['id'] # such good code i know!
    loader.stop()
    return battle_ids