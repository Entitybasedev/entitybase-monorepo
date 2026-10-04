"""Entry point for backlink statistics worker."""

from backlink_statistics_worker.worker import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
