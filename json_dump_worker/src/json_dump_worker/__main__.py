"""Entry point for JSON dump worker."""

from json_dump_worker.worker import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
