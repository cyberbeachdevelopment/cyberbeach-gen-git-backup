# cyberbeach.cc & discord.gg/cyberbeach

import os, time, random, string, json, threading, websocket, base64, mimetypes, requests


from colorama import Style
from stealth_requests import StealthSession


from utils.core import STATS, format_status, Beach, format_token_id, setup_logger
from urllib.parse import urlparse
from utils.build import get_build_number, build_super_properties, fetch_cookies, get_fingerprint, build_headers, USER_AGENT, CHROME_VERSION
from utils.solver_wrapper import SolverWrapper
from utils.phone_wrapper import PhoneWrapper

log = setup_logger(__name__)

API = "https://discord.com/api/v9"
REGISTER_URL = f"{API}/auth/register"
VERIFY_URL = f"{API}/auth/verify"
CAPTCHA_HEADERS = ("x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id")



def check_token_status(session):
    try:
        r = session.get(f"{API}/users/@me")

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


# credits to someone on github lol, not made by cyberbeach
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
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
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
            f"PFP fallback {Beach.FOAM}→{Style.RESET_ALL} "
            f"used={Beach.OCEAN}dicebear{Style.RESET_ALL}"
        )

        return f"data:image/png;base64,{encoded}"

    except Exception as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )
        return None


def discord_patch(session, endpoint, payload, success_msg=None):
    try:
        r = session.patch(f"{API}{endpoint}", json=payload)
        r.raise_for_status()

        return True

    except Exception as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
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
            f"Bio updated {Beach.FOAM}→{Style.RESET_ALL} {Beach.OCEAN}{bio[:30]}{Style.RESET_ALL}"
        )

    # custom status
    if do_status and status:
        discord_patch(
            session,
            "/users/@me/settings",
            {"custom_status": {"text": status}},
            f"Status updated {Beach.FOAM}→{Style.RESET_ALL} {Beach.OCEAN}{status[:30]}{Style.RESET_ALL}"
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
                f"Hypesquad updated {Beach.FOAM}→{Style.RESET_ALL} "
                f"{Beach.OCEAN}{houses[house_id]}{Style.RESET_ALL}"
            )
        except Exception as e:
            log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )

    # avatar
    if do_pfp:
        avatar_data = None

        if pfp and os.path.isfile(pfp):
            avatar_data = encode_image(pfp)
            if avatar_data:
                log.info(
                    f"PFP loaded {Beach.FOAM}→{Style.RESET_ALL} "
                    f"{Beach.OCEAN}{os.path.basename(pfp)}{Style.RESET_ALL}"
                )

        avatar_data = avatar_data or fetch_dicebear_avatar()

        if avatar_data:
            discord_patch(
                session,
                "/users/@me",
                {"avatar": avatar_data},
                f"PFP applied {Beach.FOAM}→{Style.RESET_ALL} {Beach.OCEAN}success{Style.RESET_ALL}"
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
        log.debug(
            f"POST JSON failed {Beach.FOAM}→{Style.RESET_ALL} "
            f"type={Beach.OCEAN}{type(last_exc).__name__}{Style.RESET_ALL} "
            f"error={Beach.CORAL}{last_exc}{Style.RESET_ALL}"
        )
    return None, None


def _solve_captcha(solver_type, solver_api_key, rqdata, proxy, email):
    log.info(
        f"Solving captcha {Beach.FOAM}→{Style.RESET_ALL} "
        f"email={Beach.OCEAN}{email}{Style.RESET_ALL}"
    )
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
        # log.warning(
        #     f"No captcha available {Beach.FOAM}→{Style.RESET_ALL} "
        #     f"captcha_token={Beach.SAND}{cap_token}{Style.RESET_ALL}"
        # )
        return None, None

    log.info(
        f"Captcha solved {Beach.FOAM}→{Style.RESET_ALL} "
        f"{Beach.PALM}{time.time() - start:.1f}s{Style.RESET_ALL}"
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


### phone shit ###


def _do_phone_verification(session, proxy, phone_cfg, solver_type, solver_api_key, email):
    if not phone_cfg.get("enabled", False):
        return False

    provider = (phone_cfg.get("provider") or "vaksms").lower()
    if provider not in PhoneWrapper.PROVIDERS:
        log.warning(
            f"Phone provider not supported {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.SAND}{provider}{Style.RESET_ALL}"
        )
        return False

    sub_cfg = phone_cfg.get(provider, {}) or {}
    api_key = sub_cfg.get("api_key") or sub_cfg.get("token")
    if not api_key:
        log.warning(
            f"Phone api_key/token missing in config {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.SAND}{provider}{Style.RESET_ALL}"
        )
        return False

    # idk its weird
    default_country = 0 if provider == "herosms" else "ru"

    try:
        client = PhoneWrapper(
            provider=provider,
            api_key=api_key,
            service=sub_cfg.get("service", "ds"),
            country=sub_cfg.get("country", default_country),
            operator=sub_cfg.get("operator"),
            sms_timeout=float(sub_cfg.get("sms_timeout", 180)),
            poll_interval=float(sub_cfg.get("poll_interval", 3)),
        )
    except ValueError as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )
        return False

    no_numbers_excs = _no_numbers_excs_for(provider)
    base_excs       = _base_excs_for(provider)

    # buy a number
    try:
        order = client.buy_number()
    except no_numbers_excs:
        log.warning(f"Phone has no numbers in stock {Beach.FOAM}→{Style.RESET_ALL} {Beach.SAND}empty pool{Style.RESET_ALL}")
        return False
    except base_excs as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )
        return False

    order_id = order.get("id")
    phone    = order.get("phone")
    if not order_id or not phone:
        log.warning(
            f"Phone bad order response {Beach.FOAM}→{Style.RESET_ALL} "
            f"order={Beach.SAND}{order}{Style.RESET_ALL}"
        )
        return False

    # discord wants E.164 with leading '+' but vak-sms/hero-sms return digits only
    phone_e164 = "+" + "".join(c for c in str(phone) if c.isdigit())

    if len(phone_e164) < 8:
        log.warning("Suspicious phone length")
        return False

    log.info(
        f"Phone bought {Beach.FOAM}→{Style.RESET_ALL} "
        f"{Beach.PALM}{phone_e164}{Style.RESET_ALL} "
        f"id={Beach.OCEAN}{order_id}{Style.RESET_ALL} "
        f"provider={Beach.OCEAN}{provider}{Style.RESET_ALL}"
    )

    success = False
    try:
        # attach phase
        attach_res, attach_json = _post_json(
            session,
            f"{API}/users/@me/phone",
            {"phone": phone_e164},
            retries=1,
        )
        attach_json = attach_json or {}

        if attach_json.get("captcha_sitekey"):
            cap_token, err = _solve_captcha(
                solver_type, solver_api_key,
                attach_json.get("captcha_rqdata", ""), proxy, email,
            )
            if not cap_token:
                log.warning(
                    f"Phone captcha failed {Beach.FOAM}→{Style.RESET_ALL} "
                    f"error={Beach.CORAL}{err}{Style.RESET_ALL}"
                )
                return False


            _apply_captcha_headers(
                session,
                cap_token,
                attach_json.get("captcha_rqtoken"),
                attach_json.get("captcha_session_id"),
            )


            attach_res, attach_json = _post_json(
                session, f"{API}/users/@me/phone", {"phone": phone_e164},
            )
            attach_json = attach_json or {}
            _clear_captcha_headers(session)

        if attach_res is None or attach_res.status_code >= 400:
            log.warning(
                f"Phone attach rejected {Beach.FOAM}→{Style.RESET_ALL} "
                f"status={Beach.SAND}{getattr(attach_res, 'status_code', '?')}{Style.RESET_ALL} "
                f"error={Beach.CORAL}{attach_json}{Style.RESET_ALL}"
            )
            return False

        verification_token = attach_json.get("verification_token")

        if not verification_token:
            log.warning(
                f"Phone no verification_token in response {Beach.FOAM}→{Style.RESET_ALL} "
                f"response={Beach.SAND}{attach_json}{Style.RESET_ALL}"
            )
            return False

        verification_token = None

        # wait for SMS
        try:
            code = client.wait_for_code(order_id)
        except _timeout_excs_for(provider):
            log.warning(
                f"Phone SMS timeout {Beach.FOAM}→{Style.RESET_ALL} "
                f"{Beach.SAND}refunded{Style.RESET_ALL}"
            )
            return False
        except base_excs as e:
            log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )
            _safe_cancel(client, order_id)
            return False

        log.info(
            f"Phone code received {Beach.FOAM}→{Style.RESET_ALL} "
            f"{Beach.PALM}{code}{Style.RESET_ALL}"
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
                f"Phone verify rejected {Beach.FOAM}→{Style.RESET_ALL} "
                f"status={Beach.SAND}{getattr(verify_res, 'status_code', '?')}{Style.RESET_ALL} "
                f"error={Beach.CORAL}{verify_json}{Style.RESET_ALL}"
            )
            _safe_cancel(client, order_id)
            return False

        phone_token = verify_json.get("token")
        if not phone_token:
            log.warning(
                f"Phone no token after verify {Beach.FOAM}→{Style.RESET_ALL} "
                f"response={Beach.SAND}{verify_json}{Style.RESET_ALL}"
            )
            _safe_cancel(client, order_id)
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
                f"Phone bind rejected {Beach.FOAM}→{Style.RESET_ALL} "
                f"status={Beach.SAND}{getattr(bind_res, 'status_code', '?')}{Style.RESET_ALL} "
                f"body={Beach.CORAL}{bind_json}{Style.RESET_ALL}"
            )
            _safe_cancel(client, order_id)
            return False

        log.info(
            f"Phone verified & bound {Beach.FOAM}→{Style.RESET_ALL} "
            f"{Beach.PALM}{phone_e164}{Style.RESET_ALL}"
        )
        _safe_finish(client, order_id)
        success = True
        return True

    finally:
        if not success:
            # _refund_or_cancel(client, order_id)
            threading.Thread(target=_refund_or_cancel, args=(client, order_id), daemon=True).start()


def _no_numbers_excs_for(provider: str) -> tuple:
    if provider == "vaksms":
        from utils.phone.vaksms import VakSmsNoNumbersError
        return (VakSmsNoNumbersError,)
    if provider == "herosms":
        from utils.phone.herosms import HeroSmsNoNumbersError
        return (HeroSmsNoNumbersError,)
    return ()


def _timeout_excs_for(provider: str) -> tuple:
    if provider == "vaksms":
        from utils.phone.vaksms import VakSmsTimeoutError
        return (VakSmsTimeoutError,)
    if provider == "herosms":
        from utils.phone.herosms import HeroSmsTimeoutError
        return (HeroSmsTimeoutError,)
    return ()


def _base_excs_for(provider: str) -> tuple:
    if provider == "vaksms":
        from utils.phone.vaksms import VakSmsError
        return (VakSmsError,)
    if provider == "herosms":
        from utils.phone.herosms import HeroSmsError
        return (HeroSmsError,)
    return (Exception,)


def _refund_or_cancel(client: "PhoneWrapper", order_id):
    time.sleep(121) # secs, globally to prevent cancellation failure

    sms_already_received = False
    try:
        # both wrappers
        order = client.client.check_order(order_id)
        if isinstance(order, dict):
            # 5sim style
            if order.get("sms"):
                sms_already_received = True
            # vak-sms / hero-sms style
            if order.get("smsCode") or order.get("code"):
                sms_already_received = True
            if (order.get("status") or "").lower() in ("ok", "send", "status_ok"):
                sms_already_received = True
    except Exception as e:
        log.debug(
            f"Pre-cancel check failed {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}{client.provider}{Style.RESET_ALL} "
            f"error={Beach.CORAL}{e}{Style.RESET_ALL}"
        )

    if sms_already_received:
        log.debug(
            f"SMS already received, finishing instead of cancelling {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}{client.provider}{Style.RESET_ALL} "
            f"order={Beach.OCEAN}{order_id}{Style.RESET_ALL}"
        )
        _safe_finish(client, order_id)
        return

    try:
        client.cancel_order(order_id)
        log.info(
            f"Phone refunded {Beach.FOAM}→{Style.RESET_ALL} "
            f"id={Beach.OCEAN}{order_id}{Style.RESET_ALL}"
        )
    except Exception as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )


def _safe_finish(client: "PhoneWrapper", order_id):
    try:
        client.finish_order(order_id)
    except Exception as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )


def _safe_cancel(client: "PhoneWrapper", order_id):
    try:
        client.cancel_order(order_id)
    except Exception as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )


### phone shit ###


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
        f"Worker {Beach.OCEAN}[{current_num}]{Style.RESET_ALL} started {Beach.FOAM}→{Style.RESET_ALL} "
        f"proxy={Beach.OCEAN}{proxy.split('@')[-1] if proxy else 'direct'}{Style.RESET_ALL} "
        f"email={Beach.OCEAN}{email}{Style.RESET_ALL}"
    )

    session = StealthSession()
    if proxy:
        proxy_url = proxy if "://" in proxy else f"http://{proxy}"
        session.proxies = {"http": proxy_url, "https": proxy_url}

    try:
        dcfduid, sdcfduid = fetch_cookies(session)
        fingerprint = get_fingerprint(session, dcfduid, sdcfduid)
    except Exception as e:
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )
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
        log.error(
            f"Register request failed {Beach.FOAM}✗{Style.RESET_ALL}"
        )
        return

    captcha_rqdata = res_json.get("captcha_rqdata")
    if not res_json.get("captcha_sitekey") or not captcha_rqdata:
        log.warning(
            f"No captcha available {Beach.FOAM}→{Style.RESET_ALL} "
            f"sitekey={Beach.OCEAN}{res_json.get('captcha_sitekey')}{Style.RESET_ALL} "
            f"rqdata={Beach.OCEAN}{captcha_rqdata}{Style.RESET_ALL}"
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

    _, res_data = _post_json(session, REGISTER_URL, register_payload, retries=2)
    if not res_data:
        STATS["error"] += 1
        log.error(
            f"Register with captcha failed {Beach.FOAM}✗{Style.RESET_ALL}"
        )
        return

    # if response is not None:
    #     try:
    #         log.debug(response.text[:500])
    #     except Exception:
    #         pass

    auth_token = res_data.get("token")

    if not auth_token:
        STATS["error"] += 1
        log.error(
            f"Error {Beach.FOAM}→{Style.RESET_ALL} "
            f"{Beach.CORAL}{res_data}{Style.RESET_ALL}"
        )
        return

    _clear_captcha_headers(session)
    session.headers.update({"authorization": auth_token})
    log.info(
        f"Generated token {Beach.FOAM}→{Style.RESET_ALL} "
        f"{Beach.PALM}{auth_token[:35]}...{Style.RESET_ALL}"
    )

    onliner = BackgroundOnliner(auth_token)
    onliner.start()


    # skip verification
    if not verification_enabled:
        _finalize(session, email, password, auth_token, onliner, logger)
        return

    log.info(
        f"Status {Beach.FOAM}→{Style.RESET_ALL} "
        f"{Beach.SAND}verification pending{Style.RESET_ALL}"
    )


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

    log.info(
        f"Email verified & bound {Beach.FOAM}→{Style.RESET_ALL} "
        f"{Beach.PALM}{email}{Style.RESET_ALL}"
    )

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
            log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
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
        log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )

    _finalize(session, email, password, auth_token, onliner, logger)