from typing import Optional
import requests
import pytest
import ray


# Settings
class Config():
    CCU_TEST:int = 50
    MIN_TEXT_LENGHT:int = 6
    MAX_TEXT_LENGHT:int = 20

    # Bot info
    BOT_ID="68830071"
    MESSENGER_USER_ID="5926713157417067"

# Request Modules
class RequestSession():
    sgton_instance=None
    def __init__(self,
                 retries: int = 3,
                 back_off_factor: float = 0.3,
                 status_force_list: tuple = (500, 502, 504),
                 session: Optional[requests.Session] = None,
                 ) -> None:
        self.init(retries,back_off_factor,status_force_list,session)

    def init(self,
             retries: int = 3,
             back_off_factor: float = 0.3,
             status_force_list: tuple = (500, 502, 504),
             session: Optional[requests.Session] = None,
             ) -> requests.Session:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util import Retry
        """
        :param retries: total retries
        :param back_off_factor: A back-off factor to apply between attempts after the second try
        :param status_force_list: list of error status
        :param session: modified session
        :return: A Requests session
        """
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=back_off_factor,
            status_forcelist=status_force_list,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # TODO: Set singleton
        self.sgton_instance=session
        return self.sgton_instance

    def get_instance(self,
                     retries: int = 3,
                     back_off_factor: float = 0.3,
                     status_force_list: tuple = (500, 502, 504),
                     session: Optional[requests.Session] = None) -> requests.Session:
        return self.sgton_instance if self.sgton_instance else self.init(retries,back_off_factor,status_force_list,session)


# TODO: Init stage
config = Config()
rq_session = RequestSession()
task_ids = []

# Func
def random_text()->str:
    import random
    import string
    random_length = random.randint(config.MIN_TEXT_LENGHT,config.MAX_TEXT_LENGHT)
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random_length))


def test_post_tasks()->None:
    try:
        ray.init() #type:ignore
        def random_body()->dict:
            return {
                "text_input": random_text(),
                "bot_id": config.BOT_ID,
                "messenger_user_id": config.MESSENGER_USER_ID,
                "block_nearly_done": "nearly_done",
                "block_done": "done",
                "message_tag": "NON_PROMOTIONAL_SUBSCRIPTION"
            }

        @ray.remote #type:ignore
        def api_post_tasks()->requests.Response:
            api_url = "https://ahachat-bot.halocom.io/api/v1/tasks"
            return rq_session.get_instance().post(url=api_url,json=random_body())

        tasks = []
        for _ in range(config.CCU_TEST):
            tasks.append(api_post_tasks.remote())
        results = ray.get(tasks) #type:ignore
        for result in results:
            task_ids.append(result.json()["task_id"])
            assert result.status_code == 200
    finally:
        ray.shutdown() #type:ignore


def test_get_task_results()->None:
    try:
        ray.init() #type:ignore
        @ray.remote #type:ignore
        def api_get_task_result(task_id:str)->requests.Response:
            api_url = f"https://ahachat-bot.halocom.io/api/v1/tasks/result/{task_id}"
            return rq_session.get_instance().get(url=api_url)

        tasks = []
        for task_id in task_ids:
            tasks.append(api_get_task_result.remote(task_id))
        results = ray.get(tasks) #type:ignore
        for result in results:
            assert result.status_code == 200
    finally:
        ray.shutdown() #type:ignore

