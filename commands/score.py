from loguru import logger

from bot.db_manager import DBManager
from bot.enums import ModesEnum
from bot.logger_manager import setup_logger


def main():
    setup_logger()
    logger.info(f"🚀 Running SeleniumBot in mode: {ModesEnum.SCORE}")
    db = DBManager()


if __name__ == "__main__":
    main()
