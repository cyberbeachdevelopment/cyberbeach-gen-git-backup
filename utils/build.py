# cyberbeach.cc & discord.gg/cyberbeach

import base64, json, platform, uuid,re 

from stealth_requests import StealthSession

CHROME_VERSION = 124
USER_AGENT = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{CHROME_VERSION}.0.0.0 Safari/537.36"


def get_build_number(proxy=None):
    try:
        sess = StealthSession()
        if proxy:
            proxy_url = f"http://{proxy}" if "://" not in proxy else proxy
            sess.proxies = {"http": proxy_url, "https": proxy_url}
        page = sess.get("https://discord.com/app").text
        assets = re.findall(r'src="/assets/([^\"]+)"', page)
        for asset in reversed(assets):
            js = sess.get(f"https://discord.com/assets/{asset}").text
            if "buildNumber:" in js:
                try:
                    return int(js.split('buildNumber:"')[1].split('"')[0])
                except Exception:
                    pass
    except Exception:
        pass
    return 502645


def build_super_properties(build_number):
    payload = {
        "os": "Windows",
        "browser": "Chrome",
        "device": "",
        "system_locale": "en-US",
        "browser_user_agent": USER_AGENT,
        "browser_version": f"{CHROME_VERSION}.0.0.0",
        "os_version": platform.release(),
        "referrer": "https://discord.com/",
        "referring_domain": "discord.com",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": build_number,
        "client_event_source": None,
        "has_client_mods": False,
        "client_launch_id": str(uuid.uuid4()),
        "launch_signature": str(uuid.uuid4()),
        "client_heartbeat_session_id": str(uuid.uuid4()),
        "client_app_state": "focused",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()


def fetch_cookies(session):
    session.get("https://discord.com")
    cookies = session.cookies.get_dict()
    dcfduid = cookies.get("__dcfduid")
    sdcfduid = cookies.get("__sdcfduid")
    return dcfduid, sdcfduid


def get_fingerprint(session, dcfduid, sdcfduid):
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "cookie": f"__dcfduid={dcfduid}; __sdcfduid={sdcfduid};",
        "sec-ch-ua": f'"Chromium";v="{CHROME_VERSION}", "Google Chrome";v="{CHROME_VERSION}", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": USER_AGENT
    }
    session.headers = headers
    data = session.get("https://discord.com/api/v9/experiments")
    try:
        return data.json().get("fingerprint")
    except Exception:
        return None


def build_headers(fingerprint, super_props):
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/",
        "priority": "u=1, i",
        "sec-ch-ua": f'"Chromium";v="{CHROME_VERSION}", "Google Chrome";v="{CHROME_VERSION}", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": USER_AGENT,
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-discord-timezone": "America/Los_Angeles",
        "x-fingerprint": fingerprint,
        "x-super-properties": super_props,
    }