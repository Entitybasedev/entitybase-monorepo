# Entity Get Process

> **⚠️ Status note (2026-09):** S3/MinIO storage has been removed from the stack. Everything — entities, revisions, statements, qualifiers, references, snaks and metadata — is stored in MySQL. This document is kept for historical context; sections describing S3/MinIO no longer apply.

```mermaid
flowchart TD
    A[EntityReadHandler.get_entity] --> B[Validate Clients]
    B -->|vitess or s3 not initialized| B1[Return 503]
    B --> C[Validate Entity]
    C -->|entity not found| C1[Return 404]
    C --> D[Get Head Revision]
    D -->|head_revision_id == 0| D1[Return 404]
    D --> E[Read Revision Data]
    E -->|Revision not found| E1[Return 404]
    E -->|Database read failure| E2[Return 500]
    E --> F{Check Deleted}
    F -->|is_deleted == True| F1[Return 404]
    F --> G[Build EntityResponse]
    G --> H[Return EntityResponse]
```

## Error Handling
- Vitess not initialized → 503 Service Unavailable
- Entity not found in Vitess → 404 Not Found
- Head revision 0 → 404 Not Found
- Entity marked as deleted → 404 Not Found
- Revision not found → 404 Not Found
- Database read failure → 500 Internal Server Error
