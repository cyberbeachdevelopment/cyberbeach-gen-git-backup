# anysolver.com

import requests
import time
from utils.core import *
log = setup_logger(__name__)

class AnySolverClient:
    def __init__(self, api_key: str, base_url: str = "https://api.anysolver.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.base_task = {
            "type": "PopularCaptchaEnterpriseToken",
            "websiteURL": "https://discord.com",
            "websiteKey": "a9b5fb07-92ff-493f-86fe-352a2803b3df",
        }

        log.debug(
            f"Client initialized {Beach.FOAM}→{Style.RESET_ALL} "
            f"base_url={Beach.OCEAN}{self.base_url}{Style.RESET_ALL}"
        )

    def _build_task(self, proxy=None, userAgent=None, rqdata=None, sessionId=None, sitekey=None):
        task = self.base_task.copy()

        if sitekey:
            task["websiteKey"] = sitekey
        if proxy:
            task["proxy"] = "http://" + proxy
        # if userAgent:
        #     task["userAgent"] = userAgent
        if rqdata:
            task["rqdata"] = rqdata
        # if sessionId:
        #     task["sessionId"] = sessionId

        # print(task)

        log.debug(
            f"Task built {Beach.FOAM}→{Style.RESET_ALL} "
            f"sitekey={Beach.OCEAN}{task.get('websiteKey')}{Style.RESET_ALL} "
            f"proxy={Beach.OCEAN}{'yes' if proxy else 'no'}{Style.RESET_ALL} "
            f"ua={Beach.OCEAN}{'yes' if userAgent else 'no'}{Style.RESET_ALL} "
            f"rqdata={Beach.OCEAN}{'yes' if rqdata else 'no'}{Style.RESET_ALL}"
        )

        return task

    def solve_captcha(
        self,
        rqdata: str,
        user_agent: str,
        proxy: str | None = None,
    ):
        task = self._build_task(proxy, user_agent, rqdata)#, sessionId, sitekey)

        try:

            create = requests.post(
                f"{self.base_url}/createTask",
                json={"clientKey": self.api_key, "task": task},
                timeout=30
            ).json()

            if create.get("errorId", 0) != 0:
                log.warning(
                    f"Create failed {Beach.FOAM}→{Style.RESET_ALL} "
                    f"error={Beach.CORAL}{create.get('errorCode')}{Style.RESET_ALL} "
                    f"desc={Beach.CORAL}{create.get('errorDescription')}{Style.RESET_ALL}"
                )
                raise Exception(
                    f"{create.get('errorCode')}: {create.get('errorDescription', 'Unknown error')}"
                )

            task_id = create["taskId"]
            log.debug(
                f"Task created {Beach.FOAM}→{Style.RESET_ALL} "
                f"id={Beach.OCEAN}{task_id}{Style.RESET_ALL}"
            )

        except Exception as e:
            STATS["error"] += 1
            log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )
            raise

        while True:
            time.sleep(3)

            try:
                result = requests.post(
                    f"{self.base_url}/getTaskResult",
                    json={"clientKey": self.api_key, "taskId": task_id},
                    timeout=30
                ).json()

                # print(result)

                status = result.get("status", "unknown")

                log.debug(
                    f"Task status {Beach.FOAM}→{Style.RESET_ALL} "
                    f"id={Beach.OCEAN}{task_id}{Style.RESET_ALL} "
                    f"status={Beach.OCEAN}{status}{Style.RESET_ALL}"
                )

                if status == "ready":
                    log.debug(
                        f"Task solved {Beach.FOAM}→{Style.RESET_ALL} "
                        f"id={Beach.OCEAN}{task_id}{Style.RESET_ALL}"
                    )
                    return result["solution"]["token"]

                if status == "failed":
                    log.warning(
                        f"Task failed {Beach.FOAM}→{Style.RESET_ALL} "
                        f"id={Beach.OCEAN}{task_id}{Style.RESET_ALL} "
                        f"error={Beach.CORAL}{result.get('errorCode')}{Style.RESET_ALL} "
                        f"desc={Beach.CORAL}{result.get('errorDescription')}{Style.RESET_ALL}"
                    )
                    return None

                if status != "processing":
                    log.warning(
                        f"Unexpected status {Beach.FOAM}→{Style.RESET_ALL} "
                        f"id={Beach.OCEAN}{task_id}{Style.RESET_ALL} "
                        f"status={Beach.SAND}{status}{Style.RESET_ALL}"
                    )
                    return None

            except Exception as e:
                STATS["error"] += 1
                log.warning(
                    f"Poll error {Beach.FOAM}→{Style.RESET_ALL} "
                    f"id={Beach.OCEAN}{task_id}{Style.RESET_ALL} "
                    f"error={Beach.SAND}{e}{Style.RESET_ALL}"
                )
                return None
