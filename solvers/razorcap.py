# razorcap.cc

import requests, time  # , certifi

from utils.core import *
log = setup_logger(__name__)


class RazorCapClient:
    """clean wrapper for razorcap api"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.razorcap.cc"
        self.site_key = "a9b5fb07-92ff-493f-86fe-352a2803b3df"
        self.site_url = "discord.com"

        log.debug(f"client initialized base_url={self.base_url}")
    
    def solve_captcha(
        self,
        rqdata: str,
        user_agent: str,
        proxy: str | None = None,
    ):
        """solve hcaptcha"""

        log.debug("solve start")

        payload = {
            'key': self.api_key,
            'type': 'hcaptcha',
            'data': {
                'sitekey': self.site_key,
                'siteurl': self.site_url,
                'proxy': proxy,
                'rqdata': rqdata
            }
        }

        try:
            log.debug(
                f"creating task site={self.site_url} "
                f"proxy={'yes' if proxy else 'no'} "
                f"rqdata={'yes' if rqdata else 'no'}"
            )

            response = requests.post(
                f'{self.base_url}/tasks/create_task',
                json=payload,
                # verify=certifi.where()
            )
            response.raise_for_status()

            task_id = response.json().get("task_id")

            if not task_id:
                log.warning(f"create failed missing_task_id")
                raise Exception("missing task_id")

            log.debug(f"task created id={task_id}")

        except requests.RequestException as e:
            STATS["error"] += 1
            log.error(f"create error={e}")
            raise

        while True:
            try:
                result = requests.get(
                    f'{self.base_url}/tasks/get_result/{task_id}',
                    # verify=certifi.where()
                )
                result.raise_for_status()
                data = result.json()

                status = data.get("status")

                log.debug(f"id={task_id} status={status}")

                if status == "success":
                    log.debug(f"task solved id={task_id}")
                    return data.get('response_key')

                if status == "pending":
                    time.sleep(1)
                    continue

                log.error(f"id={task_id} failed response={data}")
                raise Exception(f"task failed: {data}")

            except requests.RequestException as e:
                STATS["error"] += 1
                log.warning(f"id={task_id} poll_error={e}")
                time.sleep(2)
