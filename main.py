import argparse
from loguru import logger

from bot.core import SeleniumBot
from bot.logger_manager import setup_logger
from bot.config import settings
from bot.driver_manager import DriverManager
from bot.enums.modes_enum import ModesEnum


def main():
    setup_logger()

    parser = argparse.ArgumentParser(description="🤖 LinkedIn Auto Applier Bot")
    parser.add_argument(
        "--mode",
        type=lambda s: s.lower(),
        choices=[m.value for m in ModesEnum],
        default=ModesEnum.EXPLORE.value,
        help=f"Bot run mode. Options: {', '.join(m.value for m in ModesEnum)}",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default="",
        help="Comma-separated job IDs (used in test mode)",
    )

    args = parser.parse_args()

    mode = ModesEnum(args.mode)

    bot = SeleniumBot(name="JobApplierBot", db_url=settings.SQLITE_DB_PATH)

    try:
        bot.run(mode=mode.value, job_ids=args.ids)
    except Exception as e:
        logger.exception(f"❌ Error while running bot: {e}")
    finally:
        if bot.driver:
            DriverManager.close_driver(bot.driver)
        logger.info("🏁 Bot finished execution.")


if __name__ == "__main__":
    main()
