# cyberbeach.cc & discord.gg/cyberbeach

import os, time, random, string, json, threading, websocket, base64, mimetypes, requests


from colorama import Style
from stealth_requests import StealthSession


from utils.core import STATS, format_status, Beach, format_token_id, setup_logger
from urllib.parse import urlparse
from utils.build import get_build_number, build_super_properties, fetch_cookies, get_fingerprint, build_headers, USER_AGENT, CHROME_VERSION
from utils.solver_wrapper import SolverWrapper
from utils.phone.fivesim import (
    FiveSimClient,
    FiveSimError,
    FiveSimNoNumbersError,
    FiveSimTimeoutError,
)

log = setup_logger(__name__)

API = "https://discord.com/api/v9"
REGISTER_URL = f"{API}/auth/register"
VERIFY_URL = f"{API}/auth/verify"
CAPTCHA_HEADERS = ("x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id")



def check_token_status(session):
    try:
        r = session.get(f"{API}/users/@me")

        log.debug(r.text) # temp

        if r.status_code != 200:
            return "invalid"
        r2 = session.get(f"{API}/users/@me/settings")
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


def encode_image(path: str) -> str | None:
    try:
        mime = mimetypes.guess_type(path)[0] or "image/png"

        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        return f"data:{mime};base64,{encoded}"

    except Exception as e:
        log.error(
            f"{Beach.WARNING}image encode failed error={e}{Style.RESET_ALL}"
        )
        return None


def fetch_dicebear_avatar() -> str | None:
    try:
        seed = random.randint(1, 10_000_000)

        r = requests.get(
            f"https://api.dicebear.com/7.x/pixel-art/png?seed={seed}",
            timeout=10
        )

        r.raise_for_status()

        encoded = base64.b64encode(r.content).decode()

        log.info(
            f"{Beach.INFO}pfp fallback used=dicebear{Style.RESET_ALL}"
        )

        return f"data:image/png;base64,{encoded}"

    except Exception as e:
        log.error(
            f"{Beach.WARNING}dicebear fallback failed error={e}{Style.RESET_ALL}"
        )
        return None


def discord_patch(session, endpoint, payload, success_msg=None):
    try:
        r = session.patch(f"{API}{endpoint}", json=payload)
        r.raise_for_status()

        if success_msg:
            log.info(success_msg)

        return True

    except Exception as e:
        log.error(
            f"{Beach.WARNING}request failed endpoint={endpoint} error={e}{Style.RESET_ALL}"
        )
        return False


def apply_profile(
    session,
    bio=None,
    status=None,
    pfp=None,
    do_bio=True,
    do_status=True,
    do_pfp=True,
    do_hypesquad=True,
):
    # bio
    if do_bio and bio:
        discord_patch(
            session,
            "/users/@me/profile",
            {"bio": bio},
            f"{Beach.INFO}bio updated={Beach.PALM}{bio[:30]}{Style.RESET_ALL}"
        )

    # custom status
    if do_status and status:
        discord_patch(
            session,
            "/users/@me/settings",
            {"custom_status": {"text": status}},
            f"{Beach.INFO}status updated={Beach.PALM}{status[:30]}{Style.RESET_ALL}"
        )

    # hypesquad
    if do_hypesquad:
        houses = {1: "Bravery", 2: "Brilliance", 3: "Balance"}
        house_id = random.choice(tuple(houses))

        try:
            r = session.post(
                f"{API}/hypesquad/online",
                json={"house_id": house_id},
            )
            r.raise_for_status()
            log.info(
                f"{Beach.INFO}hypesquad updated="
                f"{Beach.PALM}{houses[house_id]}{Style.RESET_ALL}"
            )
        except Exception as e:
            log.error(
                f"{Beach.WARNING}hypesquad failed error={e}{Style.RESET_ALL}"
            )

    # avatar
    if do_pfp:
        avatar_data = None

        if pfp and os.path.isfile(pfp):
            avatar_data = encode_image(pfp)
            if avatar_data:
                log.info(
                    f"{Beach.INFO}pfp loaded="
                    f"{Beach.PALM}{os.path.basename(pfp)}{Style.RESET_ALL}"
                )

        avatar_data = avatar_data or fetch_dicebear_avatar()

        if avatar_data:
            discord_patch(
                session,
                "/users/@me",
                {"avatar": avatar_data},
                f"{Beach.INFO}pfp applied successfully{Style.RESET_ALL}"
            )


def _clear_captcha_headers(session):
    for h in CAPTCHA_HEADERS:
        session.headers.pop(h, None)


def _apply_captcha_headers(session, cap_token, rqtoken, session_id):
    session.headers.update({
        "x-captcha-key": cap_token,
        "x-captcha-rqtoken": rqtoken or "",
        "x-captcha-session-id": session_id or "",
    })


def _handle_rate_limit(res_json, status_code):
    if status_code != 429:
        return False
    retry_after = res_json.get("retry_after", 60)
    log.warning(
        f"{Beach.WARNING}rate limited{Style.RESET_ALL}, "
        f"waiting {Beach.SAND}{retry_after:.0f}s{Style.RESET_ALL}..."
    )
    time.sleep(retry_after + 1)
    return True


def _post_json(session, url, payload, retries=1, backoff=1.0):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            res = session.post(url, json=payload)
            try:
                data = res.json()
            except Exception:
                data = {}
            if _handle_rate_limit(data, res.status_code):
                # one extra try after rate limit sleep
                res = session.post(url, json=payload)
                try:
                    data = res.json()
                except Exception:
                    data = {}
            return res, data
        except Exception as e:
            last_exc = e
            if attempt < retries:
                time.sleep(backoff)
    if last_exc:
        log.debug(f"_post_json failed: {type(last_exc).__name__}: {last_exc}")
    return None, None


def _solve_captcha(solver_type, solver_api_key, rqdata, proxy, email):
    log.info(f"{Beach.INFO}solving captcha: email={Beach.PALM}{email}{Style.RESET_ALL}")
    start = time.time()
    try:
        cap_token = SolverWrapper(solver_type, solver_api_key).solve(
            rqdata=rqdata,
            user_agent=USER_AGENT,
            proxy=proxy,
        )
    except TypeError as e:
        log.error(f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}")
        return None, "solver_error"
    except Exception as e:
        log.error(f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}")
        return None, "solver_exception"

    if not cap_token:
        log.warning(
            f"{Beach.WARNING}no captcha available: "
            f"captcha_token={cap_token}{Style.RESET_ALL}"
        )
        return None, None

    log.info(
        f"{Beach.INFO}captcha solved "
        f"({Beach.PALM}{time.time() - start:.1f}s{Style.RESET_ALL})"
    )
    return cap_token, None


def _extract_mail_token(session, verify_url, click_headers, max_hops=2):
    if "token=" in verify_url:
        return verify_url.split("token=")[-1].split("&")[0]

    location = verify_url
    for _ in range(max_hops):
        r = session.get(location, headers=click_headers, allow_redirects=False)
        location = r.headers.get("Location", "")
        if not location:
            return None
        fragment = urlparse(location).fragment
        if fragment and "token=" in fragment:
            return fragment.split("token=")[-1].split("&")[0]
    return None


def _finalize(session, email, password, auth_token, onliner, logger, status=None):
    if status is None:
        status = check_token_status(session)
    save_account(email, password, auth_token, status, logger=logger)
    onliner.stop()


def _do_phone_verification(session, proxy, phone_cfg, solver_type, solver_api_key, email):
    provider = (phone_cfg.get("provider") or "fivesim").lower()
    if provider != "fivesim":
        log.warning(
            f"{Beach.WARNING}phone provider not supported: {provider}{Style.RESET_ALL}"
        )
        return False

    fs_cfg = phone_cfg.get("fivesim", {}) or {}
    token = fs_cfg.get("token")
    if not token:
        log.warning(f"{Beach.WARNING}phone: fivesim token missing in config{Style.RESET_ALL}")
        return False

    client = FiveSimClient(
        api_token=token,
        product="discord",
        country=fs_cfg.get("country", "england"),
        operator=fs_cfg.get("operator", "any"),
    )

    sms_timeout   = float(fs_cfg.get("sms_timeout", 180))
    poll_interval = float(fs_cfg.get("poll_interval", 3))

    # buy a number
    try:
        order = client.buy_number()
    except FiveSimNoNumbersError:
        log.warning(f"{Beach.WARNING}phone: no numbers in stock{Style.RESET_ALL}")
        return False
    except FiveSimError as e:
        log.error(f"{Beach.WARNING}phone: buy failed error={e}{Style.RESET_ALL}")
        return False

    order_id = order.get("id")
    phone    = order.get("phone")
    if not order_id or not phone:
        log.warning(f"{Beach.WARNING}phone: bad order response {order}{Style.RESET_ALL}")
        # no order_id
        return False

    log.info(
        f"{Beach.INFO}phone bought={Beach.PALM}{phone}{Style.RESET_ALL} "
        f"id={Beach.SAND}{order_id}{Style.RESET_ALL}"
    )

    success = False
    try:
        # attach phase
        attach_res, attach_json = _post_json(
            session,
            f"{API}/users/@me/phone",
            {"phone": phone},
            retries=1,
        )
        attach_json = attach_json or {}

        if attach_json.get("captcha_sitekey"):
            cap_token, err = _solve_captcha(
                solver_type, solver_api_key,
                attach_json.get("captcha_rqdata", ""), proxy, email,
            )
            if not cap_token:
                log.warning(f"{Beach.WARNING}phone: captcha failed err={err}{Style.RESET_ALL}")
                return False

            _apply_captcha_headers(
                session,
                cap_token,
                attach_json.get("captcha_rqtoken"),
                attach_json.get("captcha_session_id"),
            )
            attach_res, attach_json = _post_json(
                session, f"{API}/users/@me/phone", {"phone": phone},
            )
            attach_json = attach_json or {}
            _clear_captcha_headers(session)

        if attach_res is None or attach_res.status_code >= 400:
            log.warning(
                f"{Beach.WARNING}phone: attach rejected "
                f"status={getattr(attach_res, 'status_code', '?')} error={attach_json}"
                f"{Style.RESET_ALL}"
            )
            return False

        verification_token = attach_json.get("verification_token")
        if not verification_token:
            log.warning(
                f"{Beach.WARNING}phone: no verification_token in response {attach_json}"
                f"{Style.RESET_ALL}"
            )
            return False

        # wait for SMS
        try:
            code = client.wait_for_code(
                order_id, timeout=sms_timeout, poll_interval=poll_interval
            )
        except FiveSimTimeoutError:
            # refund
            log.warning(f"{Beach.WARNING}phone: sms timeout, refunded{Style.RESET_ALL}")
            return False
        except FiveSimError as e:
            log.error(f"{Beach.WARNING}phone: sms error={e}{Style.RESET_ALL}")
            _safe_ban(client, order_id)
            return False

        log.info(
            f"{Beach.INFO}phone code received={Beach.PALM}{code}{Style.RESET_ALL}"
        )

        # submit code to discord
        verify_res, verify_json = _post_json(
            session,
            f"{API}/phone-verifications/verify",
            {"phone_token": verification_token, "code": str(code)},
            retries=1,
        )
        verify_json = verify_json or {}

        if verify_res is None or verify_res.status_code >= 400:
            log.warning(
                f"{Beach.WARNING}phone: verify rejected "
                f"status={getattr(verify_res, 'status_code', '?')} error={verify_json}"
                f"{Style.RESET_ALL}"
            )
            _safe_ban(client, order_id)
            return False

        phone_token = verify_json.get("token")
        if not phone_token:
            log.warning(
                f"{Beach.WARNING}phone: no token after verify {verify_json}"
                f"{Style.RESET_ALL}"
            )
            _safe_ban(client, order_id)
            return False

        # bind verified phone to account
        bind_res, bind_json = _post_json(
            session,
            f"{API}/users/@me/phone",
            {"phone_token": phone_token},
            retries=1,
        )
        bind_json = bind_json or {}

        if bind_res is None or bind_res.status_code >= 400:
            log.warning(
                f"{Beach.WARNING}phone: bind rejected "
                f"status={getattr(bind_res, 'status_code', '?')} body={bind_json}"
                f"{Style.RESET_ALL}"
            )
            _safe_ban(client, order_id)
            return False

        log.info(
            f"{Beach.INFO}phone verified & bound="
            f"{Beach.PALM}{phone}{Style.RESET_ALL}"
        )
        _safe_finish(client, order_id)
        success = True
        return True

    finally:
        if not success:
            _refund_or_ban(client, order_id)


def _refund_or_ban(client, order_id):
    # incase number fails
    try:
        order = client.check_order(order_id)
        sms_list = order.get("sms") or []
    except Exception as e:
        log.debug(f"5sim check before refund failed: {e}")
        sms_list = []

    if sms_list:
        log.debug(f"5sim order {order_id}: sms already received, banning instead of cancelling")
        _safe_ban(client, order_id)
        return

    try:
        client.cancel_order(order_id)
        log.info(
            f"{Beach.INFO}phone refunded "
            f"id={Beach.SAND}{order_id}{Style.RESET_ALL}"
        )
    except FiveSimError as e:

        log.debug(f"5sim cancel failed, falling back to ban: {e}")
        _safe_ban(client, order_id)
    except Exception as e:
        log.debug(f"5sim cancel raised: {e}")
        _safe_ban(client, order_id)


def _safe_finish(client, order_id):
    try:
        client.finish_order(order_id)
    except Exception as e:
        log.debug(f"5sim finish failed: {e}")


def _safe_cancel(client, order_id):
    try:
        client.cancel_order(order_id)
    except Exception as e:
        log.debug(f"5sim cancel failed: {e}")


def _safe_ban(client, order_id):
    try:
        client.ban_order(order_id)
    except Exception as e:
        log.debug(f"5sim ban failed: {e}")


def reg(
    email,
    username,
    password,
    bio,
    status,
    pfp,
    proxy=None,
    current_num=1,
    logger=None,
    mail_api=None,
    verification_enabled=True,
    solver_type=None,
    solver_api_key=None,
    customise=None,
    phone_cfg=None,
):
    customise = customise or {}
    phone_cfg = phone_cfg or {}
    do_pfp       = customise.get("pfp", True)
    do_bio       = customise.get("bio", True)
    do_status    = customise.get("status", True)
    do_hypesquad = customise.get("hypesquad", True)
    do_phone     = bool(phone_cfg.get("enabled", False))
    
    # setup
    log.info(
        f"{Beach.INFO}worker [ {current_num} ] started "
        f"proxy={Beach.SAND}{proxy.split('@')[-1] if proxy else 'direct'}{Style.RESET_ALL} "
        f"email={Beach.PALM}{email}{Style.RESET_ALL}"
    )

    session = StealthSession()
    if proxy:
        proxy_url = proxy if "://" in proxy else f"http://{proxy}"
        session.proxies = {"http": proxy_url, "https": proxy_url}

    try:
        dcfduid, sdcfduid = fetch_cookies(session)
        fingerprint = get_fingerprint(session, dcfduid, sdcfduid)
    except Exception as e:
        log.error(f"{Beach.WARNING}fingerprint failed: error={e}{Style.RESET_ALL}")
        return

    build_num = get_build_number(proxy)
    session.headers.update(
        build_headers(fingerprint, build_super_properties(build_num))
    )

    base_payload = {
        "fingerprint": fingerprint,
        "date_of_birth": "1997-02-01",
        "consent": True,
    }


    # fake register
    fake_user = "".join(
        random.choice(string.ascii_lowercase + string.digits) for _ in range(12)
    )
    _post_json(session, REGISTER_URL, {
        **base_payload,
        "email": f"{fake_user}@outlook.com",
        "username": fake_user,
        "password": f"{fake_user}Ab1!@#",
    })


    # real register
    register_payload = {
        **base_payload,
        "email": email,
        "username": username,
        "password": password,
    }

    _, res_json = _post_json(session, REGISTER_URL, register_payload)
    if not res_json:
        STATS["error"] += 1
        log.error(f"{Beach.ERROR}register request failed{Style.RESET_ALL}")
        return

    captcha_rqdata = res_json.get("captcha_rqdata")
    if not res_json.get("captcha_sitekey") or not captcha_rqdata:
        log.warning(
            f"{Beach.WARNING}no captcha available: "
            f"captcha_sitekey={res_json.get('captcha_sitekey')} "
            f"captcha_rqdata={captcha_rqdata}{Style.RESET_ALL}"
        )
        return

    # solve register captcha + retry register with captcha headers
    cap_token, _ = _solve_captcha(
        solver_type, solver_api_key, captcha_rqdata, proxy, email
    )
    if not cap_token:
        STATS["error"] += 1
        return

    _apply_captcha_headers(
        session,
        cap_token,
        res_json.get("captcha_rqtoken"),
        res_json.get("captcha_session_id"),
    )

    response, res_data = _post_json(session, REGISTER_URL, register_payload, retries=2)
    if not res_data:
        STATS["error"] += 1
        log.error(f"{Beach.ERROR}register-with-captcha failed{Style.RESET_ALL}")
        return

    if response is not None:
        try:
            log.debug(response.text[:500])
        except Exception:
            pass

    auth_token = res_data.get("token")
    if not auth_token:
        STATS["error"] += 1
        log.error(f"{Beach.ERROR}error={res_data}{Style.RESET_ALL}")
        return

    _clear_captcha_headers(session)
    session.headers.update({"authorization": auth_token})
    log.info(
        f"{Beach.INFO}generated token="
        f"{Beach.PALM}{auth_token[:35]}...{Style.RESET_ALL}"
    )

    onliner = BackgroundOnliner(auth_token)
    onliner.start()


    # skip verification
    if not verification_enabled:
        _finalize(session, email, password, auth_token, onliner, logger)
        return

    log.info(f"{Beach.INFO}status=verification pending{Style.RESET_ALL}")


    # fetch + parse verify url
    verify_url = mail_api.get_verify_url(email, 3, 120, proxy) if mail_api else None
    if not verify_url:
        _finalize(session, email, password, auth_token, onliner, logger)
        return
    

    click_headers = {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": "en-US,en;q=0.9",
        "sec-ch-ua": (
            f'"Chromium";v="{CHROME_VERSION}", '
            f'"Google Chrome";v="{CHROME_VERSION}", '
            f'"Not-A.Brand";v="99"'
        ),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": USER_AGENT,
    }

    try:
        mail_token = _extract_mail_token(session, verify_url, click_headers)
    except Exception:
        mail_token = None

    if not mail_token:
        _finalize(session, email, password, auth_token, onliner, logger)
        return


    # verify
    _clear_captcha_headers(session)
    time.sleep(random.uniform(1, 3))

    _, verify_json = _post_json(session, VERIFY_URL, {"token": mail_token})
    verify_json = verify_json or {}

    if verify_json.get("captcha_sitekey"):
        cap_token, err = _solve_captcha(
            solver_type,
            solver_api_key,
            verify_json.get("captcha_rqdata", ""),
            proxy,
            email,
        )
        if err:
            STATS["error"] += 1
            _finalize(session, email, password, auth_token, onliner, logger, status=err)
            return
        if not cap_token:
            STATS["error"] += 1
            _finalize(session, email, password, auth_token, onliner, logger)
            return

        _apply_captcha_headers(
            session,
            cap_token,
            verify_json.get("captcha_rqtoken"),
            verify_json.get("captcha_session_id"),
        )

        _, verify_json = _post_json(session, VERIFY_URL, {"token": mail_token})
        verify_json = verify_json or {}

    # rotate to new token if discord issued one post-verify
    new_token = verify_json.get("token")
    if new_token:
        auth_token = new_token
        session.headers.update({"authorization": auth_token})

    _clear_captcha_headers(session)

    if do_phone:
        try:
            _do_phone_verification(
                session=session,
                proxy=proxy,
                phone_cfg=phone_cfg,
                solver_type=solver_type,
                solver_api_key=solver_api_key,
                email=email,
            )
        except Exception as e:
            log.warning(
                f"{Beach.WARNING}phone verification crashed: "
                f"{type(e).__name__}: {e}{Style.RESET_ALL}"
            )

    # customise: pfp / bio / status / hypesquad (each toggleable)
    try:
        apply_profile(
            session,
            bio=bio,
            status=status,
            pfp=pfp,
            do_bio=do_bio,
            do_status=do_status,
            do_pfp=do_pfp,
            do_hypesquad=do_hypesquad,
        )
    except Exception as e:
        log.warning(
            f"{Beach.WARNING}apply_profile failed: "
            f"{type(e).__name__}: {e}{Style.RESET_ALL}"
        )

    _finalize(session, email, password, auth_token, onliner, logger)