from bot.logger_manager import setup_logger
from bot.selenium_bot import SeleniumBot
from bot.config import settings
from bot.driver_manager import DriverManager

def main():
    logger = setup_logger()
    logger.info("🚀 Bot is starting...")

    bot = SeleniumBot(name="JobApplierBot", db_url=settings.SQLITE_DB_PATH)

    try:
        bot.run()
    except Exception as e:
        logger.exception(f"❌ Error while running bot: {e}")
    finally:
        if bot.driver:
            DriverManager.close_driver(bot.driver)
        logger.info("🚀 Bot finished execution.")

if __name__ == "__main__":
    main()
