"""Entry point for user statistics worker."""

from user_stats_worker.worker import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
