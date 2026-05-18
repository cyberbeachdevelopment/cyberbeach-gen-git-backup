# huzaif.online

import requests
import time

from utils.core import *
log = setup_logger(__name__)


class HuzaifClient:
    def __init__(self, api_key, api_url="https://huzaif.online", timeout=120, poll_interval=2):
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.site_key = "a9b5fb07-92ff-493f-86fe-352a2803b3df"
        self.site_url = "https://discord.com/register"  # test

        log.debug(f"client initialized base_url={self.api_url}")

    def create_task(self, proxy, rqdata, useragent):
        log.debug(
            f"creating task site={self.site_url} "
            f"proxy={'yes' if proxy else 'no'} "
            f"rqdata={'yes' if rqdata else 'no'} "
            f"ua={'yes' if useragent else 'no'}"
        )

        try:
            resp = requests.post(
                f"{self.api_url}/createtask",
                json={
                    "clientKey": self.api_key,
                    "task": {
                        "site_url": self.site_url,
                        "site_key": self.site_key,
                        "proxy": proxy,
                        "rqdata": rqdata,
                        "ua": useragent
                    }
                }
            )
            resp.raise_for_status()

            task_id = resp.json().get("taskId")

            if not task_id:
                log.error("create failed missing_task_id")
                return None

            log.debug(f"task created id={task_id}")
            return task_id

        except Exception as e:
            STATS["error"] += 1
            log.error(f"create error={e}")
            return None

    def get_result(self, task_id):
        try:
            resp = requests.post(
                f"{self.api_url}/gettaskresult",
                json={
                    "clientKey": self.api_key,
                    "taskId": task_id,
                }
            )
            resp.raise_for_status()

            result = resp.json()
            status = result.get("status")

            log.debug(f"id={task_id} status={status}")

            return result

        except Exception as e:
            STATS["error"] += 1
            log.warning(f"id={task_id} poll_error={e}")
            return None

    def solve_captcha(
        self,
        rqdata: str,
        user_agent: str,
        proxy: str | None = None,
    ):
        log.debug("solve start")

        task_id = self.create_task(proxy, rqdata, user_agent)

        if not task_id:
            log.warning("solve aborted no_task_id")
            return None

        start_time = time.time()

        while True:
            elapsed = time.time() - start_time

            if elapsed > self.timeout:
                log.warning(f"id={task_id} timeout={elapsed:.2f}s")
                return None

            result = self.get_result(task_id)

            if not result:
                log.warning(f"id={task_id} empty_result")
                return None

            status = result.get("status")

            if status == "success":
                token = result.get("uuid")
                log.debug(f"task solved id={task_id}")
                return token

            if status == "error":
                log.error(f"id={task_id} failed")
                return None

            log.debug(f"id={task_id} processing sleep={self.poll_interval}s")
            time.sleep(self.poll_interval)