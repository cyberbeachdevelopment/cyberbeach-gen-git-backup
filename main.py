# cyberbeach.cc & discord.gg/cyberbeach

import asyncio, sys, random, time, threading, os, string

from pathlib import Path
from colorama import Style

#from config import load_config
from utils.mail import get_mail_api
from utils.account import reg
from utils.core import update_title, Beach, load_config, setup_logger, show_banner, system
from utils.proxy import proxy_manager

log = setup_logger(__name__)

def title_loop():
    while True:
        update_title()
        time.sleep(0.5)    

# load config
config = load_config()
mail_api, provider = get_mail_api(config, log)

# global
SOLVER_TYPE = None
SOLVER_API_KEY = None
verification_enabled = config.get("verification", {}).get("enabled", True)
gen_count = 0

# banner & clear
system(cmd="clear")
show_banner()


# file check
def check_structure():
    required_folders = [
        "input",
        "input/user",
        "input/user/pfp",
        "output"
    ]

    required_files = {
        "input/user/bio.txt": "",
        "input/user/status.txt": "",
        "input/user/username.txt": "",
        "input/proxies.txt": "",
        "output/valid.txt": "",
        "output/locked.txt": "",
        "output/invalid.txt": "",
        "config.json": """{
    "threads": 3,
    "debug": false,

    "data": {
        "rezosolver_api_key": "",
        "anysolver_api_key": "",
        "voidsolver_api_key": ""
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

    "mail": {
        "freecustomemail_api_key": "",

        "smtp": {
            "enabled": false,

            "server": {
                "host": "",
                "port": 465,
                "use_ssl": true
            },

            "imap": {
                "host": "",
                "port": 993,
                "mailbox": "INBOX"
            },

            "auth": {
                "username": "",
                "password": ""
            },

            "domain": ""
        }
    }
}"""
    }

    # folders
    for folder in required_folders:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            log.info(f"{Beach.INFO}created folder={folder}{Style.RESET_ALL}")
    # files
    for file_path, default_content in required_files.items():
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(default_content)

            log.info(f"{Beach.INFO}created file={file_path}{Style.RESET_ALL}")

    log.info(f"{Beach.INFO}structure check complete{Style.RESET_ALL}")

check_structure()

# for customisation
def load_profile():
    base_path = Path("input/user")

    username_file = base_path / "username.txt"
    bio_file = base_path / "bio.txt"
    status_file = base_path / "status.txt"
    pfp_folder = base_path / "pfp"

    def read_file(file_path):
        try:
            if file_path.exists():
                lines = [
                    line.strip()
                    for line in file_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                return random.choice(lines) if lines else None
        except:
            pass
        return None

    username = read_file(username_file)
    bio = read_file(bio_file)
    status = read_file(status_file)

    # random pfp
    pfp = None
    try:
        if pfp_folder.exists() and pfp_folder.is_dir():
            images = [
                str(p)
                for p in pfp_folder.iterdir()
                if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".gif"]
            ]

            if images:
                pfp = random.choice(images)
    except:
        pass

    # random password
    password = ''.join(
        random.choice(string.ascii_letters + string.digits)
        for _ in range(16)
    )

    if not username:
        username = ''.join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in range(10)
        )

    log.info(
        f"{Beach.INFO}profile loader "
        f"username={username if username else 'None'} "
        f"bio={bio if bio else 'None'} "
        f"status={status if status else 'None'} "
        f"pfp={pfp if pfp else 'None'} "
        f"password={password}{Style.RESET_ALL}"
    )

    # return {
    #     "username": username,
    #     "bio": bio,
    #     "status": status,
    #     "pfp": pfp,
    #     "password": password
    # }

    return username, bio, status, pfp, password

# multiple solver support
def select_solver():

    available_solvers = []
    solvers_info = {
        "rezosolver": {"name": "RezoSolver", "key_path": "data.rezosolver_api_key"},
        "anysolver": {"name": "AnySolver.io", "key_path": "data.anysolver_api_key"},
        "razorcap": {"name": "RazorCap", "key_path": "data.razorcap_api_key"},
    }
    for solver_type, _ in solvers_info.items():
        api_key = config.get("data", {}).get(solver_type + "_api_key", "")
        if api_key:
            available_solvers.append(solver_type)

    if not available_solvers:
        log.warning(f"{Beach.WARNING}api key missing: provider={Style.RESET_ALL}")
        sys.exit(1)

    if len(available_solvers) > 1:
        chosen = random.choice(available_solvers)
        log.info(f"{Beach.INFO}solver={solvers_info[chosen]['name']}{Style.RESET_ALL}")
        return chosen
    else:
        log.info(
    f"{Beach.INFO}solver={solvers_info[available_solvers[0]]['name']}{Style.RESET_ALL}"
)
        return available_solvers[0]


# main
async def main():
    # some more globals
    global SOLVER_TYPE, SOLVER_API_KEY, gen_count

    solver_choice = select_solver()
    SOLVER_TYPE = solver_choice
    SOLVER_API_KEY = config.get("data", {}).get(f"{solver_choice}_api_key", "")
    if not SOLVER_API_KEY:
        log.warning(f"{Beach.WARNING}api key missing: provider={Style.RESET_ALL}")
        sys.exit(1)

    NUM_THREADS = config.get("threads", 10)
    semaphore = asyncio.Semaphore(NUM_THREADS)

    # customise toggles (pfp / bio / status / hypesquad)
    customise_cfg = config.get("customise", {}) or {}

    # for title
    threading.Thread(target=title_loop, daemon=True).start()

    async def schedule_worker(current_num: int):
        try:
            # fetch
            proxy = await asyncio.to_thread(proxy_manager.pop_top)
            # dont need it if empty either way

            email = await asyncio.to_thread(mail_api.create_account)

            if not email:
                log.warning(
                    f"{Beach.WARNING}failed to create email "
                    f"provider={provider}{Style.RESET_ALL}"
                )
                return

            username, bio, status, pfp, password = load_profile()

            # run /reg worker
            await asyncio.to_thread(
                reg,
                email,
                username,
                password,
                bio,
                status,
                pfp,
                proxy,
                current_num,
                log,
                mail_api,
                verification_enabled,
                SOLVER_TYPE,
                SOLVER_API_KEY,
                customise_cfg,
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