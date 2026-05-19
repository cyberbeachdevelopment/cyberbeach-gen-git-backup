# anysolver.io

import requests, time
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

        log.debug(f"client initialized base_url={self.base_url}")

    def _build_task(self, proxy=None, userAgent=None, rqdata=None, sessionId=None, sitekey=None):
        task = self.base_task.copy()

        if sitekey:
            task["websiteKey"] = sitekey
        if proxy:
            task["proxy"] = "http://" + proxy
        if userAgent:
            task["userAgent"] = userAgent
        if rqdata:
            task["rqdata"] = rqdata
        if sessionId:
            task["sessionId"] = sessionId

        log.debug(
            f"task built sitekey={task.get('websiteKey')} "
            f"proxy={'yes' if proxy else 'no'} "
            f"ua={'yes' if userAgent else 'no'} "
            f"rqdata={'yes' if rqdata else 'no'}"
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
            log.debug("creating task...")
            create = requests.post(
                f"{self.base_url}/createTask",
                json={"clientKey": self.api_key, "task": task},
                timeout=30
            ).json()

            if create.get("errorId") != 0:
                log.error(
                    f"create failed error={create.get('errorCode')} "
                    f"desc={create.get('errorDescription')}"
                )
                raise Exception(
                    f"{create.get('errorCode')}: {create.get('errorDescription', 'Unknown error')}"
                )

            task_id = create["taskId"]
            log.debug(f"task created id={task_id}")

        except Exception as e:
            STATS["error"] += 1
            log.error(f"create exception error={e}")
            raise

        while True:
            time.sleep(3)

            try:
                result = requests.post(
                    f"{self.base_url}/getTaskResult",
                    json={"clientKey": self.api_key, "taskId": task_id},
                    timeout=30
                ).json()

                status = result.get("status")

                log.debug(f"id={task_id} status={status}")

                if status == "ready":
                    log.debug(f"task solved id={task_id}")
                    return result["solution"]["token"]

                if status == "failed":
                    log.error(
                        f"id={task_id} failed error={result.get('errorCode')} "
                        f"desc={result.get('errorDescription')}"
                    )
                    raise Exception(
                        f"{result.get('errorCode')}: {result.get('errorDescription', 'Unknown error')}"
                    )

                if status != "processing":
                    log.warning(f"id={task_id} unexpected_status={status}")
                    raise Exception(f"Unexpected status: {status}")

            except Exception as e:
                STATS["error"] += 1
                log.warning(f"id={task_id} poll_error={e}")
