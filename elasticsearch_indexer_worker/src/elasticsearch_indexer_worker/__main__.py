"""Entry point for the Elasticsearch indexer worker."""

import asyncio

from elasticsearch_indexer_worker.worker import main

if __name__ == "__main__":
    asyncio.run(main())
