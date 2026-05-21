# cyberbeach.cc & discord.gg/cyberbeach

import base64, json, platform, uuid, re, requests

from stealth_requests import StealthSession

from utils.core import setup_logger, STATS, Beach, Style
log = setup_logger(__name__)


def get_latest_chrome_version():
    try:
        r = requests.get(
            "https://versionhistory.googleapis.com/v1/chrome/platforms/win/channels/stable/versions",
            timeout=5,
        )
        version = r.json()["versions"][0]["version"]
        major = int(version.split(".")[0])
        log.debug(
            f"Resolved Chrome version {Beach.FOAM}→{Style.RESET_ALL} "
            f"version={Beach.OCEAN}{version}{Style.RESET_ALL} "
            f"major={Beach.OCEAN}{major}{Style.RESET_ALL}"
        )
        return major
    except Exception as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )

        return 131  # fallback


# chrome is now dynamic yay
CHROME_VERSION = get_latest_chrome_version()
# edge needed for xbox lol
EDGE_VERSION = CHROME_VERSION
log.debug(f"using CHROME_VERSION={CHROME_VERSION} EDGE_VERSION={EDGE_VERSION}")


USER_AGENT = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/{CHROME_VERSION}.0.0.0 Safari/537.36 "
    f"Edg/{EDGE_VERSION}.0.0.0 "
    f"Xbox; Xbox One)"
)

# xbox ua template
SEC_CH_UA = (
    f'"Chromium";v="{CHROME_VERSION}", '
    f'"Microsoft Edge";v="{EDGE_VERSION}", '
    f'"Not-A.Brand";v="99"'
)
SEC_CH_UA_PLATFORM = '"Xbox"'


def get_build_number(proxy=None):
    try:
        sess = StealthSession()
        if proxy:
            proxy_url = f"http://{proxy}" if "://" not in proxy else proxy
            sess.proxies = {"http": proxy_url, "https": proxy_url}

        page = sess.get("https://discord.com/app").text
        assets = re.findall(r'src="/assets/([^\"]+)"', page)

        for _, asset in enumerate(reversed(assets)):
            js = sess.get(f"https://discord.com/assets/{asset}").text
            if "buildNumber:" in js:
                try:
                    build = int(js.split('buildNumber:"')[1].split('"')[0])
                    log.debug(
                        f"Found build number {Beach.FOAM}→{Style.RESET_ALL} "
                        f"build={Beach.OCEAN}{build}{Style.RESET_ALL} "
                        f"asset={Beach.OCEAN}{asset}{Style.RESET_ALL}"
                    )
                    return build
                except Exception as e:
                    log.debug(
                        f"Build number parse failed {Beach.FOAM}→{Style.RESET_ALL} "
                        f"asset={Beach.OCEAN}{asset}{Style.RESET_ALL} "
                        f"err={Beach.CORAL}{e!r}{Style.RESET_ALL}"
                    )
    except Exception as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )
    return 502645


def build_super_properties(build_number):

    payload = {
        "os": "Xbox",
        "browser": "Microsoft Edge",
        "device": "Xbox One",
        "system_locale": "en-US",
        "browser_user_agent": USER_AGENT,
        "browser_version": f"{EDGE_VERSION}.0.0.0",
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
    encoded = base64.b64encode(raw).decode()

    log.debug(
        f"Super props encoded {Beach.FOAM}→{Style.RESET_ALL} "
        f"raw_len={Beach.OCEAN}{len(raw)}{Style.RESET_ALL} "
        f"b64_len={Beach.OCEAN}{len(encoded)}{Style.RESET_ALL}"
    )

    return encoded


def fetch_cookies(session):

    session.get("https://discord.com")

    cookies = session.cookies.get_dict()
    dcfduid = cookies.get("__dcfduid")
    sdcfduid = cookies.get("__sdcfduid")

    log.debug(
        f"Cookies fetched {Beach.FOAM}→{Style.RESET_ALL} "
        f"dcfduid={Beach.OCEAN}{'present' if dcfduid else 'missing'}{Style.RESET_ALL} "
        f"sdcfduid={Beach.OCEAN}{'present' if sdcfduid else 'missing'}{Style.RESET_ALL} "
        f"total_cookies={Beach.OCEAN}{len(cookies)}{Style.RESET_ALL}"
    )

    return dcfduid, sdcfduid


def get_fingerprint(session, dcfduid, sdcfduid):

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "cookie": f"__dcfduid={dcfduid}; __sdcfduid={sdcfduid};",
        "sec-ch-ua": SEC_CH_UA,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": SEC_CH_UA_PLATFORM,
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": USER_AGENT,
    }
    session.headers = headers

    res = session.get("https://discord.com/api/v9/experiments")

    if res.status_code != 200:
        raise RuntimeError(
            f"experiments returned status={res.status_code} error={res.text[:200]}"
        )

    try:
        fp = res.json().get("fingerprint")
    except ValueError as e:
        raise RuntimeError(f"experiments non-json error={res.text[:200]}") from e

    if not fp:
        raise RuntimeError(f"experiments missing fingerprint field error={res.text[:200]}")

    log.info(
        f"Fingerprint acquired {Beach.FOAM}→{Style.RESET_ALL} "
        f"{Beach.OCEAN}{fp}{Style.RESET_ALL}"
    )
    return fp


def build_headers(fingerprint, super_props):

    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/",
        "priority": "u=1, i",
        "sec-ch-ua": SEC_CH_UA,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": SEC_CH_UA_PLATFORM,
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

    log.debug(
        f"API headers built {Beach.FOAM}→{Style.RESET_ALL} "
        f"header_count={Beach.OCEAN}{len(headers)}{Style.RESET_ALL}"
    )
    return headers