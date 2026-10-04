"""Entry point for general statistics worker."""

from general_stats_worker.worker import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
