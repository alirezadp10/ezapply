from loguru import logger

from bot.agents import NormalizerAgent
from bot.enums import ModesEnum
from bot.logger_manager import setup_logger


def main():
    setup_logger()

    logger.info(f"🚀 Running SeleniumBot in mode: {ModesEnum.FETCH_QUESTIONS}")

    NormalizerAgent.ask("foo", "bar")


if __name__ == "__main__":
    main()
