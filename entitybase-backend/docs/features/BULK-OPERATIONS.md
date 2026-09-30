# Bulk Operations

> **⚠️ Status note (2026-09):** S3/MinIO storage has been removed from the stack. Everything — entities, revisions, statements, qualifiers, references, snaks and metadata — is stored in MySQL. This document is kept for historical context; sections describing S3/MinIO no longer apply.

## Bulk export

Stream snapshots from S3

Parallelized by entity_id

Deterministic ordering possible

No database pressure.
