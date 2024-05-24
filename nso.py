#! /usr/bin/env python3
# Dynamo for Stat.ink
# howlagon 2023

# Much of this code is based loosely on a mix of my own personal research, alongside work on s3s by @frozenpandaman
# https://github.com/frozenpandaman/s3s
# https://github.com/ZekeSnider/NintendoSwitchRESTAPI

import aiohttp, re, base64, hashlib, json
from os import urandom
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from sys import exit

from data import APP_VERSION

SPLATNET_URL: str = "https://api.lp1.av5ja.srv.nintendo.net"
USER_AGENT: str   = 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Mobile Safari/537.36'

NSO_VERSION: str | None     = None
NSO_FALLBACK: str           = "2.10.0"
WEBVIEW_VERSION: str | None = None
WEBVIEW_FALLBACK: str       = "6.0.0-2ba8cb04"

async def get_nso_version() -> str:
    '''Gets the current Nintendo Switch Online app version from the apple app store.'''
    # because the play store is harder to get LOL
    global NSO_VERSION
    if NSO_VERSION is not None:
        return NSO_VERSION
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://apps.apple.com/us/app/nintendo-switch-online/id1234806557") as r:
                soup = BeautifulSoup(await r.text(), 'html.parser')
        p = soup.find("p", {"class": "whats-new__latest__version"})
        version = p.get_text().lstrip("Version ").strip()
    except:
        return NSO_FALLBACK
    NSO_VERSION = version
    return NSO_VERSION

async def get_webview_version() -> str:
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Host': SPLATNET_URL.lstrip('https://'),
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-GPC': '1',
        'TE': 'trailers',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': USER_AGENT,
    }

    cookies = {
        '_dnt': '1',
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(SPLATNET_URL, headers=headers, cookies=cookies) as r:
            if r.status != 200:
                return WEBVIEW_FALLBACK
            text = await r.text()
    soup = BeautifulSoup(text, 'html.parser')
    script_tag = soup.select_one("script[src*='static']")
    if script_tag is None:
        return WEBVIEW_FALLBACK
    script_url = f"{SPLATNET_URL}{script_tag['src']}"
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Host': SPLATNET_URL.lstrip('https://'),
        'Pragma': 'no-cache',
        'Referrer': f'{SPLATNET_URL}/api/graphql',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-GPC': '1',
        'TE': 'trailers',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': USER_AGENT,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(script_url, headers=headers) as script:
            if script.status != 200:
                return WEBVIEW_FALLBACK
            script_text = await script.text()
    pattern = r"\"(?P<hash>[0-9a-f]{40})\".+?\|\|\"revision_info_not_set\".+?(?P<version>\d+\.\d+\.\d+)-"
    match = re.search(pattern, string=script_text)
    if match is None:
        return WEBVIEW_FALLBACK
    version = match.group('version')
    hash = match.group('hash')[:8]
    WEBVIEW_VERSION = f"{version}-{hash}"

    return WEBVIEW_VERSION

async def _get_session_token(code: str, verifier: bytes, stats_for_nerds=True, recursive=False) -> str:
    headers = {
        'Host': 'accounts.nintendo.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        # 'charset': 'utf-8',
        'Connection': 'keep-alive',
        'User-Agent': f'OnlineLounge/{await get_nso_version()} NASDKAPI IOS',
        'Accept': 'application/json',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'gzip',
    }
    body = {
        'client_id': '71b963c1b7b6d119',
        'session_token_code': code,
        'session_token_code_verifier': verifier.replace(b"=", b"")
    }

    async with aiohttp.ClientSession() as session:
        r = await session.post(f'https://accounts.nintendo.com/connect/1.0.0/api/session_token', data=urlencode(body), headers=headers)
        if r.status != 200 and not recursive:
            print(f"Got a non-200 response from Nintendo while fetching session token. Retrying...")
            return await _get_session_token(code, verifier, stats_for_nerds, True)
        elif recursive:
            print(f"Unable to recover! Please try again.")
            if stats_for_nerds: print(f"Response:\n{await r.text()}")
            exit(1)
        try:
            json = await r.json()
            return json['session_token']
        except json.decoder.JSONDecodeError:
            print(f"Got an invalid JSON response from Nintendo while fetching session token. Please try again.")
            if stats_for_nerds: print(f"Response:\n{await r.text()}")
            exit(1)
        except KeyError:
            print(f"Invalid session token code. What.\n\n{await r.text()}")
            exit(1)

async def _get_service_access_tokens(session_token: str) -> dict:
    headers = {
        'Host': 'accounts.nintendo.com',
        'Content-Type': 'application/json',
        'charset': 'utf-8',
        'Connection': 'keep-alive',
        'User-Agent': f'OnlineLounge/{await get_nso_version()} NASDKAPI iOS',
        'Accept': 'application/json',
        'Accept-Language': 'en-us',
        'Accept-Encoding': 'gzip, deflate',
    }
    body = {
        'client_id': '71b963c1b7b6d119',
        'session_token': session_token,
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer-session-token',
    }

    async with aiohttp.ClientSession() as session:
        async with session.post('https://accounts.nintendo.com/connect/1.0.0/api/token', headers=headers, json=body) as r:
            try:
                response = await r.json()
                return {
                    'access_token': response['access_token'],
                    'id_token': response['id_token'],
                }
            except KeyError:
                print(f"Invalid service token code. What.\n\n{await r.text()}")
                exit(1)
            except json.decoder.JSONDecodeError:
                print(f"Got an invalid JSON response from Nintendo while fetching service token. Please try again.")
                exit(1)

async  def _get_user_details(access_token: str) -> dict:
    headers = {
        'Host': 'api.accounts.nintendo.com',
        'Content-Type': 'application/json',
        'charset': 'utf-8',
        'Connection': 'keep-alive',
        'User-Agent': f'OnlineLounge/{await get_nso_version()} NASDKAPI iOS',
        'Accept': 'application/json',
        'Accept-Language': 'en-us',
        'Accept-Encoding': 'gzip, deflate',
        'Authorization': f'Bearer {access_token}'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.accounts.nintendo.com/2.0.0/users/me', headers=headers) as r:
            try:
                data = await r.json()
                return data
            except json.decoder.JSONDecodeError:
                print(f"Got an invalid JSON response from Nintendo while fetching user details. Please try again.")
                exit(1)

async def _get_f_data(service_token: str, na_id: str, hash_method: int = 1, coral_id: int = None) -> tuple[str, int, str]:
    """Calls the imink f-token API to generate the user's f token

    Args:
        service_token (str)
        hash_method (int, optional), Defaults to 1.

    Returns:
        tuple [
            str: f token,
            int: timestamp,
            str: UUID v4
        ]
    """
    assert hash_method in [1, 2]

    headers = {
        'User-Agent': f'howlagon dynamo/{APP_VERSION}',
        'Content-Type': 'application/json',
        'charset': 'utf-8',
    }
    body = {
        'token': service_token,
        'hash_method': hash_method,
        'na_id': na_id,
    }
    if hash_method == 2 and coral_id is not None:
        body['coral_id'] = coral_id
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f'https://api.imink.app/f', data=json.dumps(body), headers=headers) as r:
            try:
                response = await r.json()
                return response['f'], response['timestamp'], response['request_id']
            except KeyError:
                print(f"Received an invalid JSON response from imink. Please try again.\n{await r.text()}")
                exit(1)

async def _get_web_api_response(id_token: str, user_data: dict, f_data: tuple) -> str:
    body =  { 'parameter': {
        'f': f_data[0],
        'naIdToken':  id_token,
        'language':   user_data['language'],
        'naCountry':  user_data['country'],
        'naBirthday': user_data['birthday'],
        'timestamp':  f_data[1],
        'requestId':  f_data[2],
    }}
    headers = {
        'X-Platform': 'Android',
        'X-ProductVersion': await get_nso_version(),
        'Content-Type': 'application/json; charset=utf-8',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': f'com.nintendo.znca/{await get_nso_version()}(Android/7.1.2)',
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f'https://api-lp1.znc.srv.nintendo.net/v3/Account/Login', json=body, headers=headers) as r:
            try:
                response = await r.json()
                return response['result']
            except KeyError:
                print(f"Received an invalid JSON response from Nintendo while fetching login access token. Please try again.\n{await r.text()}")
                exit(1)

async def _get_g_token(web_api_response: dict, service_access_response: dict, f_data: dict, user_data: dict) -> str:
    access_token = web_api_response['webApiServerCredential']['accessToken']
    coral_user_id = web_api_response['user']['id']
    id_token = service_access_response['id_token']
    f_token, timestamp, uuid = f_data
    headers = {
        'X-Platform': 'Android',
        'X-ProductVersion': await get_nso_version(),
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json; charset=utf-8',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': f'com.nintendo.znca/{await get_nso_version()}(Android/7.1.2)',
    }
    body = { 'parameter': {
        'f': f_token,
        'id': 4834290508791808,
        'registrationToken': access_token,
        'requestId': uuid,
        'timestamp': timestamp
    }}
    na_id = user_data['id']
    
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api-lp1.znc.srv.nintendo.net/v2/Game/GetWebServiceToken', json=body, headers=headers) as r:
            response = await r.json()
        if response.get('status') == 9403:
            f_token, timestamp, uuid = await _get_f_data(access_token, na_id, 2, coral_id=coral_user_id)
            body = { 'parameter': {
                'f': f_token,
                'id': 4834290508791808,
                'registrationToken': access_token,
                'requestId': uuid,
                'timestamp': timestamp
            }}
            async with session.post('https://api-lp1.znc.srv.nintendo.net/v2/Game/GetWebServiceToken', json=body, headers=headers) as r:
                response = await r.json()
    if response.get('status') == 9403:
        print("ERROR_INVALID_GAME_WEB_TOKEN (unauthorized).")
        exit(3)
    try:
        g_token = response['result']['accessToken']
    except KeyError:
        print(f"Received an invalid JSON response from Nintendo while fetching g token. Please try again.\n{await r.text()}")
    return g_token

async def _get_bullet_token(g_token: str, user_data: dict) -> str:
    assert all(key in user_data.keys() for key in ['language', 'country']), f"Invalid user data. {user_data}"
    headers = {
        'Accept-Language': user_data['language'],
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'Origin': SPLATNET_URL,
        'User-Agent': USER_AGENT,
        'X-Web-View-Ver': await get_webview_version(),
        'X-Requested-With': 'com.nintendo.znca',
        'X-NACountry': user_data['country'],
    }
    cookies = {
        '_gtoken': g_token,
        '_dnt': '1',
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f'{SPLATNET_URL}/api/bullet_tokens', headers=headers, cookies=cookies) as r:
            if r.status >= 300: print(await r.text())
            match r.status:
                case 204:
                    print("User has not played online before.")
                    exit(1)
                case 401:
                    print("ERROR_INVALID_GAME_WEB_TOKEN (unauthorized).")
                    exit(3)
                case 403:
                    print("ERROR_OBSOLETE_VERSION (forbidden).")
                    exit(3)
            try:
                bullet_data = await r.json()
                return bullet_data['bulletToken']
            except [json.decoder.JSONDecodeError, TypeError]:
                print(f"Invalid JSON response from Nintendo to {r.request.url}.\n{await r.text()}")
                exit(3)
            except:
                print(f"Invalid bullet token code. What.\n\n{await r.text()}")
                exit(3)

async def generate_new_tokens(session_token: str) -> tuple:
    service_access_response = await _get_service_access_tokens(session_token)
    access_token, id_token = service_access_response['access_token'], service_access_response['id_token']
    user_data = await _get_user_details(access_token)
    f_data = await _get_f_data(id_token, user_data['id'])
    web_api_response = await _get_web_api_response(id_token, user_data, f_data)
    f_data = await _get_f_data(access_token, user_data['id'])
    g_token = await _get_g_token(web_api_response, service_access_response, f_data, user_data)
    bullet_token = await _get_bullet_token(g_token, user_data)
    return bullet_token, g_token

class LoginManager:
    '''Allows for splitting up the login process into two steps, for use alongside something such as Flask. Should only be used once per account.'''
    def __init__(self) -> None:
        session_state = base64.urlsafe_b64encode(urandom(36))
        self.session_code_verifier = base64.urlsafe_b64encode(urandom(32))
        session_cv_hash = hashlib.sha256()
        session_cv_hash.update(self.session_code_verifier.replace(b"=", b""))
        session_code_challenge = base64.urlsafe_b64encode(session_cv_hash.digest())
        self.body = {
            'state':                               session_state,
            'redirect_uri':                        'npf71b963c1b7b6d119://auth',
            'client_id':                           '71b963c1b7b6d119',
            'scope':                               'openid user user.birthday user.mii user.screenName',
            'response_type':                       'session_token_code',
            'session_token_code_challenge':        session_code_challenge.replace(b"=", b""),
            'session_token_code_challenge_method': 'S256',
            'theme':                               'login_form'
        }
        self.login_url = f'https://accounts.nintendo.com/connect/1.0.0/authorize?{urlencode(self.body)}'
    async def login(self, code: str) -> tuple:
        try:
            session_token_code = re.search(r'de=(.*)&st', code).group(1)
            session_token = await _get_session_token(session_token_code, self.session_code_verifier)
        except KeyError:
            print("Invalid session token code.")
        service_access_response = await _get_service_access_tokens(session_token)
        access_token, id_token = service_access_response['access_token'], service_access_response['id_token']
        user_data = await _get_user_details(access_token)
        f_data = await _get_f_data(id_token, user_data['id'])
        web_api_response = await _get_web_api_response(id_token, user_data, f_data)
        f_data = await _get_f_data(access_token, user_data['id'])
        g_token = await _get_g_token(web_api_response, service_access_response, f_data, user_data)
        bullet_token = await _get_bullet_token(g_token, user_data)
        return user_data['nickname'], session_token, bullet_token, g_token, json.dumps(user_data), None

    async def login_with_token(self, session_token: str) -> tuple:
        service_access_response = await _get_service_access_tokens(session_token)
        access_token, id_token = service_access_response['access_token'], service_access_response['id_token']
        user_data = await _get_user_details(access_token)
        f_data = await _get_f_data(id_token, user_data['id'])
        web_api_response = await _get_web_api_response(id_token, user_data, f_data)
        f_data = await _get_f_data(access_token, user_data['id'])
        g_token = await _get_g_token(web_api_response, service_access_response, f_data, user_data)
        bullet_token = await _get_bullet_token(g_token, user_data)
        return user_data['nickname'], session_token, bullet_token, g_token, json.dumps(user_data), None