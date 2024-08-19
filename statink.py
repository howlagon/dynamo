import aiohttp
import json
import msgpack
import re
from datetime import datetime

from database import UserDatabase, Cache
from loader import Loader
from data import APP_VERSION
import tools.utils as utils
import tools.statink.versus as vs
import tools.statink.common as common

async def format_request(payload: dict) -> dict:
    payload['agent'] = 'Dynamo'
    payload['agent_version'] = APP_VERSION
    payload['automated'] = 'yes'
    payload['test'] = "yes"

    return payload

async def format_battle(username: str, battle_data: dict) -> dict:
    # skips level_before/after, cash_before/after
    loader = Loader('Formatting battle data...', detailed=True).start()
    data = battle_data['data']['vsHistoryDetail']
    previous_history_detail = data['previousHistoryDetail'].get('id')
    lobby_mode = await vs.find_statink_lobby_mode(battle_data)
    players: list = data['myTeam']['players']
    me = await vs.find_me_from_players(players)
    #### general data ####
    payload = {
        # 'test': 'yes',
        'uuid': await utils.decode_battle_id(data['id']),
        'lobby': lobby_mode,
        'rule': await vs.find_statink_mode_rule(data['vsRule']['rule']),
        'stage': await vs.find_statink_stage(data['vsStage']['name']),
        'weapon': await common.find_statink_weapon(me['weapon']['name']),
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
        payload['our_team_role'] = await vs.format_tricolor_role(data['myTeam']['tricolorRole'])
        payload['their_team_role'] = await vs.format_tricolor_role(data['otherTeams'][0]['tricolorRole'])
        if len(data['otherTeams']) > 1:
            payload['third_team_role'] = await vs.format_tricolor_role(data['otherTeams'][1]['tricolorRole'])
    #### series, open, x ####
    elif lobby_mode in ['xmatch', 'bankara_open', 'bankara_challenge']:
        payload['knockout'] = 'yes' if data['knockout'] in ['WIN', 'LOSE'] else 'no'
        payload['our_team_count'] = data['myTeam']['result']['score']
        payload['their_team_count'] = data['otherTeams'][0]['result']['score']
    #### series, open ####
    if lobby_mode in ['bankara_open', 'bankara_challenge']:
        rank_before = await vs.find_rank_before(username, previous_history_detail)
        payload['rank_before'] = rank_before[0].lower()
        if len(rank_before) > 1:
            payload['rank_before_s_plus'] = rank_before[1]
        rank_after = await vs.find_rank_after(username, data['id'])
        payload['rank_after'] = rank_after[0].lower()
        if len(rank_after) > 1:
            payload['rank_after_s_plus'] = rank_after[1]
    #### open ####
    if lobby_mode in ['bankara_open']:
        bankara_power = await vs.find_bankara_power(data['bankaraMatch'])
        if bankara_power is not None: payload['bankara_power_after'] = bankara_power
        bankara_power_before = await vs.get_anarchy_power_before(username, previous_history_detail)
        if bankara_power_before is not None: payload['bankara_power_before'] = bankara_power_before
    #### x, series (for win/loss) ####
    if lobby_mode in ['xmatch', 'bankara_challenge']:
        payload['challenge_win'], payload['challenge_lose'] = await vs.get_challenge_win_loss(username, data['id'], lobby_mode)
    #### x (for x poewr) ####
    if lobby_mode in ['xmatch']:
        payload['x_power_before'] = data['xMatch']['lastXPower']
        x_power_after = await vs.get_x_power_after(username, data['id'])
        if x_power_after is not None: payload['x_power_after'] = x_power_after
    
    payload['our_team_color'] = await utils.rgba_to_hex(data['myTeam']['color'])
    payload['their_team_color'] = await utils.rgba_to_hex(data['otherTeams'][0]['color'])

    payload['our_team_players'] = [await vs.format_player(player, i + 1) for i, player in enumerate(players)]
    payload['their_team_players'] = [await vs.format_player(player, i + 1) for i, player in enumerate(data['otherTeams'][0]['players'])]
    
    if len(data['otherTeams']) > 1:
        payload['third_team_color'] = await utils.rgba_to_hex(data['otherTeams'][1]['color'])
        payload['third_team_players'] = [await vs.format_player(player, i + 1) for i, player in enumerate(data['otherTeams'][1]['players'])]

    date = datetime.strptime(data['playedTime'], "%Y-%m-%dT%H:%M:%SZ")
    proper_datetime = int((date - datetime(1970, 1, 1)).total_seconds())
    payload['start_at'] = int(proper_datetime)
    payload['end_at'] = proper_datetime + data['duration']
    # print('\n', payload, '\n')
    
    loader.stop()
    return payload

async def format_job(username: str, battle_data: dict) -> dict:
    loader = Loader('Formatting job data...', detailed=True).start()
    data = battle_data['data']['coopHistoryDetail']
    payload = {
        "uuid": await utils.decode_battle_id(data['id']),
        "private": "no", # FIX LATER
        "big_run": "yes" if data["rule"] == "BIG_RUN" else "no",
        "eggstra_work": "no", # FIX LATER
        "stage": vs.find_statink_stage(data['coopStage']['name'])
    }

    payload["danger_rate"] = data['dangerRate'] * 100 if payload["eggstra_work"] == "no" else None
    payload["fail_reason"] = None
    
    #### player data ####
    payload["title_after"] = data["afterGrade"]['name']
    payload["title_exp_after"] = data["afterGradePoint"]
    payload["title_before"], payload["title_exp_before"] = await find_job_grade_before(username, data['previousHistoryDetail']['id'])
    
    #### team data ####
    payload["golden_eggs"] = await find_total_golden_eggs(data)
    payload["power_eggs"] = await find_total_power_eggs(data)

    #### king ####
    payload["king_smell"] = data["smellMeter"]
    payload["king_salmonid"] = await statink_find_king(data["boss"]["id"])
    payload["clear_extra"] = data["bossResult"].get("hasDefeatBoss") if data["bossResult"] is not None else None

    #### scales ####
    payload["gold_scale"] = data["scale"]["gold"] if data["scale"] is not None else 0
    payload["silver_scale"] = data["scale"]["silver"] if data["scale"] is not None else 0
    payload["bronze_scale"] = data["scale"]["bronze"] if data["scale"] is not None else 0

    #### job score ####
    payload["job_point"] = data["jobPoint"]
    payload["job_score"] = data["jobScore"]
    payload["job_rate"] = data["jobRate"]
    payload["job_bonus"] = data["jobBonus"]

    #### waves ####
    payload["clear_waves"] = 3 if len(data['waveResults']) >= 3 else len(data['waveResults']) - 1
    payload["waves"] = [await generate_wave(wave) for wave in data['waveResults']]

    #### ####
    payload["players"]

async def upload_battle(username: str, battle_id: str):
    db = UserDatabase()
    bullet_token, g_token = db[username][2], db[username][3]
    # get battle data
    battle_data = await Cache.view_battle(battle_id, bullet_token, g_token)
    print(f"\n{battle_id} {battle_data}")
    request = await format_request(await format_battle(username, battle_data))
    loader = Loader('Uploading battle...', detailed=True).start()
    headers = {
        'Authorization': f'Bearer {db[username][5]}',
        'Content-Type': 'application/json'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://stat.ink/api/v3/battle', headers=headers, json=request) as r:
            data = await r.json()
    loader.stop()

async def upload_job(username: str, job_id: str):
    db = UserDatabase()

async def fetch_uploaded_battles(stat_ink_api_key: str):
    headers = {
        'Authorization': f'Bearer {stat_ink_api_key}'
    }
    with Loader('Fetching uploaded battles...', detailed=True):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://stat.ink/api/v3/s3s/uuid-list', headers=headers) as r:
                data = await r.json()
    return data

async def fetch_uploaded_jobs(stat_ink_api_key: str):
    headers = {
        'Authorization': f'Bearer {stat_ink_api_key}'
    }
    with Loader('Fetching uploaded jobs...', detailed=True):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://stat.ink/api/v3/salmon/uuid-list', headers=headers) as r:
                data = await r.json()
    return data


async def find_job_grade_before(username: str, previous_history_detail: str | None) -> dict:
    """Takes a mode and battle id and returns the rank of the previous battle"""
    if previous_history_detail is None: return None
    db = UserDatabase()
    bullet_token, g_token = db[username][2], db[username][3]
    coop = await Cache.view_coop(previous_history_detail, bullet_token, g_token)
    return coop["afterGrade"], coop["afterGradePoint"]

async def find_total_golden_eggs(data: dict) -> int:
    return sum([wave['teamDeliverCount'] for wave in data['waveResults']])

async def find_total_power_eggs(data: dict) -> int:
    return sum([member["deliverCount"] for member in data['memberResults']]) + data["myResult"]["deliverCount"]

async def find_known_occurrence(event_wave: dict | None) -> str:
    if event_wave is None: return None
    event_id = event_wave["id"]
    match event_id:
        case "Q29vcEV2ZW50V2F2ZS0x": return "rush"
        case "Q29vcEV2ZW50V2F2ZS0y": return "goldie_seeking"
        case "Q29vcEV2ZW50V2F2ZS0z": return "griller"
        case "Q29vcEV2ZW50V2F2ZS00": return "mothership"
        case "Q29vcEV2ZW50V2F2ZS01": return "fog"
        case "Q29vcEV2ZW50V2F2ZS02": return "cohock_charge"
        case "Q29vcEV2ZW50V2F2ZS03": return "giant_tornado"
        case "Q29vcEV2ZW50V2F2ZS04": return "mudmouth_eruption"

async def statink_get_uniform_color(uniform_id: str) -> str:
    match uniform_id:
        case "Q29vcFVuaWZvcm0tNw==": return "white" # 7

async def generate_wave(waveResult: dict) -> dict:
    match waveResult["waterLevel"]:
        case 0: water_level = "low"
        case 1: water_level = "normal"
        case 2: water_level = "high"

    specials = [await common.find_statink_special(special["id"]) for special in waveResult["specialWeapons"]]
    special_uses = {}
    for special in specials:
        if special in special_uses:
            special_uses[special] += 1
        else:
            special_uses[special] = 1
    return {
        "tide": water_level,
        "event": await find_known_occurrence(waveResult["eventWave"]),
        "danger_rate": None, # FIX LATER
        "golden_quota": waveResult["deliverNorm"],
        "golden_delivered": waveResult["teamDeliverCount"],
        "golden_appearances": waveResult["goldenPopCount"],
        "special_uses": special_uses
    }

async def generate_player(player: dict, me: bool = False) -> dict:
    return {
        "me": me,
        "name": player["player"]["name"],
        "number": player["player"]["nameId"],
        "splashtag_title": player["player"]["byname"],
        "uniform": await statink_get_uniform_color(player["player"]["uniform"]["id"]),
        "special": await common.find_statink_special(utils.encode_b64(f"SpecialWeapon-{player['player']['specialWeapon']['weaponId']}")),
    }

async def statink_find_king(king_id: str) -> str:
    match king_id:
        case "Q29vcEVuZW15LTIz": return "cohozuna"
        case "Q29vcEVuZW15LTI0": return "horrorboros"
        case "Q29vcEVuZW15LTI1": return "megalodontia"
        case "Q29vcEVuZW15LTMw": return "triumvirate"