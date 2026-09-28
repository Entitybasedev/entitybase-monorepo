export const HOST = import.meta.env.VITE_HOST || 'localhost'

export const infrastructure = [
  { name: 'MinIO', url: `http://${HOST}:9001`, description: 'S3 storage + console', healthPath: '/minio/health/live', linkUrl: `http://${HOST}:9001` },
  { name: 'MySQL', url: `http://${HOST}:3307`, description: 'Database (no HTTP interface)', healthPath: '/' },
  { name: 'Redpanda', url: `http://${HOST}:9645`, description: 'Kafka messaging + console', healthPath: '/', linkUrl: `http://${HOST}:8084` },
  { name: 'Entitybase API', url: `http://${HOST}:8083`, description: 'Main API server', healthPath: '/health' },
  { name: 'Valkey', url: `http://${HOST}:6378`, description: 'Redis-compatible caching', healthPath: '/' },
  { name: 'Elasticsearch', url: `http://${HOST}:9201`, description: 'Search engine', healthPath: '/', configKey: 'elasticsearch_enabled' },
  { name: 'Meilisearch', url: `http://${HOST}:7700`, description: 'Full-text search', healthPath: '/', linkUrl: `http://${HOST}:7700`, configKey: 'meilisearch_enabled' },
]

export const eventStreaming = [
  { name: 'Server-Sent Events Backend', url: `http://${HOST}:8888`, description: 'Streaming backend SSE API', healthPath: '/health', linkUrl: `http://${HOST}:8889` },
  { name: 'Server-Sent Events Frontend', url: `http://${HOST}:8889`, description: 'Frontend for all topics and events', healthPath: '/health', linkUrl: `http://${HOST}:8889` },
  { name: 'Entity Change Producer', url: `http://${HOST}:8083`, healthPath: '/health', producerKey: 'entity_change', topic: 'entity_change', description: 'Topic with all changes to entities', linkUrl: `http://${HOST}:8889` },
  { name: 'Incremental RDF Producer', url: `http://${HOST}:8083`, healthPath: '/health', producerKey: 'incremental_rdf', topic: 'incremental_rdf_diff', description: 'Topic with RDF diff of all changes to entities', linkUrl: `http://${HOST}:8889` },
//  { name: 'User Change Producer', url: `http://${HOST}:8083`, healthPath: '/health', producerKey: 'user_change', topic: 'user_change' },
]

export const workers = [
  { name: 'ID Worker', url: `http://${HOST}:8001`, healthPath: '/health', linkUrl: `http://${HOST}:8001/health`, configKey: 'id_worker_enabled' },
  { name: 'JSON Dump Worker', url: `http://${HOST}:8002`, healthPath: '/health', linkUrl: `http://${HOST}:8002/health`, configKey: 'json_worker_enabled' },
  { name: 'TTL Dump Worker', url: `http://${HOST}:8003`, healthPath: '/health', linkUrl: `http://${HOST}:8003/health`, configKey: 'ttl_worker_enabled' },
  { name: 'Backlink Stats Worker', url: `http://${HOST}:8004`, healthPath: '/health', linkUrl: `http://${HOST}:8004/health`, configKey: 'backlink_stats_worker_enabled' },
  { name: 'General Stats Worker', url: `http://${HOST}:8005`, healthPath: '/health', linkUrl: `http://${HOST}:8005/health`, configKey: 'general_stats_worker_enabled' },
  { name: 'User Stats Worker', url: `http://${HOST}:8006`, healthPath: '/health', linkUrl: `http://${HOST}:8006/health`, configKey: 'user_stats_worker_enabled' },
  { name: 'Elasticsearch Indexer Worker', url: `http://${HOST}:8007`, healthPath: '/health', linkUrl: `http://${HOST}:8007/health`, configKey: 'elasticsearch_enabled' },
  { name: 'Meilisearch Indexer Worker', url: `http://${HOST}:8009`, healthPath: '/health', linkUrl: `http://${HOST}:8009/health`, configKey: 'meilisearch_enabled' },
  { name: 'Purge Worker', url: `http://${HOST}:8008`, healthPath: '/health', linkUrl: `http://${HOST}:8008/health`, configKey: 'purge_worker_enabled' },
]

export const producers = eventStreaming.filter(item => item.producerKey)
export const streamingServices = eventStreaming.filter(item => !item.producerKey)