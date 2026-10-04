# Workers Overview

## Backlink Statistics Worker

**Class**: `BacklinkStatisticsWorker`
**Location**: `backlink_statistics_worker/src/backlink_statistics_worker/worker.py`
**Purpose**: 

**Configuration**:
- `backlink_stats_enabled`: False
- `backlink_stats_schedule`: "0 2 * * *"  # Daily at 2 AM
- `backlink_stats_top_limit`: 100

**Health Checks**: Available via worker health endpoint

## Elasticsearch Indexer Worker

**Class**: `ElasticsearchIndexerWorker`
**Location**: `elasticsearch_indexer_worker/src/elasticsearch_indexer_worker/worker.py`
**Purpose**: Worker that consumes entity change events and indexes them to Elasticsearch. This worker: 1. Consumes entity change events from entitybase.entity_change Kafka topic 2. Fetches entity snapshots from S3 for the new revision 3. Transforms entity data to Elasticsearch format 4. Indexes the document to OpenSearch

**Health Checks**: Available via worker health endpoint

## Entity Diff Worker

**Class**: `EntityDiffWorker`
**Location**: `entity_diff_worker/src/entity_diff_worker/worker.py`
**Purpose**: Worker for computing entity diffs.

**Health Checks**: Available via worker health endpoint

## General Stats Worker

**Class**: `GeneralStatsWorker`
**Location**: `general_stats_worker/src/general_stats_worker/worker.py`
**Purpose**: 

**Health Checks**: Available via worker health endpoint

## Incremental Rdf Worker

**Class**: `IncrementalRDFWorker`
**Location**: `incremental_rdf_worker/src/incremental_rdf_worker/worker.py`
**Purpose**: Worker that consumes entity change events and generates incremental RDF diffs. This worker: 1. Consumes entity change events from entitybase.entity_change Kafka topic 2. Looks up revision metadata in MySQL to get content hashes 3. Fetches entity snapshots from S3 for both old and new revisions 4. Computes RDF diffs using IncrementalRDFUpdater 5. Publishes RDF change events to incremental_rdf_diff Kafka topic

**Health Checks**: Available via worker health endpoint

## Json Dump Worker

**Class**: `JsonDumpWorker`
**Location**: `json_dump_worker/src/json_dump_worker/worker.py`
**Purpose**: 

**Health Checks**: Available via worker health endpoint

## Notification Cleanup Worker

**Class**: `NotificationCleanupWorker`
**Location**: `notification_cleanup_worker/src/notification_cleanup_worker/worker.py`
**Purpose**: Worker that periodically cleans up old notifications to enforce limits.

**Health Checks**: Available via worker health endpoint

## Ttl Dump Worker

**Class**: `TtlDumpWorker`
**Location**: `ttl_dump_worker/src/ttl_dump_worker/worker.py`
**Purpose**: 

**Health Checks**: Available via worker health endpoint

## User Stats Worker

**Class**: `UserStatsWorker`
**Location**: `user_stats_worker/src/user_stats_worker/worker.py`
**Purpose**: 

**Health Checks**: Available via worker health endpoint

## Watchlist Consumer Worker

**Class**: `WatchlistConsumerWorker`
**Location**: `watchlist_consumer_worker/src/watchlist_consumer_worker/worker.py`
**Purpose**: Worker that consumes entity change events and creates notifications for watchers.

**Configuration**:
- `kafka_bootstrap_servers`: Comma-separated list of Kafka broker addresses
- `kafka_topic`: Kafka topic for entity changes (default: "wikibase-entity-changes")

**Health Checks**: Available via worker health endpoint

**Dependencies**: Requires aiokafka for Kafka consumption.

