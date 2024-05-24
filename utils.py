import base64
import builtins
import threading
import uuid
from time import sleep
from sys import stdout

from config import params

NAMESPACE = uuid.UUID('b3a2dbf5-2c09-4792-b78c-00b548b70aeb')

async def decode_b64(b64: str) -> str:
    return base64.b64decode(b64).decode('utf-8')

async def decode_battle_id(b64: str) -> str:
    decoded = await decode_b64(b64)
    return str(uuid.uuid5(NAMESPACE, decoded[-52:]))

async def rgba_to_hex(color_dict: dict) -> str:
    r = round(color_dict['r'] * 255)
    g = round(color_dict['g'] * 255)
    b = round(color_dict['b'] * 255)
    a = round(color_dict['a'] * 255)
    return f"{r:02x}{g:02x}{b:02x}{a:02x}"

def freakify(text: str) -> str:
    if not isinstance(text, str):
        return text
    base = "abcdefghijklmnopqrstuvwxyzABCDEFGHJIKLMNOPQRSTUVWXYZ"
    lookup = "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓙𝓘𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩"
    return text.translate(str.maketrans(base, lookup))

old_print = builtins.print
def new_print(*args, **kwargs):
    if params['freaky']:
        old_print(freakify(*args), **kwargs)
    else:
        old_print(*args, **kwargs)

builtins.print = new_print