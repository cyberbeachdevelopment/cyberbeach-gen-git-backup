# cyberbeach.cc & discord.gg/cyberbeach


import time, os, logging, sys


from colorama import Fore, Style

from utils.version import __version__
from config import load_config

config = load_config()
START_TIME = time.time()


# ! CUSTOM LEVELS
AD_LEVEL = 25
logging.addLevelName(AD_LEVEL, "AD")


def ad(self, message, *args, **kwargs):
    if self.isEnabledFor(AD_LEVEL):
        self._log(AD_LEVEL, message, args, **kwargs)


logging.Logger.ad = ad


# ! STATS
STATS = {
    "unlocked": 0,
    "invalid": 0,
    "locked": 0,
    "rate": 0,
    "error": 0,
}


# ! CPM
def get_cpm():
    elapsed = time.time() - START_TIME

    total = (
        STATS["unlocked"] +
        STATS["invalid"] +
        STATS["locked"] +
        STATS["rate"] +
        STATS["error"]
    )

    return int((total / elapsed) * 60) if elapsed > 0 else 0


# ! LIVE
def update_stats(code):
    STATS["checked"] += 1

    if code == 200:
        STATS["valid"] += 1
    elif code == 401:
        STATS["invalid"] += 1
    elif code == 403:
        STATS["locked"] += 1
    elif code == 429:
        STATS["rate"] += 1
    else:
        STATS["error"] += 1


# ! FORMAT
def format_token_id(token: str) -> str:
    if token and len(token) > 10:
        return f"{token[:4]}...{token[-4:]}"
    elif token and len(token) > 0:
        return f"{token[:4]}.."
    else:
        return "Unknown***"


# ! PALETTE
class Beach:
    OCEAN = Fore.CYAN
    DEEP = Fore.BLUE
    SAND = Fore.YELLOW
    SUNSET = Fore.LIGHTMAGENTA_EX
    CORAL = Fore.LIGHTRED_EX
    FOAM = Fore.WHITE
    PALM = Fore.GREEN
    GLOW = Style.BRIGHT

    INFO = FOAM
    WARNING = SAND
    ERROR = CORAL
    DEBUG = DEEP


# ! HELPER
class CyberBeachFormatter(logging.Formatter):
    LEVEL_STYLES = {
        "DEBUG": Beach.DEEP + "🌊 DEBUG",
        "INFO": Beach.FOAM + "🏝️ INFO ",
        "AD": Beach.SUNSET + Style.BRIGHT + "📢 AD   ",
        "WARNING": Beach.SAND + "🫧 WARN ",
        "ERROR": Beach.CORAL + "🔥 ERROR",
        "CRITICAL": Beach.CORAL + Style.BRIGHT + "💀 CRIT ",
    }

    GREY = Fore.LIGHTBLACK_EX  # <-- add this

    def format(self, record):
        level = self.LEVEL_STYLES.get(record.levelname, record.levelname)
        time_str = time.strftime("%H:%M:%S", time.localtime(record.created))

        # original message (no color)
        msg = record.getMessage()

        # apply grey ONLY to message part
        grey_msg = f"{self.GREY}{msg}{Style.RESET_ALL}"

        return (
            f"{Beach.OCEAN}{time_str}{Style.RESET_ALL} | "
            f"{level}{Style.RESET_ALL} | "
            f"{grey_msg}"
        )


# ! LOGGER
DEBUG_MODE = config.get("debug", False)

def setup_logger(name="cyberbeach"):
    os.makedirs("log", exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = "%(message)s"

    console = logging.StreamHandler(sys.stdout)

    # debug=true
    console.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

    console.setFormatter(CyberBeachFormatter(fmt))

    file = logging.FileHandler("log/logs.txt", encoding="utf-8")

    # debug=true
    file.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

    file.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        "%Y-%m-%d %H:%M:%S"
    ))

    logger.addHandler(console)
    logger.addHandler(file)

    return logger


log = setup_logger(__name__)

# ! MAP
STATUS_MAP = {
    200: ("UNLOCKED ✅", Beach.PALM),
    401: ("INVALID ❌", Beach.CORAL),
    403: ("LOCKED 🔒", Beach.SUNSET),
    429: ("RATE ⏳", Beach.SAND),
}


def format_status(code):
    label, color = STATUS_MAP.get(code, ("ERROR 💥", Beach.CORAL))
    return f"{color}{label:<12} [{code}]{Style.RESET_ALL}"


# ! SYSTEM 
def system(cmd=None, title=None):
    if cmd == "clear":
        os.system("cls" if os.name == "nt" else "clear")

    if title and os.name == "nt":
        os.system(f'title "{title}"')


# ! TITLE
_last = 0
def update_title(title=None, delay=0.5):
    if title is None:
        title = f"🌊 v={__version__}"

    global _last
    now = time.time()

    if now - _last > delay:
        #elapsed = now - START_TIME
        cpm = get_cpm()

        total = (
            STATS["unlocked"] +
            STATS["locked"] +
            STATS["invalid"]
        )

        # unlocked increases %, locked/invalid decrease it
        rate_percent = (
            (STATS["unlocked"] / total) * 100
            if total > 0 else 0
        )

        t = (
            f"{title} | "
            f"unlocked={STATS['unlocked']} "
            f"locked={STATS['locked']} "
            f"invalid={STATS['invalid']} "
            f"rate={rate_percent:.1f}% "
            f"error={STATS['error']} "
            f"cpm={cpm}"
        )

        system(title=t)
        _last = now


# ! BANNER
def show_banner():
    print(Fore.YELLOW + Style.BRIGHT + r"""
⠀⠀⠀⠀⠀⠀⠀⣀⣀⣀⣀⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⠻⢿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣀⣤⣶⣶⣦⣄⠙⣿⣿⣿⣇⣠⣶⣾⣿⣷⣶⣶⠄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣷⣼⣿⣿⣿⣿⣿⣿⣿⠟⠋⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠘⠛⠉⠉⠉⠁⠉⠉⠛⢿⣿⣿⣿⣿⣿⣿⣷⣶⣶⣤⣀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⠿⠛⢿⣿⣿⣿⣿⣟⠛⠻⢿⣷⣦⡀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⡿⠁⠀⠀⢸⣿⣿⡿⠻⣿⣷⡀⠀⠉⠻⢷⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⡿⠁⠀⠀⠀⠸⣿⡿⠁⠀⠈⢿⣇⠀⠀⠀⠀⠀⠀⠀                              X       anysolver.com
⠀⠀⠀⠀⠀⠀⠀⢠⣿⣿⠁⠀⠀⠀⠀⠀⠉⠀⠀⠀⠀⠀⠏⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢠⣿⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⣾⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣼⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢠⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀cyberbeach.cc
⠀⠀⠀⠀⣼⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀& discord.gg/cyberbeach
⠀⠀⠀⠀⠈⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀& github.com/megaatverizon 
""" + Style.RESET_ALL)


# ! EXIT
def exit_program():
    input("press enter to exit")    