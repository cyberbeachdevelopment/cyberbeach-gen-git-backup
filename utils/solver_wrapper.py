# cyberbeach.cc & discord.gg/cyberbeach

from utils.core import *

from solvers.anysolver import AnySolverClient


log = setup_logger(__name__)


DEFAULT_SITEKEY = "a9b5fb07-92ff-493f-86fe-352a2803b3df" # sitekey
DEFAULT_PAGEURL = "https://discord.com/register" # discord.com



# universal solver
class SolverWrapper:
    

    PROVIDERS = {
        "anysolver": AnySolverClient,
    }

    def __init__(
        self,
        provider: str,
        api_key: str,
        **kwargs,
    ):
        provider = provider.lower()

        if provider not in self.PROVIDERS:
            raise ValueError(
                f"unsupported provider '{provider}' "
                f"(available: {list(self.PROVIDERS.keys())})"
            )

        self.provider = provider
        self.client = self.PROVIDERS[provider](
            api_key=api_key,
            **kwargs,
        )

        log.debug(
            f"Solver wrapper initialized {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}{provider}{Style.RESET_ALL}"
        )

    def solve(
        self,
        rqdata: str,
        user_agent: str,
        proxy: str | None = None,
    ):
        return self.client.solve_captcha(
            rqdata=rqdata,
            user_agent=user_agent,
            proxy=proxy,
        )