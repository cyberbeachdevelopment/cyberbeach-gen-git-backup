# voidsolver.tech

import requests
import time

from utils.core import *

log = setup_logger(__name__)


class VoidSolverClient:
    """razor died so yeah new solver and dat"""

    BASE_URL = "https://api.voidsolver.tech"

    CREATE_PATH = "/tasks/create"
    RESULT_PATH = "/tasks/result/{task_id}"


    TASK_ID_FIELD = "task_id"
    STATUS_FIELD = "status"
    SOLUTION_FIELD = "solution"

    # status values
    STATUS_READY = "ready"
    STATUS_PROCESSING = "processing"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.site_key = "a9b5fb07-92ff-493f-86fe-352a2803b3df"
        self.site_url = "discord.com"

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

        log.debug(f"client initialized base_url={self.BASE_URL}")


    # public api
    def solve_captcha(
        self,
        rqdata: str,
        user_agent: str,
        proxy: str | None = None,
    ):
        """solve hcaptcha via voidsolver standard solver"""
        log.debug("solve start")

        task_id = self._create_task(rqdata, user_agent, proxy)
        return self._poll_result(task_id)


    # internals
    def _create_task(self, rqdata: str, user_agent: str, proxy: str | None):
        payload = {
            "type": "hcaptcha",
            "sitekey": self.site_key,
            "siteurl": self.site_url,
            "rqdata": rqdata,
            "useragent": user_agent,
        }
        if proxy:
            payload["proxy"] = proxy

        try:
            log.debug(
                f"creating task site={self.site_url} "
                f"proxy={'yes' if proxy else 'no'} "
                f"rqdata={'yes' if rqdata else 'no'}"
            )

            response = self._session.post(
                f"{self.BASE_URL}{self.CREATE_PATH}",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            task_id = data.get(self.TASK_ID_FIELD)
            if not task_id:
                log.warning(f"create failed response={data}")
                raise Exception(f"missing {self.TASK_ID_FIELD} in response: {data}")

            log.debug(f"task created id={task_id}")
            return task_id

        except requests.RequestException as e:
            STATS["error"] += 1
            log.error(f"create error={e}")
            raise

    def _poll_result(self, task_id: str, poll_interval: float = 1.0, max_wait: float = 180.0):
        url = f"{self.BASE_URL}{self.RESULT_PATH.format(task_id=task_id)}"
        deadline = time.time() + max_wait

        while True:
            if time.time() > deadline:
                STATS["error"] += 1
                log.error(f"id={task_id} timeout after {max_wait}s")
                raise Exception(f"task {task_id} timed out")

            try:
                result = self._session.get(url, timeout=30)
                result.raise_for_status()
                data = result.json()

                status = data.get(self.STATUS_FIELD)
                log.debug(f"id={task_id} status={status}")

                # success — accept a few common spellings
                if status in (self.STATUS_READY, "success", "completed", "solved"):
                    solution = (
                        data.get(self.SOLUTION_FIELD)
                        or data.get("response_key")
                        or data.get("token")
                        or data.get("generated_pass_UUID")
                    )
                    if not solution:
                        log.error(f"id={task_id} success but no solution field: {data}")
                        raise Exception(f"no solution in response: {data}")

                    log.debug(f"task solved id={task_id}")
                    return solution

                # still processing
                if status in (self.STATUS_PROCESSING, "pending", "processing", "queued"):
                    time.sleep(poll_interval)
                    continue

                # anything else = failure
                STATS["error"] += 1
                log.error(f"id={task_id} failed response={data}")
                raise Exception(f"task failed: {data}")

            except requests.RequestException as e:
                STATS["error"] += 1
                log.warning(f"id={task_id} poll_error={e}")
                time.sleep(2)