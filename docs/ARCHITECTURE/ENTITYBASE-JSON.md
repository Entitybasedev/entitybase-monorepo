# Entitybase JSON

> **Status:** `.njson` is implemented and specified here. Parts marked
> *Open* are deliberately undecided; they are listed so they are not mistaken
> for settled design.

There are three JSON shapes in this system, and confusing them is the main
source of surprise when reading the API. This document says which is which,
and specifies the one that is ours.

| Shape | Where | What it is |
| --- | --- | --- |
| **Wikibase JSON** | `POST /v1/import`, JSONL dump importer | **Input only.** An interchange format we parse on the way in. |
| **Revision JSON** | `GET /v1/entities/{id}.json` | The stored revision, with content hashes. Storage-shaped. |
| **Normalized Entitybase JSON** | `GET /v1/entities/{id}.njson` | The revision with hashes resolved. Readable. Specified below. |

## Wikibase JSON is an import format, not an output format

**We accept Wikibase JSON. We do not produce it.**

Wikibase JSON is parsed on the way in — by `POST /v1/import` and by the JSONL
dump importer — because that is how existing Wikidata data arrives, and
re-deriving it from our own model would be wasted work for no consumer.

Nowhere else does Wikibase JSON appear:

- No endpoint returns it.
- `.json` does **not** return it. `.json` returns our revision, hashes and all.
- `.ttl` is RDF, not Wikibase JSON.
- The search indexes are not Wikibase JSON.

This is a deliberate position, consistent with
[the internal representation design](PARSER/INTERNAL-REPRESENTATION.md), which
states *"Do not mirror Wikibase JSON"* — we normalise it into our own
representation on import and then stop thinking in its terms.

The consequence worth being blunt about: **do not expect `.njson` to be
drop-in compatible with a Wikibase client.** It has no `pageid`, no `ns`, no
`title`, no `lastrevid`, no `claims` grouping by property, no `mainsnak`
wrapper of our own, and no `modified` timestamp. Field names overlap where the
concepts genuinely coincide (`labels`, `descriptions`, `aliases`, `sitelinks`,
`datatype`, `rank`, `datavalue`) and diverge where they do not.

If you need Wikibase JSON specifically, convert it yourself from `.njson`.
We are not going to keep a serializer alive for a format we only read.

## Why a separate endpoint rather than changing `.json`

`.json` is the revision as stored. Clients that reason about revisions,
deduplication or diffing need it exactly as-is. Overwriting it with a
denormalized view would break them, and it would couple the storage model to
every reader.

So `.njson` is additive: same entity, same revision, hashes resolved.

```
GET /v1/entities/Q42.json     →  {"hashes": {"labels": {"en": 9274834750876690022}, ...}}
GET /v1/entities/Q42.njson    →  {"labels": {"en": {"language": "en", "value": "Douglas Adams"}}, ...}
```

## The normalized document

Top level. Every key below is always present.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | `Q42` / `P31` / `L7`. |
| `entity_type` | string | `item`, `property` or `lexeme`. |
| `revision_id` | integer | The revision this document describes. |
| `labels` | object | Language → term. Always present, `{}` when empty. |
| `descriptions` | object | Language → term. Always present, `{}` when empty. |
| `aliases` | object | Language → list of terms. Always present, `{}` when empty. |
| `sitelinks` | object | Site → sitelink. Always present, `{}` when empty. |
| `statements` | array | Always present, `[]` when empty. |
| `properties` | array | Property IDs used, in no guaranteed order. |
| `property_counts` | object \| null | Property ID → statement count. |
| `datatype` | string | Properties only; `""` otherwise. |
| `state` | object | Lock / deletion / protection flags. |
| `edit` | object | Who, when, and the edit summary of this revision. |
| `created_at` | string | ISO 8601. |
| `schema_version` | string | Revision schema version. |
| `redirects_to` | string | `""` when not a redirect. |
| `lemmas` | object | Lexemes only, `{}` otherwise. |
| `forms` | array | Lexemes only, `[]` otherwise. |
| `senses` | array | Lexemes only, `[]` otherwise. |
| `language` | string | Lexeme language QID, `""` otherwise. |
| `lexical_category` | string | Lexeme category QID, `""` otherwise. |

### Terms

Labels, descriptions and aliases are keyed by language. Each term is an object
carrying its own language, so a term stays self-describing when it is read on
its own:

```json
"labels":      { "en": { "language": "en", "value": "Douglas Adams" } },
"descriptions":{ "en": { "language": "en", "value": "English author" } },
"aliases":      { "en": [ { "language": "en", "value": "Douglas Noel Adams" },
                            { "language": "en", "value": "DNA" } ] }
```

Repeating `language` inside the term is redundant against the key it sits
under. It is kept deliberately: the same term objects appear elsewhere without
their key, and a term that has to be looked up to be understood is worse than
one that repeats a two-letter code.

### Sitelinks

```json
"sitelinks": {
  "enwiki": { "site": "enwiki", "title": "Douglas Adams", "badges": ["featuredarticle"] }
}
```

`badges` is always an array, `[]` when there are none.

### Statements

A statement is returned as the object that is stored for it, verbatim:

```json
"statements": [
  {
    "mainsnak": {
      "snaktype": "value",
      "property": "P31",
      "datatype": "wikibase-item",
      "datavalue": { "value": { "id": "Q5" }, "type": "wikibase-item" }
    },
    "type": "statement",
    "rank": "normal",
    "qualifiers": {},
    "references": []
  }
]
```

Statements are the one place where `.njson` inherits Wikibase vocabulary
(`mainsnak`, `datavalue`, `rank`, `snaktype`), and that is not an accident: a
statement is stored as a self-contained object of this shape, so it is already
what it is. Note that `mainsnak`, `qualifiers` and `references` are as stored —
they are **not** further normalized, and nothing inside them is hashed.

The list is a flat array in revision order. It is **not** grouped by property
the way Wikibase groups claims. Use `properties` / `property_counts`, or group
client-side.

### What is not in the document

- **`hashes`** — the internal index, dropped. Its presence is the defining
  difference from `.json`, and it must not reappear.
- **Any content hash.** No term, sitelink or statement is referenced by hash.
- **Internal IDs.** Database identifiers, revision content hashes and object
  store keys are all absent.
- **Storage metadata.** Ref counts, table names, schema details.

## Behaviour

**Content type.** `application/json`, same as `.json`.

**Errors.** Status codes match `.json`: `404` for an unknown entity, `400` for
an unusable identifier. A hash that cannot be resolved — the entity cannot be
reconstructed — is a `500`; the response says the entity could not be
normalized and names the kind of content that was missing, never the hash or
any storage detail. The hash itself is logged server-side.

The rule behind that: **a document that looks complete but is not is worse than
an error.** A missing label is not rendered as an empty string.

**Performance.** Resolution costs a fixed number of queries — one per content
type — regardless of how many references the entity has. Hashes repeated within
an entity are fetched once and reused.

## Open

Decisions not yet made. Each needs a real use case before it is settled.

- **Statement grouping.** A flat list is honest but awkward for consumers that
  want claims-by-property. Grouping, or an optional `?group_by=property`, are
  both on the table.
- **Lexeme terms.** `lemmas`, `forms` and `senses` are passed through as
  stored. Whether they get normalized treatment — and whether forms/senses
  should reference resolved glosses — is undecided.
- **Sitelink URLs.** `wikibase.py` already defines a `SitelinkValue` with a
  `url` field, unused today. Whether `.njson` should emit a computed URL is
  undecided.
- **Revisions.** `/revision/{id}/njson` does not exist. It probably should,
  and it is cheap given the normalizer takes a revision.
- **Sorting.** Terms follow the revision's map order, statements follow
  revision order. Neither is specified as meaningful; a future sort must not be
  mistaken for a change in meaning.
- **Stability.** This document describes intent, not a frozen contract. It will
  change as the model does. Nothing should depend on field order.

## Where the code is

| Concern | Location |
| --- | --- |
| Endpoint | `models/rest_api/entitybase/v1/endpoints/entities.py` |
| Normalization | `models/rest_api/entitybase/v1/services/normalization.py` |
| Batch loaders | `models/infrastructure/db/storage/metadata_storage.py`, `s3/client.py` |
| Tests | `tests/unit/.../test_normalization.py`, `tests/integration/.../test_entity_normalized_json.py`, `e2e-ui/tests/normalized-json.spec.js` |