# Entitybase plugin for DokuWiki

Refer to Entitybase items from a wiki page. Small on purpose: one syntax
component, one API call, no database knowledge in the plugin.

## Syntax

```
{{entity>Q42}}        the label in the wiki interface language
{{entity>Q42|de}}     the label in a chosen language
```

`Q42` renders as **Douglas Adams** (or the label in German with `|de`), linked
to the item. When the item has no label in that language, the id itself is
shown and marked with `entitybase-missing`, so a page still reads sensibly and
the problem is visible rather than silent.

## Install

Copy the `entitybase` directory into your wiki's plugin directory, or point the
plugin manager at this repository:

```bash
git clone <this repo> src
cp -r src/plugin-dokuwiki/entitybase /path/to/dokuwiki/lib/plugins/
```

Then set the API location in **Admin → Configuration Settings → Entitybase
Plugin**:

| Setting | Meaning | Default |
|---|---|---|
| `api` | Entitybase API base URL | `http://localhost:8083` |
| `entity_url` | Where an item's page lives; empty renders plain text | *(empty)* |
| `fallback_lang` | Language to try when the interface language has no label | `en` |
| `cache_ttl` | Seconds a cached label stays fresh; `0` uses the wiki's `cachetime` | `0` |
| `timeout` | Seconds before an API request is given up on | `5` |

## How it resolves a label

1. The language you asked for, if any.
2. The wiki interface language (`$conf['lang']`).
3. `fallback_lang`.

The first hit wins. Every lookup is cached in the wiki's cache directory
(`getCacheName`), keyed by entity and language, so a page mentioning the same
item many times costs one request. A missing label is cached too — otherwise
every render would ask again.

The plugin only calls the public API and understands nothing about the
database behind it:

```
GET {api}/v1/entities/{id}/labels/{lang}   ->  200 {"value": "..."}  |  404
```

Anything other than a 200, or an unparseable body, is treated as "no label".
The API being down therefore degrades to showing ids, never to a broken page.

## Layout

```
plugin-dokuwiki/
├── README.md
├── entitybase/
│   ├── client.php        HTTP + JSON, no DokuWiki dependencies
│   ├── helper.php        language resolution and caching
│   ├── syntax.php        the {{entity>}} component
│   ├── plugin.info.txt
│   ├── conf/default.php  defaults, read automatically by getConf()
│   ├── conf/metadata.php admin form fields
│   └── lang/en/lang.php
└── tests/run.php
```

`client.php` deliberately knows nothing about DokuWiki and takes its HTTP
transport as an argument, which is what makes the tests possible.

## Verified against a real wiki

With the stack running, a page containing

```
A plain item: {{entity>Q1}}
Forced language: {{entity>Q1|de}}
Missing item: {{entity>Q999999}}
```

renders as

```html
<a href="..." class="entitybase-item" ...>Demo item</a>          <!-- en label -->
<a href="..." class="entitybase-item" ...>Demo item</a>          <!-- |de fell back to en -->
<a href="..." class="entitybase-item entitybase-missing" ...>Q999999</a>
```

Note for anyone extending this: helpers in this DokuWiki release extend
`dokuwiki\Extension\Plugin`. There is no `HelperPlugin` base class, and a
helper that fails to load is only visible as a null from `loadHelper()` deep in
`render()` — check `data/log/error/` when output looks unstyled.

## Run it with the stack

The wiki is part of the compose stack, with the plugin mounted in:

```bash
docker compose up -d dokuwiki
# http://localhost:8082
```

`plugin-dokuwiki/dokuwiki/local.php` is mounted over the wiki's generated
`conf/local.php` and points the plugin at `http://entitybase-api:8080` — the
API by service name on the compose network — and links items to
`http://localhost:8080/entity`. That is what makes it work with no install
step; a real deployment should set the same values in the admin settings
instead and drop the mount. The dashboard links to the wiki.

## Tests

```bash
php plugin-dokuwiki/tests/run.php
```

No PHPUnit, no network: the transport is faked, so this needs nothing but a
PHP binary. It covers the label found, missing label, missing entity, empty
value, unparseable body, a transport that gives up, URL encoding, a trailing
slash on the base URL, and that a non-200 is never mistaken for a label.

CI runs the same file inside `dokuwiki/dokuwiki:stable`, so the tests execute
on a real PHP with cURL rather than whatever a machine happens to have:

```bash
docker run --rm -v "$PWD/plugin-dokuwiki:/plugin:ro" dokuwiki/dokuwiki:stable \
  php /plugin/tests/run.php
```

## Possible next steps

Each is a small addition to what is here, in rough order of value:

- `{{entitylist>Q42|property=P31}}` — the items an item points at.
- `{{property>Q42|P31}}` — one property of an item.
- Batch the label lookups per page, so a page with 30 items is one request
  instead of 30. The API already has `GET /v1/resolve/labels/{hashes}`.
- Editor autocomplete for `{{entity>}}` via the search endpoint.