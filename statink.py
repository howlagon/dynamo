import aiohttp
import json
from time import time
from datetime import datetime
from typing import Literal

from database import UserDatabase, Cache
from data import APP_VERSION
from config import params, testrun
import tools.utils as utils
import tools.statink.versus as vs
import tools.statink.salmon as salmon
import tools.statink.common as common

async def format_request(payload: dict) -> dict:
    payload['agent'] = 'Dynamo'
    payload['agent_version'] = APP_VERSION
    payload['automated'] = 'yes'
    payload['test'] = "yes" if testrun else "no"

    return payload

async def format_battle(username: str, battle_data: dict) -> dict:
    # skips level_before/after, cash_before/after
    data = battle_data['data']['vsHistoryDetail']
    if data["judgement"] == "DEEMED_LOSE":
        return None
    previous_history_detail = data['previousHistoryDetail'].get('id') if data['previousHistoryDetail'] is not None else None
    lobby_mode = await vs.find_statink_lobby_mode(battle_data)
    players: list = data['myTeam']['players']
    me = await vs.find_me_from_players(players)
    #### general data ####
    payload = {
        # 'test': 'yes',
        'uuid': await utils.decode_battle_id(data['id']),
        'lobby': lobby_mode,
        'rule': await vs.find_statink_mode_rule(data['vsRule']['rule']),
        'stage': await common.find_statink_stage(data['vsStage']['id']),
        'weapon': await common.find_statink_weapon(me['weapon']['name']),
        'result': data['judgement'].lower(),
        'knockout': None,
        'rank_in_team': players.index(next(filter(lambda n: n.get('isMyself') == True, players))) + 1,
        'medals': [award['name'] for award in data['awards']],
        'kill': me['result']['kill'],
        'assist': me['result']['assist'],
        'kill_or_assist': me['result']['kill'] + me['result']['assist'],
        'death': me['result']['death'],
        'special': me['result']['special'],
        'inked': me['paint']
        }

    #### turf, splatfest ####
    if lobby_mode in ['regular', 'splatfest_open', 'splatfest_challenge']:
        payload['our_team_inked'] = sum([player['paint'] for player in players])
        payload['their_team_inked'] = sum([player['paint'] for player in data['otherTeams'][0]['players']])
        if len(data['otherTeams']) > 1:
            payload['third_team_inked'] = sum([player['paint'] for player in data['otherTeams'][1]['players']])
        if data["judgement"] != "DRAW":
            payload['our_team_percent'] = data['myTeam']['result']['paintRatio'] * 100
            payload['their_team_percent'] = data['otherTeams'][0]['result']['paintRatio'] * 100
            if len(data['otherTeams']) > 1:
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
        if data["judgement"] != "DRAW":
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

    #### x (for x power) ####
    if lobby_mode in ['xmatch']:
        payload['x_power_before'] = data['xMatch']['lastXPower']
        x_power_after = await vs.get_x_power_after(username, data['id'])
        if x_power_after is not None: payload['x_power_after'] = x_power_after
    
    #### battle data ####
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
    
    return payload

async def format_job(username: str, battle_data: dict) -> dict:
    data = battle_data['data']['coopHistoryDetail']
    data['previousHistoryDetail'].get('id') if data['previousHistoryDetail'] is not None else None
    payload = {
        "uuid": await utils.decode_job_id(data['id']),
        "private": "no", # FIX LATER
        "big_run": "yes" if data["rule"] == "BIG_RUN" else "no",
        "eggstra_work": "no", # FIX LATER
        "stage": await common.find_statink_stage(data['coopStage']['id'])
    }

    payload["danger_rate"] = data['dangerRate'] * 100 if payload["eggstra_work"] == "no" else None
    clear_waves = data['resultWave'] - 1
    payload["clear_waves"] = 3 if clear_waves == -1 else clear_waves
    
    #### player data ####
    payload["title_after"] = await salmon.convert_job_id_to_name(data["afterGrade"]['id'])
    payload["title_exp_after"] = data["afterGradePoint"]
    grade_before = await salmon.find_job_grade_before(username, data['previousHistoryDetail'].get('id') if data['previousHistoryDetail'] is not None else None)
    if grade_before is not None:
        payload["title_before"], payload["title_exp_before"] = grade_before
    
    #### team data ####
    payload["golden_eggs"] = await salmon.find_total_golden_eggs(data)
    payload["power_eggs"] = await salmon.find_total_power_eggs(data)

    #### king ####
    payload["king_smell"] = data["smellMeter"]
    if data["bossResult"] is not None:
        payload["king_salmonid"] = await salmon.statink_find_boss(data["bossResult"]["boss"]["id"])
        payload["clear_extra"] = data["bossResult"].get("hasDefeatBoss") if data["bossResult"] is not None else None

        payload["gold_scale"] = data["scale"]["gold"]
        payload["silver_scale"] = data["scale"]["silver"]
        payload["bronze_scale"] = data["scale"]["bronze"]

    #### job score ####
    payload["job_point"] = data["jobPoint"]
    payload["job_score"] = data["jobScore"]
    payload["job_rate"] = data["jobRate"]
    payload["job_bonus"] = data["jobBonus"]

    #### players ####
    payload["players"] = [await salmon.generate_player(player) for player in data['memberResults']] + [await salmon.generate_player(data['myResult'], me=True)]

    #### waves ####
    payload["waves"] = [await salmon.generate_wave(wave) for wave in data['waveResults']]

    #### bosses ####
    payload["bosses"] = await salmon.generate_boss_kills(data['enemyResults'])

    date = datetime.strptime(data['playedTime'], "%Y-%m-%dT%H:%M:%SZ")
    proper_datetime = int((date - datetime(1970, 1, 1)).total_seconds())
    payload['start_at'] = int(proper_datetime)
    # no end_at, maybe its hidden somewhere in the response?

    return payload

async def upload(statink_key: str, battle_id: str, payload: dict, type: Literal["battle", "job"]):
    match type:
        case "job":
            url = 'https://stat.ink/api/v3/salmon'
        case "battle" | _: 
            url = 'https://stat.ink/api/v3/battle'
    headers = {
        'Authorization': f'Bearer {statink_key}',
        'Content-Type': 'application/json'
    }
    type = type.title()
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as r:
            data = await r.json()
            if testrun and r.status == 200:
                print(f"{type} validated succsesfully! ID: {battle_id}")
            elif r.status not in [200, 201]:
                print(f"Error uploading {type.lower()}. ID: {battle_id}\nMessage: {await r.text()}")
                print(json.dumps(payload, indent=4))
            elif data["created_at"]["time"] < time() - 30:
                print(f"{type} already uploaded: {data['url']}")
            else:
                print(f"{type} uploaded to {data['url']}")
    return

async def upload_battle(username: str, battle_id: str):
    db = UserDatabase()
    bullet_token, g_token = db[username][2], db[username][3]
    # get battle data
    battle_data = await Cache.view_battle(battle_id, bullet_token, g_token)
    battle = await format_battle(username, battle_data)
    if battle is None: return False
    request = await format_request(battle)
    
    await upload(db[username][5], battle_id, request, "battle")

async def upload_job(username: str, job_id: str):
    db = UserDatabase()
    bullet_token, g_token = db[username][2], db[username][3]

    job_data = await Cache.view_coop(job_id, bullet_token, g_token)
    job = await format_job(username, job_data)
    request = await format_request(job)

    await upload(db[username][5], job_id, request, "job")

async def fetch_uploaded_battles(stat_ink_api_key: str, mode: str = 'adaptive'):
    headers = {
        'Authorization': f'Bearer {stat_ink_api_key}'
    }
    if mode not in ["bankara", "bankara_challenge", "bankara_open", "private"]:
        mode = "adaptive"
    params = {
        'lobby': mode
    }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://stat.ink/api/v3/s3s/uuid-list' , headers=headers, params=params) as r:
            data = await r.json()
    return data

async def fetch_uploaded_jobs(stat_ink_api_key: str):
    headers = {
        'Authorization': f'Bearer {stat_ink_api_key}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://stat.ink/api/v3/salmon/uuid-list', headers=headers) as r:
            data = await r.json()
    return data
