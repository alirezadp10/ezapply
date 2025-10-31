from loguru import logger
from bot.driver_manager import DriverManager
from bot.db_manager import DBManager
from bot.enums import ModesEnum
from bot.linkedin_auth import LinkedInAuth
from bot.job_finder import JobFinder
from bot.job_applicator import JobApplicator
from bot.modes import run_mode


class SeleniumBot:
    def __init__(self, name: str, db_url: str):
        self.name = name
        self.driver = DriverManager.create_driver()
        self.db = DBManager(db_url)
        self.auth = LinkedInAuth(self.driver)
        self.finder = JobFinder(self.driver, self.db)
        self.applicator = JobApplicator(self.driver, self.db)

    def run(self, mode: ModesEnum = ModesEnum.EXPLORE, job_ids: str = "") -> None:
        logger.info(f"🚀 Running SeleniumBot in mode: {mode}")
        self.auth.login_if_needed()
        run_mode(mode, bot=self, job_ids=job_ids)
