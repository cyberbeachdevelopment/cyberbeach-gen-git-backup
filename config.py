# cyberbeach.cc & discord.gg/cyberbeach

import json

#from utils.core import setup_logger, STATS, Beach
from colorama import Style

#log = setup_logger(__name__)


# load
def load_config():
    config = {}
    try:
        with open("input/config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        # STATS["error"] += 1
        # log.error(
        #     f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
        # )
        pass
    return config
