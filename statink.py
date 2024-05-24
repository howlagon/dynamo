import aiohttp
import utils
import json
import msgpack
import re
from datetime import datetime
from splatnet import graphql
from database import UserDatabase, Cache
from loader import Loader
from data import APP_VERSION

async def format_request(username: str, battle_data: dict) -> dict:
    # skips level_before/after, cash_before/after
    loader = Loader('Formatting battle data...', detailed=True).start()
    data = battle_data['data']['vsHistoryDetail']
    previous_history_detail = data['previousHistoryDetail'].get('id')
    lobby_mode = await find_statink_lobby_mode(battle_data)
    players: list = data['myTeam']['players']
    me = await find_me_from_players(players)
    #### general data ####
    payload = {
        # 'test': 'yes',
        'uuid': await utils.decode_battle_id(data['id']),
        'lobby': lobby_mode,
        'rule': await find_statink_mode_rule(data['vsRule']['rule']),
        'stage': await find_statink_stage(data['vsStage']['name']),
        'weapon': await find_statink_weapon(me['weapon']['name']),
        'result': data['judgement'].lower(),
        'knockout': None,
        'rank_in_team': players.index(next(filter(lambda n: n.get('isMyself') == True, players))) + 1,
        'kill': me['result']['kill'],
        'assist': me['result']['assist'],
        'kill_or_assist': me['result']['kill'] + me['result']['assist'],
        'death': me['result']['death'],
        'special': me['result']['special'],
        'inked': me['paint'],
        'medals': [award['name'] for award in data['awards']],
    }
    #### turf, splatfest ####
    if lobby_mode in ['regular', 'splatfest_open', 'splatfest_challenge']:
        payload['our_team_inked'] = sum([player['paint'] for player in players])
        payload['our_team_percent'] = data['myTeam']['result']['paintRatio'] * 100
        payload['their_team_inked'] = sum([player['paint'] for player in data['otherTeams'][0]['players']])
        payload['their_team_percent'] = data['otherTeams'][0]['result']['paintRatio'] * 100
        if len(data['otherTeams']) > 1:
            payload['third_team_inked'] = sum([player['paint'] for player in data['otherTeams'][1]['players']])
            payload['third_team_percent'] = data['otherTeams'][1]['result']['paintRatio'] * 100
    #### splatfest ####
    elif lobby_mode in ['splatfest_open', 'splatfest_challenge']:
        payload['our_team_theme'] = data['myTeam']['festTeamName']
        payload['their_team_theme'] = data['otherTeams'][0]['festTeamName']
        if len(data['otherTeams']) > 1:
            payload['third_team_theme'] = data['otherTeams'][1]['festTeamName']
    #### splatfest tricolor ####
    elif lobby_mode in ['tricolor']:
        payload['our_team_role'] = await format_tricolor_role(data['myTeam']['tricolorRole'])
        payload['their_team_role'] = await format_tricolor_role(data['otherTeams'][0]['tricolorRole'])
        if len(data['otherTeams']) > 1:
            payload['third_team_role'] = await format_tricolor_role(data['otherTeams'][1]['tricolorRole'])
    #### series, open, x ####
    elif lobby_mode in ['xmatch', 'bankara_open', 'bankara_challenge']:
        payload['knockout'] = 'yes' if data['knockout'] in ['WIN', 'LOSE'] else 'no'
        payload['our_team_count'] = data['myTeam']['result']['score']
        payload['their_team_count'] = data['otherTeams'][0]['result']['score']
    #### series, open ####
    if lobby_mode in ['bankara_open', 'bankara_challenge']:
        rank_before = await find_rank_before(username, previous_history_detail)
        payload['rank_before'] = rank_before[0].lower()
        if len(rank_before) > 1:
            payload['rank_before_s_plus'] = rank_before[1]
        rank_after = await find_rank_after(username, data['id'])
        payload['rank_after'] = rank_after[0].lower()
        if len(rank_after) > 1:
            payload['rank_after_s_plus'] = rank_after[1]
    #### open ####
    if lobby_mode in ['bankara_open']:
        bankara_power = await find_bankara_power(data['bankaraMatch'])
        if bankara_power is not None: payload['bankara_power_after'] = bankara_power
        bankara_power_before = await get_anarchy_power_before(username, previous_history_detail)
        if bankara_power_before is not None: payload['bankara_power_before'] = bankara_power_before
    #### x, series (for win/loss) ####
    if lobby_mode in ['xmatch', 'bankara_challenge']:
        payload['challenge_win'], payload['challenge_lose'] = await get_challenge_win_loss(username, data['id'], lobby_mode)
    #### x (for x poewr) ####
    if lobby_mode in ['xmatch']:
        payload['x_power_before'] = data['xMatch']['lastXPower']
        x_power_after = await get_x_power_after(username, data['id'])
        if x_power_after is not None: payload['x_power_after'] = x_power_after
    
    payload['our_team_color'] = await utils.rgba_to_hex(data['myTeam']['color'])
    payload['their_team_color'] = await utils.rgba_to_hex(data['otherTeams'][0]['color'])

    payload['our_team_players'] = [await format_player(player, i + 1) for i, player in enumerate(players)]
    payload['their_team_players'] = [await format_player(player, i + 1) for i, player in enumerate(data['otherTeams'][0]['players'])]
    
    if len(data['otherTeams']) > 1:
        payload['third_team_color'] = await utils.rgba_to_hex(data['otherTeams'][1]['color'])
        payload['third_team_players'] = [await format_player(player, i + 1) for i, player in enumerate(data['otherTeams'][1]['players'])]

    payload['agent'] = 'Dynamo'
    payload['agent_version'] = APP_VERSION
    payload['automated'] = 'yes'
    date = datetime.strptime(data['playedTime'], "%Y-%m-%dT%H:%M:%SZ")
    proper_datetime = int((date - datetime(1970, 1, 1)).total_seconds())
    payload['start_at'] = int(proper_datetime)
    payload['end_at'] = proper_datetime + data['duration']
    # print('\n', payload, '\n')
    
    loader.stop()
    return payload

async def upload_battle(username: str, battle_id: str):
    db = UserDatabase()
    bullet_token, gtoken = db[username][2], db[username][3]
    # get battle data
    battle_data = await Cache.view_battle(battle_id, bullet_token, gtoken)
    request = await format_request(username, battle_data)
    loader = Loader('Uploading battle...', detailed=True).start()
    headers = {
        'Authorization': f'Bearer {db[username][5]}',
        'Content-Type': 'application/json'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://stat.ink/api/v3/battle', headers=headers, json=request) as r:
            data = await r.json()
    loader.stop()
    # print('\n', json.dumps(request), '\n')
    print('\n', json.dumps(data), '\n')

async def find_statink_lobby_mode(battle_data: dict) -> str:
    """Takes a battle data dict and returns the lobby mode for stat.ink"""
    # so cool. so cool. so cool. so cool. so cool. so cool. so cool
    mode: str
    data = battle_data['data']['vsHistoryDetail']
    vsMode = battle_data['data']['vsHistoryDetail']['vsMode']['mode']
    match vsMode:
        case 'X_MATCH': mode = 'xmatch'
        case 'LEAGUE': mode = 'event'
        case 'PRIVATE': mode = 'private'
        case 'FEST': 
            match data['festMatch']['myFestPower']:
                case None: mode = 'splatfest_open'
                case _: mode = 'splatfest_challenge'
        case 'BANKARA':
            match data['bankaraMatch']['mode']:
                case 'CHALLENGE': mode = 'bankara_challenge'
                case _: mode = 'bankara_open'
        case 'REGULAR': mode = 'regular'
    return mode

async def find_statink_mode_rule(rule: str) -> str:
    match rule:
        case 'TURF_WAR': return 'nawabari'
        case 'LOFT': return 'yagura'
        case 'AREA': return 'area' # so cool
        case 'GOAL': return 'hoko'
        case 'CLAM': return 'asari' # so cool
        case 'TRI_COLOR': return 'tricolor'

async def find_statink_stage(stage: str) -> str:
    match stage:
        case _: return stage.lower() \
                             .replace(' ', '_') \
                             .replace('.', '') \
                             .replace("'", '') \
                             .replace('&', 'and')

async def find_statink_weapon(weapon: str) -> str:
    return weapon.replace(' ', '_') \
                 .replace('-', '_') \
                 .replace("'", '_') \
                 .replace('.', '') \
                 .replace('(', '') \
                 .replace(')', '') \
                 .lower()

async def find_me_from_players(players: list) -> dict | None:
    for player in players:
        if player['isMyself']: return player
    return None

async def find_bankara_power(bankara_match: dict) -> int | None:
    if bankara_match.get("bankaraPower") is not None and bankara_match['bankaraPower'].get('power') is not None:
        return bankara_match['bankaraPower']['power']
    return None

async def find_rank_before(username: str, previous_history_detail: str | None) -> str | None:
    """Takes a mode and battle id and returns the rank of the previous battle"""
    if previous_history_detail is None: return None
    db = UserDatabase()
    bullet_token, gtoken = db[username][2], db[username][3]
    matches = await Cache.graphql(bullet_token, gtoken, 'latest', return_json=True)
    # wacky list comprehension
    battles = [node['historyDetails']['nodes'] for node in matches['data']['latestBattleHistories']['historyGroups']['nodes']][0]
    battle = [battle for battle in battles if battle['id'] == previous_history_detail][0]
    rank = await split_rank(battle['udemae'])
    return rank

async def find_rank_after(username: str, history_detail: str) -> str:
    db = UserDatabase()
    bullet_token, gtoken = db[username][2], db[username][3]
    matches = await Cache.graphql(bullet_token, gtoken, 'latest', return_json=True)
    # wacky list comprehension
    battles = [node['historyDetails']['nodes'] for node in matches['data']['latestBattleHistories']['historyGroups']['nodes']][0]
    battle = [battle for battle in battles if battle['id'] == history_detail][0]
    rank = await split_rank(battle['udemae'])
    return rank

async def split_rank(rank):
    regex = r"([CBAS][-+]?)(\d\d?)?"
    match = re.match(regex, rank)
    return match.groups()

async def fetch_uploaded_battles(stat_ink_api_key: str):
    headers = {
        'Authorization': f'Bearer {stat_ink_api_key}'
    }
    with Loader('Fetching uploaded battles...', detailed=True):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://stat.ink/api/v3/s3s/uuid-list', headers=headers) as r:
                data = await r.json()
    return data

async def get_challenge_win_loss(username, history_detail: str, mode: str):
    assert mode in ['xmatch', 'bankara_challenge']
    if mode == 'bankara_challenge':
        mode = 'bankara'
    
    db = UserDatabase()
    bullet_token, gtoken = db[username][2], db[username][3]
    matches = await graphql(bullet_token, gtoken, f'{mode}', return_json=True)
    nodes = matches['data'][[key for key in matches['data'].keys() if 'Histories' in key][0]]['nodes']
    for node in nodes:
        for battle in node['historyDetails']['nodes']:
            if history_detail == battle['id']:
                break
    measurement = node['bankaraMatchChallenge' if mode == 'bankara' else 'xMatchMeasurement']
    return measurement['winCount'], measurement['loseCount']

async def get_x_power_after(username, history_detail: str):
    db = UserDatabase()
    bullet_token, gtoken = db[username][2], db[username][3]
    matches = await graphql(bullet_token, gtoken, 'xmatch', return_json=True)
    nodes = matches['data'][[key for key in matches['data'].keys() if 'Histories' in key][0]]['nodes']
    for node in nodes:
        for battle in node['historyDetails']['nodes']:
            if history_detail == battle['id']:
                break
    return node['xMatchMeasurement']['xPowerAfter']

async def get_anarchy_power_before(username, previous_history_detail: str | None):
    if previous_history_detail is None: return None
    db = UserDatabase()
    bullet_token, gtoken = db[username][2], db[username][3]
    previous_battle = await Cache.view_battle(previous_history_detail, bullet_token, gtoken)
    return previous_battle['data']['vsHistoryDetail']['bankaraMatch']['bankaraPower']['power']

async def format_player(player_dict: dict, rank_in_team: int) -> dict:
    new_dict = {
        'me': player_dict['isMyself'],
        'rank_in_team': rank_in_team,
        'name': player_dict['name'],
        'number': player_dict['nameId'],
        'splashtag_title': player_dict['byname'],
        'weapon': await find_statink_weapon(player_dict['weapon']['name']),
        'inked': player_dict['paint'],
        'gears': {
            'headgear': await format_gear_structure(player_dict['headGear']),
            'clothing': await format_gear_structure(player_dict['clothingGear']),
            'shoes': await format_gear_structure(player_dict['shoesGear'])
        },
        'disconnected': 'yes' if player_dict['result'] is None else 'no',
        'crown': 'yes' if player_dict['crown'] or player_dict.get('festDragonCert') != 'NONE' else 'no',
        'species': player_dict['species'].lower()
    }
    if new_dict['crown'] == 'yes':
        new_dict['crown_type'] = 'x' if player_dict['crown'] else '333x' if player_dict.get('festDragonCert') == 'DOUBLE_DRAGON' else '100x'

    if player_dict['result'] is not None:
        new_dict.update({
            'kill': player_dict['result']['kill'],
            'assist': player_dict['result']['assist'],
            'kill_or_assist': player_dict['result']['kill'] + player_dict['result']['assist'],
            'death': player_dict['result']['death'],
            'special': player_dict['result']['special'],
        })
    if player_dict['result']['noroshiTry'] is not None:
        new_dict['signal'] = player_dict['result']['noroshiTry']
    return new_dict

async def format_gear_structure(gear_dict: dict) -> dict:
    new_dict = {
        'primary_ability': await find_statink_weapon(gear_dict['primaryGearPower']['name']),
        'secondary_abilities': [await find_statink_weapon(ability['name']) for ability in gear_dict['additionalGearPowers'] if ability['name'].lower() != 'unknown']
    }
    return new_dict

async def format_tricolor_role(role: str) -> str:
    match role:
        case 'DEFENSE': return 'defender'
        case _: return 'attacker'