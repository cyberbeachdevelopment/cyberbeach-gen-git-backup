# cyberbeach.cc & discord.gg/cyberbeach

import asyncio, sys, random, time, threading, os, string

from pathlib import Path
from colorama import Style

from utils.mail import get_mail_api
from utils.account import reg
from utils.core import (
    update_title,
    Beach,
    load_config,
    setup_logger,
    show_banner,
    system,
)
from utils.proxy import proxy_manager

log = setup_logger(__name__)


def title_loop():
    while True:
        update_title()
        time.sleep(0.5)


# load config
config = load_config()
mail_api, provider = get_mail_api(config, log)

# globals
SOLVER_TYPE = None
SOLVER_API_KEY = None
PHONE_PROVIDER = None
PHONE_CFG = {}

verification_enabled = config.get("verification", {}).get("enabled", True)
gen_count = 0

# banner & clear
system(cmd="clear")
show_banner()


SOLVERS = {
    "anysolver":  {"name": "anysolver", "key": "anysolver_api_key"},
}

PHONE_PROVIDERS = {
    "vaksms": {
        "name": "vak-sms",

        "required_fields": [("api_key", "token")],
    },
    "herosms": {
        "name": "hero-sms",
        "required_fields": [("api_key", "token")],
    },
}


def check_structure():
    required_folders = [
        "input",
        "input/user",
        "input/user/pfp",
        "output",
    ]

    default_config = """
{
  "solver": {
    "anysolver_api_key": "your_anysolver_api_key"
  },

  "mail": {
    "provider": "freecustomemail",

    "freecustomemail": {
      "api_key": "your_freecustomemail_api_key"
    },

    "imap": {
      "enabled": false,
      "host": "",
      "port": 993,
      "username": "",
      "password": "",
      "use_ssl": true,
      "mailbox": "INBOX",
      "domain": ""
    }
  },

    "phone": {
    "enabled": false,
    "provider": "herosms_or_vaksms",

    "vaksms": {
      "api_key": "",
      "service": "ds",
      "country": "uk",
      "operator": null,
      "sms_timeout": 180,
      "poll_interval": 3
    },

    "herosms": {
      "api_key": "",
      "service": "ds",
      "country": 16,
      "operator": null,
      "sms_timeout": 180,
      "poll_interval": 3
    }
  }, 

  "verification": {
    "enabled": true
  },

  "customise": {
    "hypesquad": true,
    "pfp": true,
    "bio": true,
    "status": true
  },

  "threads": 1,
  "debug": true
}"""

    required_files = {
        "input/user/bio.txt": "",
        "input/user/status.txt": "",
        "input/user/username.txt": "",
        "input/proxies.txt": "",
        "output/valid.txt": "",
        "output/locked.txt": "",
        "output/invalid.txt": "",
        "input/config.json": default_config,
    }

    for folder in required_folders:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            log.info(
                f"Created folder {Beach.FOAM}→{Style.RESET_ALL} "
                f"{Beach.OCEAN}{folder}{Style.RESET_ALL}"
            )

    for file_path, default_content in required_files.items():
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(default_content)
            log.info(
                f"Created file {Beach.FOAM}→{Style.RESET_ALL} "
                f"{Beach.OCEAN}{file_path}{Style.RESET_ALL}"
            )


check_structure()


def load_profile():
    base_path = Path("input/user")

    username_file = base_path / "username.txt"
    bio_file      = base_path / "bio.txt"
    status_file   = base_path / "status.txt"
    pfp_folder    = base_path / "pfp"

    def read_random_line(file_path: Path):
        try:
            if file_path.exists():
                lines = [
                    ln.strip()
                    for ln in file_path.read_text(encoding="utf-8").splitlines()
                    if ln.strip()
                ]
                return random.choice(lines) if lines else None
        except Exception as e:
            log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )
        return None

    username = read_random_line(username_file)
    bio      = read_random_line(bio_file)
    status   = read_random_line(status_file)

    # random pfp
    pfp = None
    try:
        if pfp_folder.exists() and pfp_folder.is_dir():
            images = [
                str(p)
                for p in pfp_folder.iterdir()
                if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif")
            ]
            if images:
                pfp = random.choice(images)
    except Exception as e:
        log.error(
            f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
        )

    # random password
    password = "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(16)
    )

    if not username:
        username = "".join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(10)
        )

    log.info(
        f"Profile loaded {Beach.FOAM}→{Style.RESET_ALL} "
        f"{Beach.OCEAN}{username or '∅'}{Style.RESET_ALL}"
    )
    log.debug(f"  ├─ bio      = {bio or '∅'}")
    log.debug(f"  ├─ status   = {status or '∅'}")
    log.debug(f"  ├─ pfp      = {pfp or '∅'}")
    log.debug(f"  └─ password = {password}")

    return username, bio, status, pfp, password


def select_solver():
    data = config.get("solver", {}) or {}

    available = []
    for slug, meta in SOLVERS.items():
        api_key = data.get(meta["key"], "")
        if api_key:
            available.append((slug, api_key))

    if not available:
        log.warning(f"API key missing {Beach.FOAM}→{Style.RESET_ALL} no solver configured")
        sys.exit(1)

    slug, api_key = random.choice(available) if len(available) > 1 else available[0]
    log.info(f"Solver {Beach.FOAM}→{Style.RESET_ALL} {Beach.OCEAN}{SOLVERS[slug]['name']}{Style.RESET_ALL}")
    return slug, api_key


def _has_required(sub: dict, required_fields) -> bool:
    for field in required_fields:
        if isinstance(field, (list, tuple)):
            # group
            if not any(sub.get(f) for f in field):
                return False
        else:
            if not sub.get(field):
                return False
    return True


def select_phone_provider():
    phone_cfg = config.get("phone", {}) or {}

    if not phone_cfg.get("enabled", False):
        return None, phone_cfg

    requested = (phone_cfg.get("provider") or "").lower().strip()

    available = []
    for slug, meta in PHONE_PROVIDERS.items():
        sub = phone_cfg.get(slug, {}) or {}
        if _has_required(sub, meta["required_fields"]):
            available.append(slug)

    if not available:
        log.warning(
            f"Phone enabled but no provider configured {Beach.FOAM}→{Style.RESET_ALL} "
            f"{Beach.SAND}set credentials under {Beach.OCEAN}config.phone.<provider>{Style.RESET_ALL}"
        )
        return None, {**phone_cfg, "enabled": False}

    if requested:
        if requested not in PHONE_PROVIDERS:
            log.warning(
                f"Phone provider {Beach.OCEAN}{requested}{Style.RESET_ALL} not supported "
                f"{Beach.FOAM}→{Style.RESET_ALL} "
                f"supported={Beach.OCEAN}{list(PHONE_PROVIDERS)}{Style.RESET_ALL}"
            )
            return None, {**phone_cfg, "enabled": False}

        if requested not in available:
            log.warning(
                f"Phone provider {Beach.OCEAN}{requested}{Style.RESET_ALL} missing required fields "
                f"{Beach.FOAM}→{Style.RESET_ALL} "
                f"available={Beach.OCEAN}{available}{Style.RESET_ALL}"
            )
            return None, {**phone_cfg, "enabled": False}

        chosen = requested
    else:
        chosen = random.choice(available) if len(available) > 1 else available[0]

    log.info(
        f"Phone provider {Beach.FOAM}→{Style.RESET_ALL} "
        f"{Beach.OCEAN}{PHONE_PROVIDERS[chosen]['name']}{Style.RESET_ALL}"
    )

    resolved = {**phone_cfg, "enabled": True, "provider": chosen}
    return chosen, resolved


async def main():
    global SOLVER_TYPE, SOLVER_API_KEY, PHONE_PROVIDER, PHONE_CFG, gen_count

    SOLVER_TYPE, SOLVER_API_KEY = select_solver()
    PHONE_PROVIDER, PHONE_CFG   = select_phone_provider()

    customise_cfg = config.get("customise", {}) or {}

    NUM_THREADS = config.get("threads", 10)
    semaphore = asyncio.Semaphore(NUM_THREADS)

    threading.Thread(target=title_loop, daemon=True).start()

    async def schedule_worker(current_num: int):
        try:
            proxy = await asyncio.to_thread(proxy_manager.pop_top)
            email = await asyncio.to_thread(mail_api.create_account)
            if not email:
                log.warning(
                    f"Failed to create email {Beach.FOAM}→{Style.RESET_ALL} "
                    f"provider={Beach.OCEAN}{provider}{Style.RESET_ALL}"
                )
                return

            username, bio, status, pfp, password = load_profile()

            await asyncio.to_thread(
                reg,
                email, username, password, bio, status, pfp,
                proxy, current_num, log, mail_api,
                verification_enabled, SOLVER_TYPE, SOLVER_API_KEY,
                customise_cfg, PHONE_CFG,
            )
        finally:
            semaphore.release()

    while True:
        await semaphore.acquire()
        gen_count += 1
        current_num = gen_count
        asyncio.create_task(schedule_worker(current_num))


if __name__ == "__main__":
    asyncio.run(main())