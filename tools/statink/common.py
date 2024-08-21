import tools.utils as utils

async def find_statink_weapon(weapon: str) -> str:
    if weapon.lower() == "random": return None
    return weapon.replace(' ', '_') \
                 .replace('-', '_') \
                 .replace("'", '_') \
                 .replace('.', '') \
                 .replace('+', '_') \
                 .replace('(', '') \
                 .replace(')', '') \
                 .replace('__', '_') \
                 .lower()

async def find_statink_special(special_id: str) -> str:
    match special_id:
        #### vs ####
        case "U3BlY2lhbFdlYXBvbi0x": return "trizooka"
        case "U3BlY2lhbFdlYXBvbi0y": return "big_bubbler"
        case "U3BlY2lhbFdlYXBvbi0z": return "zipcaster"
        case "U3BlY2lhbFdlYXBvbi00": return "tenta_missiles"
        case "U3BlY2lhbFdlYXBvbi01": return "ink_storm"
        case "U3BlY2lhbFdlYXBvbi02": return "booyah_bomb"
        case "U3BlY2lhbFdlYXBvbi03": return "wave_breaker"
        case "U3BlY2lhbFdlYXBvbi04": return "ink_vac"
        case "U3BlY2lhbFdlYXBvbi05": return "killer_wail_5_1"
        case "U3BlY2lhbFdlYXBvbi0xMA==": return "inkjet"
        case "U3BlY2lhbFdlYXBvbi0xMQ==": return "ultra_stamp"
        case "U3BlY2lhbFdlYXBvbi0xMg==": return "crab_tank"
        case "U3BlY2lhbFdlYXBvbi0xMw==" : return "reefslider"
        case "U3BlY2lhbFdlYXBvbi0xNA==": return "triple_inkstrike"
        case "U3BlY2lhbFdlYXBvbi0xNQ==": return "tacticooler"
        case "U3BlY2lhbFdlYXBvbi0xNg==": return "super_chump"
        case "U3BlY2lhbFdlYXBvbi0xNw==": return "kraken_royale"
        case "U3BlY2lhbFdlYXBvbi0xOA==": return "triple_splashdown"
        case "U3BlY2lhbFdlYXBvbi0xOQ==": return "splattercolor_screen"
        #### salmon ####
        case "U3BlY2lhbFdlYXBvbi0yMDAwNg==": return "booyah_bomb"
        case "U3BlY2lhbFdlYXBvbi0yMDAwNw==": return "wave_breaker"
        case "U3BlY2lhbFdlYXBvbi0yMDAwOQ==": return "killer_wail_5_1"
        case "U3BlY2lhbFdlYXBvbi0yMDAxMA==": return "inkjet"
        case "U3BlY2lhbFdlYXBvbi0yMDAxMg==": return "crab_tank"
        case "U3BlY2lhbFdlYXBvbi0yMDAxMw==": return "reefslider"
        case "U3BlY2lhbFdlYXBvbi0yMDAxNA==": return "triple_inkstrike"
        case "U3BlY2lhbFdlYXBvbi0yMDAxNw==": return "kraken_royale"
        case "U3BlY2lhbFdlYXBvbi0yMDAxOA==": return "triple_splashdown"
        
        case _: return None

async def find_statink_stage(stage_id: str) -> str:
    stage = await utils.decode_b64(stage_id)
    return int(stage.replace("CoopStage-", "") \
                      .replace("VsStage_", ""))