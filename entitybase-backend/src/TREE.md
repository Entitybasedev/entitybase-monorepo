# Tree
```
src/
└── models
    ├── config
    ├── data
    │   ├── config
    │   ├── infrastructure
    │   │   ├── db
    │   │   │   └── records
    │   │   ├── elasticsearch
    │   │   ├── meilisearch
    │   │   ├── s3
    │   │   │   └── hashes
    │   │   ├── stream
    │   │   └── vitess
    │   │       └── records
    │   ├── rest_api
    │   │   └── v1
    │   │       └── entitybase
    │   │           ├── request
    │   │           │   └── entity
    │   │           └── response
    │   │               └── entity
    │   └── workers
    ├── infrastructure
    │   ├── db
    │   │   ├── repositories
    │   │   └── storage
    │   ├── s3
    │   │   ├── revision
    │   │   └── storage
    │   ├── sqlite
    │   │   └── repositories
    │   ├── stream
    │   └── vitess
    │       ├── repositories
    │       └── storage
    ├── internal_representation
    │   └── values
    ├── json_parser
    │   └── values
    ├── rdf_builder
    │   ├── hashing
    │   ├── models
    │   ├── ontology
    │   ├── property_registry
    │   └── writers
    ├── rest_api
    │   └── entitybase
    │       └── v1
    │           ├── endpoints
    │           ├── handlers
    │           │   └── entity
    │           │       ├── lexeme
    │           │       └── property
    │           ├── routes
    │           ├── services
    │           └── utils
    ├── services
    │   ├── elasticsearch
    │   └── meilisearch
    ├── utils
    ├── validation
    └── workers
        └── dev

64 directories
```
