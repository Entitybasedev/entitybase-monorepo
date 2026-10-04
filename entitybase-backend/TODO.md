# TODO

- [ ] Add monitoring and metrics for worker health and range utilization
- [ ] Fix todos in the codebase
- [ ] Report terms per language in the stats service
  - `GeneralStatsService.get_terms_per_language()`
    (`src/models/rest_api/entitybase/v1/services/general_stats_service.py`) returns
    an empty map: it queries `labels`, `descriptions` and `aliases` tables that do
    not exist, so every query raises and is swallowed. The statistics page shows
    no terms per language.
  - Language is not a column anywhere. Terms are keyed by the hash of the term text
    in `entity_terms` (no language), and `metadata_content` stores the raw string
    with no language either. The only place a language appears is
    `entity_revision_data.data` -> `revision.hashes.{labels,descriptions,aliases}`,
    which is a JSON object keyed by language code.
  - Why not SQL: unnesting those JSON objects needs `JSON_TABLE`, which exists in
    MySQL 8 and MariaDB 10.6+ only. The project also runs on SQLite and Vitess
    (`DB_TYPE` in settings), so a `JSON_TABLE` query would work in CI and fail
    elsewhere.
  - Why not Python in the request path: it means scanning a revision row per
    entity. That is a job for the daily stats worker, not for `GET /v1/stats`,
    which must stay cheap.
  - Suggested shape: aggregate in `general_stats_worker` once a day, persist per
    language counts (the `general_daily_stats` table already exists), and have the
    live endpoint read the stored counts instead of scanning.
  - Must count head revisions only. `entity_revision_data` holds every historical
    revision, so counting all rows would inflate the numbers as entities are edited.
  - Tests: assert the SQL names tables that exist (the same guard as
    `TestStatsQueryTables` in
    `tests/unit/models/rest_api/entitybase/v1/services/test_general_stats_service.py`),
    so a phantom table cannot come back unnoticed. Those tests exist because this
    class of bug shipped silently: every earlier test mocked the cursor and never
    checked the query.
- [ ] Emit statements in the RDF/Turtle export
  - `GET /v1/entities/{id}.ttl` returns the labels and descriptions of an entity
    but none of its statements, so an item with facts exports as an almost empty
    graph.
  - Cause: revisions store statements hash-referenced under `hashes.statements`
    (e.g. `[4115458737514604876]`), and the RDF converter
    (`models.rdf_builder.converter.EntityConverter`) only reads claims that are
    inline in the revision. It is handed hash references and finds nothing.
  - Verified: serialising a real revision that has a statement produces
    `wd:Q... a wikibase:Item` and the CC0 dataset triples, and no statement triple.
  - Options, cheapest first: resolve the statement hashes before conversion, or
    teach the converter to read `hashes.statements` and fetch each statement and
    snak by hash. The statement and snak fetch endpoints already exist
    (`GET /v1/statements/{hash}`, `GET /v1/resolve/snaks/{hash}`).
  - Related: `GET /v1/entities/{id}.json` has the same shape, so any consumer that
    expects inline statements is affected, not just RDF.
  - Tests: a round-trip test that creates an item with a statement, exports turtle
    and asserts the predicate for that statement is present.