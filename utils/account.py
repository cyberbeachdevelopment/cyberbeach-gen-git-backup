# cyberbeach.cc & discord.gg/cyberbeach

import os, time, random, string, json, threading, websocket, base64, mimetypes, requests


from colorama import Style
from stealth_requests import StealthSession


from utils.core import STATS, format_status, Beach, format_token_id, setup_logger
from urllib.parse import urlparse
from utils.build import get_build_number, build_super_properties, fetch_cookies, get_fingerprint, build_headers, USER_AGENT, CHROME_VERSION
from utils.solver_wrapper import SolverWrapper

log = setup_logger(__name__)


def check_token_status(session):
    try:
        r = session.get("https://discord.com/api/v9/users/@me")

        log.debug(r.text) # temp

        if r.status_code != 200:
            return "invalid"
        r2 = session.get("https://discord.com/api/v9/users/@me/settings")
        if r2.status_code == 200:
            return "Valid"
        elif r2.status_code == 403:
            return "locked"
    except Exception:
        pass
    return "invalid"


def save_account(email, password, token, token_status, logger=None):

    os.makedirs("output", exist_ok=True)

    user = email.split("@")[0] if "@" in email else email
    short_token = format_token_id(token)

    # decide file + stats only (no formatting, no emojis)
    if token_status == "Valid":
        filename = "output/valid.txt"
        STATS["unlocked"] += 1
        log_fn = log.info
        code = 200

    elif token_status == "locked":
        filename = "output/locked.txt"
        STATS["locked"] += 1
        log_fn = log.warning
        code = 403

    else:
        filename = "output/invalid.txt"
        STATS["invalid"] += 1
        log_fn = log.error
        code = 400

    status_text = format_status(code)

    log_msg = (
        f"{Beach.OCEAN}{short_token}{Style.RESET_ALL} "
        f"{status_text} "
        f"{Beach.FOAM}user={user} "
        f"{Beach.SAND}email={email}"
    )

    log_fn(log_msg)

    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{email}:{password}:{token}\n")


# credits to someone on github lol
class BackgroundOnliner:
    
    def __init__(self, token):
        self.token = token
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        try:
            ws = websocket.WebSocket()
            ws.settimeout(10)
            ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")
            hello = json.loads(ws.recv())
            heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

            identify = {
                "op": 2,
                "d": {
                    "token": self.token,
                    "properties": {"$os": "Windows"},
                },
            }
            ws.send(json.dumps(identify))
            ready = False
            for _ in range(10):
                resp = json.loads(ws.recv())
                if resp.get("t") == "READY":
                    ready = True
                    break
                if resp.get("op") == 9:
                    ws.close()
                    return
            if not ready:
                ws.close()
                return
            while not self._stop.is_set():
                ws.send(json.dumps({"op": 1, "d": None}))
                self._stop.wait(heartbeat_interval)
            ws.close()
        except Exception:
            pass


def apply_profile(session, bio=None, status=None, pfp=None):
    try:
        # bio
        if bio:
            bio_payload = {
                "bio": bio
            }

            session.patch(
                "https://discord.com/api/v9/users/@me/profile",
                json=bio_payload
            )

            log.info(
                f"{Beach.INFO}bio updated={Beach.PALM}{bio[:30]}{Style.RESET_ALL}"
            )

        # status
        if status:
            status_payload = {
                "custom_status": {
                    "text": status
                }
            }

            session.patch(
                "https://discord.com/api/v9/users/@me/settings",
                json=status_payload
            )

            log.info(
                f"{Beach.INFO}status updated={Beach.PALM}{status[:30]}{Style.RESET_ALL}"
            )

        # hypesquad  
        # will be toggable later  
        house_id = random.choice([1, 2, 3])

        houses = {
            1: "Bravery",
            2: "Brilliance",
            3: "Balance"
        }

        hypesquad_payload = {
            "house_id": house_id
        }

        session.post(
            "https://discord.com/api/v9/hypesquad/online",
            json=hypesquad_payload
        )

        log.info(
            f"{Beach.INFO}hypesquad updated={Beach.PALM}{houses[house_id]}{Style.RESET_ALL}"
        )

        # pfp
        # PRIMARY
        avatar_data = None

        if pfp and os.path.exists(pfp) and os.path.isfile(pfp):
            try:
                mime_type = mimetypes.guess_type(pfp)[0] or "image/png"

                with open(pfp, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()

                avatar_data = f"data:{mime_type};base64,{encoded}"

                log.info(
                    f"{Beach.INFO}pfp updated={Beach.PALM}{os.path.basename(pfp)}{Style.RESET_ALL}"
                )

            except Exception as e:
                log.warning(
                    f"{Beach.WARNING}local pfp failed error={e}{Style.RESET_ALL}"
                )

        # FALLBACK (dicebear temp)
        if not avatar_data:
            try:
                seed = random.randint(1, 10_000_000)
                url = f"https://api.dicebear.com/7.x/pixel-art/png?seed={seed}"

                r = requests.get(url, timeout=10)
                r.raise_for_status()

                encoded = base64.b64encode(r.content).decode()
                avatar_data = f"data:image/png;base64,{encoded}"

                log.info(
                    f"{Beach.INFO}pfp fallback used=dicebear{Style.RESET_ALL}"
                )

            except Exception as e:
                log.warning(
                    f"{Beach.WARNING}dicebear fallback failed error={e}{Style.RESET_ALL}"
                )

        if avatar_data:
            try:
                session.patch(
                    "https://discord.com/api/v9/users/@me",
                    json={"avatar": avatar_data}
                )

                log.info(
                    f"{Beach.INFO}pfp applied successfully{Style.RESET_ALL}"
                )

            except Exception as e:
                log.warning(
                    f"{Beach.WARNING}discord update failed error={e}{Style.RESET_ALL}"
                )

    except Exception as e:
        log.warning(
            f"{Beach.WARNING}profile update failed error={e}{Style.RESET_ALL}"
        )


def reg(email, username, password, bio, status, pfp, proxy=None, current_num=1, logger=None, mail_api=None, verification_enabled=True, solver_type=None, solver_api_key=None):

    log.info(
    f"{Beach.INFO}worker [ {current_num} ] started "
    f"proxy={Beach.SAND}{proxy.split('@')[-1] if proxy else 'direct'}{Style.RESET_ALL} "
    f"email={Beach.PALM}{email}{Style.RESET_ALL}"
)
    session = StealthSession()
    if proxy:
        proxy_url = f"http://{proxy}" if "://" not in proxy else proxy
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
    try:
        dcfduid, sdcfduid = fetch_cookies(session)
        fingerprint = get_fingerprint(session, dcfduid, sdcfduid)
    except Exception:
        log.warning(f"{Beach.WARNING}fingerprint failed{Style.RESET_ALL}")
        return
    build_num = get_build_number(proxy)
    super_props = build_super_properties(build_num)
    headers = build_headers(fingerprint, super_props)
    session.headers.update(headers)
    fake_user = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(12))
    fake_payload = {
        "fingerprint": fingerprint,
        "email": f"{fake_user}@outlook.com",
        "username": fake_user,
        "password": f"{fake_user}Ab1!@#",
        "date_of_birth": "1997-02-01",
        "consent": True,
    }
    try:
        fake_res = session.post("https://discord.com/api/v9/auth/register", json=fake_payload)
        fake_json = fake_res.json()
        if fake_res.status_code == 429:
            retry_after = fake_json.get("retry_after", 60)
            log.warning(
    f"{Beach.WARNING}rate limited{Style.RESET_ALL}, "
    f"waiting {Beach.SAND}{retry_after:.0f}s{Style.RESET_ALL}..."
)
            time.sleep(retry_after + 1)
    except Exception:
        pass

    register_payload = {
        "fingerprint": fingerprint,
        "email": email,
        "username": username,
        "password": password,
        "date_of_birth": "1997-02-01",
        "consent": True,
    }

    res = session.post("https://discord.com/api/v9/auth/register", json=register_payload)
    start_time = time.time()
    res_json = res.json()

    if res.status_code == 429:
        retry_after = res_json.get("retry_after", 60)
        log.warning(
    f"{Beach.WARNING}rate limited{Style.RESET_ALL}, "
    f"waiting {Beach.SAND}{retry_after:.0f}s{Style.RESET_ALL}..."
)
        time.sleep(retry_after + 1)
        res = session.post("https://discord.com/api/v9/auth/register", json=register_payload)
        res_json = res.json()

    captcha_sitekey = res_json.get("captcha_sitekey")
    captcha_rqdata = res_json.get("captcha_rqdata")
    captcha_rqtoken = res_json.get("captcha_rqtoken")
    captcha_session_id = res_json.get("captcha_session_id")

    if not captcha_sitekey or not captcha_rqdata:
        log.warning(f"{Beach.WARNING}no captcha available: captcha_sitekey={captcha_sitekey} captcha_rqdata={captcha_rqdata}{Style.RESET_ALL}")
        return

    log.info(
        f"{Beach.INFO}solving captcha: email={Beach.PALM}{email}{Style.RESET_ALL}"
    )
    #cap_token, cookies = SolverWrapper(
    cap_token = SolverWrapper(
        solver_type,
        solver_api_key
    ).solve(
        rqdata=captcha_rqdata,
        user_agent=USER_AGENT,
        proxy=proxy
    )

    if not cap_token:
        log.warning(f"{Beach.WARNING}no captcha available: captcha_token={cap_token}{Style.RESET_ALL}")
        STATS["error"] += 1
        return

    # if cookies:
    #     for k, v in cookies.items():
    #         session.cookies.set(k, v)
    solve_time = time.time() - start_time
    log.info(
    f"{Beach.INFO}captcha solved ({Beach.PALM}{solve_time:.1f}s{Style.RESET_ALL})"
)

    session.headers.update({
        "x-captcha-key": cap_token,
        "x-captcha-rqtoken": captcha_rqtoken,
        "x-captcha-session-id": captcha_session_id,
    })

    response = None
    for attempt in range(3):
        try:
            response = session.post("https://discord.com/api/v9/auth/register", json=register_payload)
            break
        except Exception:
            if attempt < 2:
                time.sleep(1)
            else:
                return
    try:
        raw_text = response.text
        log.debug(f"{raw_text[:500]}")
    except Exception as e:
        STATS["error"] += 1
        log.error(
            f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
        )
        
    try:
        res_data = response.json()
    except Exception as e:
        STATS["error"] += 1
        log.error(
            f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
        )
        return
    if 'token' not in res_data:
        STATS["error"] += 1
        log.error(
            f"{Beach.ERROR}error={res_data}{Style.RESET_ALL}"
        )
        return
    auth_token = res_data['token']
    for h in ["x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id"]:
        session.headers.pop(h, None)
    session.headers.update({"authorization": auth_token})
    log.info(
        f"{Beach.INFO}generated token={Beach.PALM}{auth_token[:35]}...{Style.RESET_ALL}"
    )

    onliner = BackgroundOnliner(auth_token)
    onliner.start()

    if not verification_enabled:
        pre_verify_status = check_token_status(session)
        save_account(email, password, auth_token, pre_verify_status, logger=logger)
        onliner.stop()
        return

    log.info(f"{Beach.INFO}status=verification pending{Style.RESET_ALL}")
    
    verify_url = None
    if mail_api:
        verify_url = mail_api.get_verify_url(email, 3, 120, proxy)
    if not verify_url:
        token_status = check_token_status(session)
        save_account(email, password, auth_token, token_status, logger=logger)
        onliner.stop()
        return

    try:
        click_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'sec-ch-ua': f'"Chromium";v="{CHROME_VERSION}", "Google Chrome";v="{CHROME_VERSION}", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': USER_AGENT,
        }

        mail_token = None

        if "token=" in verify_url:
            mail_token = verify_url.split("token=")[-1].split("&")[0]

        if not mail_token:
            location = ""
            r1 = session.get(verify_url, headers=click_headers, allow_redirects=False)
            location = r1.headers.get("Location", "")

            if location:
                fragment = urlparse(location).fragment
                if fragment and "token=" in fragment:
                    mail_token = fragment.split("token=")[-1].split("&")[0]

            if not mail_token and location:
                r2 = session.get(location, headers=click_headers, allow_redirects=False)
                location2 = r2.headers.get("Location", "")
                if location2:
                    fragment2 = urlparse(location2).fragment
                    if fragment2 and "token=" in fragment2:
                        mail_token = fragment2.split("token=")[-1].split("&")[0]

        if not mail_token:
            token_status = check_token_status(session)
            save_account(email, password, auth_token, token_status, logger=logger)
            onliner.stop()
            return

    except Exception:
        token_status = check_token_status(session)
        save_account(email, password, auth_token, token_status, logger=logger)
        onliner.stop()
        return

    for h in ["x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id"]:
        session.headers.pop(h, None)

    time.sleep(random.uniform(1, 3))

    verify_res = session.post(
        "https://discord.com/api/v9/auth/verify",
        json={"token": mail_token}
    )
    verify_json = verify_res.json()

    if verify_json.get("captcha_sitekey"):
        log.info(
            f"{Beach.INFO}solving captcha: email={Beach.PALM}{email}{Style.RESET_ALL}"
        )

        verify_start = time.time()

        try:
            solver = SolverWrapper(solver_type, solver_api_key)

            #args
            sitekey = verify_json["captcha_sitekey"]
            rqdata = verify_json.get("captcha_rqdata", "")

            # verify_cap_token, verify_cookies = solver.solve(
            #     sitekey,
            #     rqdata,
            #     USER_AGENT,
            #     proxy
            # )

            verify_cap_token = solver.solve(
                rqdata=rqdata,
                user_agent=USER_AGENT,
                proxy=proxy
            )

            verify_cookies = None
        except TypeError as e:
            log.error(
            f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
        )
            STATS["error"] += 1

            save_account(email, password, auth_token, "solver_error", logger=logger)
            onliner.stop()
            return

        except Exception as e:
            log.error(
            f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
        )
            STATS["error"] += 1

            save_account(email, password, auth_token, "solver_exception", logger=logger)
            onliner.stop()
            return

        if not verify_cap_token:
            log.warning(f"{Beach.WARNING}no captcha available: captcha_token={verify_cap_token}{Style.RESET_ALL}")
            STATS["error"] += 1

            token_status = check_token_status(session)
            save_account(email, password, auth_token, token_status, logger=logger)
            onliner.stop()
            return

        verify_solve_time = time.time() - verify_start
        log.info(
            f"{Beach.INFO}captcha solved ({Beach.PALM}{verify_solve_time:.1f}s{Style.RESET_ALL})"
        )

        if verify_cookies:
            for k, v in verify_cookies.items():
                session.cookies.set(k, v)

        session.headers.update({
            "x-captcha-key": verify_cap_token,
            "x-captcha-rqtoken": verify_json.get("captcha_rqtoken", ""),
            "x-captcha-session-id": verify_json.get("captcha_session_id", ""),
        })

        verify_res = session.post(
            "https://discord.com/api/v9/auth/verify",
            json={"token": mail_token}
        )
        verify_json = verify_res.json()

    new_token = verify_json.get("token")
    if new_token:
        auth_token = new_token
        session.headers.update({"authorization": auth_token})    

    for h in ["x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id"]:
        session.headers.pop(h, None)

    # pfp, bio, status
    apply_profile(session, bio, status, pfp)    

    token_status = check_token_status(session)
    save_account(email, password, auth_token, token_status, logger=logger)
    onliner.stop()