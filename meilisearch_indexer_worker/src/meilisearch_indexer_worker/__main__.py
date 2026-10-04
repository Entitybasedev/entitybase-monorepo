"""Entry point for the Meilisearch indexer worker."""

import asyncio

from meilisearch_indexer_worker.worker import main

if __name__ == "__main__":
    asyncio.run(main())