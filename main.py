"""FastAPI application and executable Discord bot entry point."""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.router import api_router
from app.bot.bot import DiscordBotApplication
from app.config.logging import configure_logging
from app.config.settings import BotConfig
from app.core.error_handlers import register_exception_handlers
from app.core.middleware import RequestIdMiddleware, RequestLoggingMiddleware
from app.services.discord_service import DiscordService
from app.services.webhook_service import NotificationCoordinator
from database.database import create_database_engine
from database.session import create_session_factory


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Configure logging and own the optional Discord Bot task."""
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    logger = logging.getLogger(__name__)
    logger.info("CollabNotify API started.")
    database_url = os.getenv("DATABASE_URL", "sqlite:///database/collabnotify.db")
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    application.state.notification_coordinator = None
    bot_task: asyncio.Task[None] | None = None
    if os.getenv("ENABLE_DISCORD_BOT", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        bot_config = BotConfig.from_env()
        bot_application = DiscordBotApplication(
            bot_config, session_factory=session_factory
        )
        application.state.notification_coordinator = NotificationCoordinator(
            session_factory,
            DiscordService(bot_application.client.channel_service),
        )
        bot_task = asyncio.create_task(
            bot_application.run(), name="collabnotify-discord-bot"
        )

        def _log_bot_completion(task: asyncio.Task[None]) -> None:
            if task.cancelled():
                return
            exception = task.exception()
            if exception is not None:
                logger.error(
                    "Discord Bot task stopped unexpectedly.",
                    exc_info=(type(exception), exception, exception.__traceback__),
                )

        bot_task.add_done_callback(_log_bot_completion)
        ready_task = asyncio.create_task(
            bot_application.client.wait_until_ready(),
            name="collabnotify-discord-ready",
        )
        done, _pending = await asyncio.wait(
            {bot_task, ready_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if bot_task in done:
            ready_task.cancel()
            with suppress(asyncio.CancelledError):
                await ready_task
            await bot_task
        else:
            await ready_task
        logger.info("Discord client is ready.")
    try:
        yield
    finally:
        if bot_task is not None:
            bot_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await bot_task
        engine.dispose()
        logger.info("CollabNotify API stopped.")


def create_app() -> FastAPI:
    """Create and configure the CollabNotify FastAPI application."""
    application = FastAPI(
        title="CollabNotify API",
        description="Webhook notification service for Discord.",
        version="0.1.0",
        lifespan=application_lifespan,
    )
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.include_router(api_router)
    register_exception_handlers(application)
    return application


app = create_app()


async def run_bot() -> None:
    """Load configuration and run the Discord bot until shutdown."""
    config = BotConfig.from_env()
    configure_logging(config.log_level)
    database_url = os.getenv("DATABASE_URL", "sqlite:///database/collabnotify.db")
    engine = create_database_engine(database_url)
    try:
        application = DiscordBotApplication(
            config,
            session_factory=create_session_factory(engine),
        )
        await application.run()
    finally:
        engine.dispose()


def main() -> None:
    """Run the bot and handle an interactive Ctrl+C shutdown."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutdown requested by user.")


if __name__ == "__main__":
    main()
