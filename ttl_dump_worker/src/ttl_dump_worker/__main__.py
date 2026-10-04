"""Entry point for TTL dump worker."""

from ttl_dump_worker.worker import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
