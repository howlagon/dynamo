from database import UserDatabase, Cache
from tools.statink import common
import tools.utils as utils

async def convert_job_id_to_name(job_id: str) -> str:
    job = await utils.decode_b64(job_id)
    return int(job.replace("CoopGrade-", ""))

async def find_job_grade_before(username: str, previous_history_detail: str | None) -> tuple[str, int]:
    """Finds the job title and points of the previous Salmon Run battle

    Args:
        username (str)
        previous_history_detail (str | None): Previous Battle ID

    Returns:
        tuple[str, int]: Job title, points (0-999)
    """
    if previous_history_detail is None: return None
    db = UserDatabase()
    bullet_token, g_token = db[username][2], db[username][3]
    coop = await Cache.view_coop(previous_history_detail, bullet_token, g_token)
    data = coop["data"]["coopHistoryDetail"]
    return await convert_job_id_to_name(data["afterGrade"]["id"]), data["afterGradePoint"]

async def find_total_golden_eggs(data: dict) -> int:
    return sum([wave['teamDeliverCount'] if wave['teamDeliverCount'] is not None else 0 for wave in data['waveResults']])

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
    uniform = await utils.decode_b64(uniform_id)
    return int(uniform.replace("CoopUniform-", ""))

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
    data = {
        "tide": water_level,
        "event": await find_known_occurrence(waveResult["eventWave"]),
        # "danger_rate": None, # FIX LATER
        "golden_quota": waveResult["deliverNorm"],
        "golden_delivered": waveResult["teamDeliverCount"],
        "golden_appearances": waveResult["goldenPopCount"],
        "special_uses": special_uses
    }
    if data["event"] is None:
        del data["event"]
    
    return data

async def generate_player(player: dict, me: bool = False) -> dict:
    return {
        "me": "yes" if me else "no",
        "name": player["player"]["name"],
        "number": player["player"]["nameId"],
        "splashtag_title": player["player"]["byname"],
        "uniform": await statink_get_uniform_color(player["player"]["uniform"]["id"]),
        "special": await common.find_statink_special(await utils.encode_b64(f"SpecialWeapon-{player['specialWeapon']['weaponId']}")),
        "weapons": await generate_weapons(player["weapons"]),
        "golden_eggs": player["goldenDeliverCount"],
        "golden_assist": player["goldenAssistCount"],
        "power_eggs": player["deliverCount"],
        "rescue": player["rescueCount"],
        "rescued": player["rescuedCount"],
        "defeat_boss": player["defeatEnemyCount"],
        "disconnected": "yes" if await determine_disconnect(player) else "no",
        "species": player["player"]["species"].lower()
    }

async def statink_find_boss(boss_id: str) -> str:
    boss = await utils.decode_b64(boss_id)
    return int(boss.replace("CoopEnemy-", ""))

async def generate_weapons(weapons: list) -> list:
    return [await common.find_statink_weapon(weapon["name"]) for weapon in weapons]

async def generate_boss_kills(bosses: dict) -> dict:
    kills = {}
    for boss in bosses:
        boss_id = await statink_find_boss(boss["enemy"]["id"])
        if boss.get("popCount") is None or boss.get("popCount") == 0:
            kills[boss_id] = None
            continue
        kills[boss_id] = {
            "appearances": boss.get("popCount"),
            "defeated": boss.get("teamDefeatCount"),
            "defeated_by_me": boss.get("defeatCount")
        }
    return kills

async def determine_disconnect(data: dict) -> bool:
    for weapon in data["weapons"]:
        if weapon.get("name") == "Random":
            return True
    
    checks = [
        "defeatEnemyCount",
        "deliverCount",
        "goldenAssistCount",
        "goldenDeliverCount",
        "rescueCount",
        "rescuedCount"
    ]

    if all([data.get(check) == 0 for check in checks]):
        return True