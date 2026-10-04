"""Elasticsearch indexer worker."""

from elasticsearch_indexer_worker.worker import (
    ElasticsearchIndexerWorker,
    main,
)

__all__ = ["ElasticsearchIndexerWorker", "main"]
