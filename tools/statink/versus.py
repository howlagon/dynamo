import re

from database import UserDatabase, Cache
from splatnet import graphql
from tools.statink import common

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
    bullet_token, g_token = db[username][2], db[username][3]
    matches = await Cache.graphql(bullet_token, g_token, 'latest', return_json=True)
    # wacky list comprehension
    battles = [node['historyDetails']['nodes'] for node in matches['data']['latestBattleHistories']['historyGroups']['nodes']][0]
    try:
        battle = [battle for battle in battles if battle['id'] == previous_history_detail][0]
    except IndexError:
        return None
    rank = await split_rank(battle['udemae'])
    return rank

async def find_rank_after(username: str, history_detail: str) -> str:
    db = UserDatabase()
    bullet_token, g_token = db[username][2], db[username][3]
    matches = await Cache.graphql(bullet_token, g_token, 'latest', return_json=True)
    # wacky list comprehension
    battles = [node['historyDetails']['nodes'] for node in matches['data']['latestBattleHistories']['historyGroups']['nodes']][0]
    battle = [battle for battle in battles if battle['id'] == history_detail][0]
    rank = await split_rank(battle['udemae'])
    return rank

async def split_rank(rank):
    regex = r"([CBAS][-+]?)(\d\d?)?"
    match = re.match(regex, rank)
    return match.groups()

async def get_challenge_win_loss(username, history_detail: str, mode: str):
    assert mode in ['xmatch', 'bankara_challenge']
    if mode == 'bankara_challenge':
        mode = 'bankara'
    
    db = UserDatabase()
    bullet_token, g_token = db[username][2], db[username][3]
    matches = await graphql(bullet_token, g_token, f'{mode}', return_json=True)
    nodes = matches['data'][[key for key in matches['data'].keys() if 'Histories' in key][0]]['nodes']
    for node in nodes:
        for battle in node['historyDetails']['nodes']:
            if history_detail == battle['id']:
                break
    measurement = node['bankaraMatchChallenge' if mode == 'bankara' else 'xMatchMeasurement']
    return measurement['winCount'], measurement['loseCount']

async def get_x_power_after(username, history_detail: str):
    db = UserDatabase()
    bullet_token, g_token = db[username][2], db[username][3]
    matches = await graphql(bullet_token, g_token, 'xmatch', return_json=True)
    nodes = matches['data'][[key for key in matches['data'].keys() if 'Histories' in key][0]]['nodes']
    for node in nodes:
        for battle in node['historyDetails']['nodes']:
            if history_detail == battle['id']:
                break
    return node['xMatchMeasurement']['xPowerAfter']

async def get_anarchy_power_before(username, previous_history_detail: str | None):
    if previous_history_detail is None: return None
    db = UserDatabase()
    bullet_token, g_token = db[username][2], db[username][3]
    previous_battle = await Cache.view_battle(previous_history_detail, bullet_token, g_token)
    return previous_battle['data']['vsHistoryDetail']['bankaraMatch']['bankaraPower']['power']

async def format_player(player_dict: dict, rank_in_team: int) -> dict:
    new_dict = {
        'me': player_dict['isMyself'],
        'rank_in_team': rank_in_team,
        'name': player_dict['name'],
        'number': player_dict['nameId'],
        'splashtag_title': player_dict['byname'],
        'weapon': await common.find_statink_weapon(player_dict['weapon']['name']),
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
        'primary_ability': await common.find_statink_weapon(gear_dict['primaryGearPower']['name']),
        'secondary_abilities': [await common.find_statink_weapon(ability['name']) for ability in gear_dict['additionalGearPowers'] if ability['name'].lower() != 'unknown']
    }
    return new_dict

async def format_tricolor_role(role: str) -> str:
    match role:
        case 'DEFENSE': return 'defender'
        case _: return 'attacker'