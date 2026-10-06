# Entitybase plugin for DokuWiki

Refer to Entitybase items, properties and lexemes from a wiki page. Small on
purpose: one syntax component, a few API calls, no database knowledge in the
plugin.

## Syntax

```
{{entity>Q42}}             an item as its label
{{entity>Q42|de}}          the label in a chosen language

{{lexeme>L1}}              a lexeme as its lemma and language: "demo (English)"
{{lexeme>L1|de}}           the lemma looked up in German first
{{lexeme>L1||lemma}}       only the lemma
{{lexeme>L1||lang}}        only the language

{{property>P1}}            a property as its label and datatype: "instance of (item)"
{{property>P1|de}}         the label in a chosen language
{{property>P1||label}}     only the label
{{property>P1||datatype}}  only the datatype
```

The separator is `>` and the arguments are separated by `|`, as in every other
DokuWiki macro: `{{lexeme>L1}}`, not `{{lexeme|L1}}`.

Three names, one macro: what a reference renders as follows from the id, not
from the name you typed. `{{entity>L1}}` is a lexeme, `{{lexeme>P1}}` is a
property, and both render exactly as `{{lexeme>L1}}` and `{{property>P1}}`
would. The names are there to say what you mean, not to pick a different
lookup.

The arguments are positional, so an argument you want to skip is left empty:

```
{{lexeme>L1||lemma}}   the lemma, in the default language
{{lexeme>L1|de|lemma}} the lemma, in German
```

When an entity has no label, lemma or datatype, the id itself is shown and
marked with `entitybase-missing`, so a page still reads sensibly and the
problem is visible rather than silent. Neither half of a reference is dropped
because the other is missing: a lemma without a language still names a word,
and a language without a lemma is still what the id referred to.

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
| `entity_url` | Where an entity's page lives; empty renders plain text | *(empty)* |
| `cache_ttl` | Seconds a cached label stays fresh; `0` uses the wiki's `cachetime` | `0` |
| `timeout` | Seconds before an API request is given up on | `5` |

Two more settings, `default_lang` and `fallback_chain`, are in
`conf/default.php` and are read from there. They are not in
`conf/metadata.php`, so the configuration manager does not offer them as
fields; set them in `conf/local.php` instead:

```php
$conf['plugin']['entitybase']['default_lang'] = 'sv';
$conf['plugin']['entitybase']['fallback_chain'] = 'sv, en, de';
```

## How it resolves a language

Every lookup walks the same chain and stops at the first hit:

1. The language the page named, as in `{{entity>Q42|de}}`.
2. `default_lang`, if you set one.
3. The wiki interface language (`$conf['lang']`). A wiki set to German reads
   German labels by default, so nothing has to be written down.
4. Each language in `fallback_chain`, in order.

A language is never asked for twice, and `fallback_chain` holds **at most five**
languages — anything after the fifth is ignored. Five is a deliberate ceiling: a
longer chain costs one request per language for every entity on a page whose
label is missing, and the languages nobody labels anything in are the ones worth
cutting.

So with no `default_lang`, a German wiki and `fallback_chain = en, fr`, the
chain for `{{entity>Q42}}` is `de, en, fr`, and for `{{entity>Q42|nl}}` it is
`nl, de, en, fr`.

The chain is what keeps a sparse knowledge base readable. An entity with only an
English label renders as that label in a German wiki instead of a bare id.

Every lookup is cached in the wiki's cache directory (`getCacheName`), keyed by
entity, kind of term and language, so a page mentioning the same item many times
costs one request. A missing label is cached too — otherwise every render would
ask again.

The plugin only calls the public API and understands nothing about the database
behind it:

```
GET {api}/v1/entities/{id}/labels/{lang}            ->  200 {"value": "..."}  |  404
GET {api}/v1/entities/lexemes/{id}/lemmas/{lang}    ->  200 {"value": "..."}  |  404
GET {api}/v1/entities/lexemes/{id}/language         ->  200 {"language": "Q1860"}
GET {api}/v1/entities/{id}                          ->  200 {"data": {"revision": {"datatype": "..."}}}
```

A lexeme's language is a reference to another entity, so showing it costs a
second label lookup: `Q1860` on its own means nothing to a reader, `English`
does. A datatype belongs to the property rather than to a language of it, so it
has no chain and no link — it is not an entity. Its `wikibase-` prefix is
dropped for the same reason: `wikibase-item` and `item` mean the same to anyone
writing in the wiki, and the full value stays in the tooltip.

Anything other than a 200, or an unparseable body, is treated as "no label".
The API being down therefore degrades to showing ids, never to a broken page.

## Layout

```
plugin-dokuwiki/
├── README.md
├── entitybase/
│   ├── client.php        HTTP + JSON, no DokuWiki dependencies
│   ├── helper.php        language resolution and caching
│   ├── syntax.php        the {{entity>}}, {{lexeme>}} and {{property>}} components
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
Missing item: {{entity>Q99999999}}
A lexeme: {{lexeme>L1}}
A property: {{property>P1}}
```

renders as

```html
<a href="..." class="entitybase-item" ...>Demo item</a>          <!-- en label -->
<a href="..." class="entitybase-item" ...>Demo item</a>          <!-- |de fell back -->
<a href="..." class="entitybase-item entitybase-missing" ...>Q99999999</a>
<a href="..." class="entitybase-item entitybase-lexeme" ...>demo</a>
  <span class="entitybase-language">(<a href="..." ...>English</a>)</span>
<a href="..." class="entitybase-item entitybase-property" ...>demo property</a>
  <span class="entitybase-datatype" title="wikibase-item">(item)</span>
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

No PHPUnit, no network: the HTTP transport is faked, so this needs nothing but a
PHP binary. DokuWiki's own classes are stubbed too, which is what lets the
syntax component be rendered and inspected outside a wiki.

The tests cover the label found, missing label, missing entity, empty value,
unparseable body, a transport that gives up, URL encoding, a trailing slash on
the base URL, that a non-200 is never mistaken for a label, the lemma and
datatype endpoints, the whole language chain including the five-language cap,
and the rendering of every entity kind in every mode — including the awkward
cases, where one half of a reference is missing.

CI runs the same file inside `dokuwiki/dokuwiki:stable`, so the tests execute
on a real PHP with cURL rather than whatever a machine happens to have:

```bash
docker run --rm -v "$PWD/plugin-dokuwiki:/plugin:ro" dokuwiki/dokuwiki:stable \
  php /plugin/tests/run.php
```

## Possible next steps

Each is a small addition to what is here, in rough order of value:

- `{{entitylist>Q42|property=P31}}` — the items an item points at.
- `{{senses>L1}}` — the glosses of a lexeme, which the lemmas endpoint sits
  right next to.
- Batch the label lookups per page, so a page with 30 items is one request
  instead of 30. The API already has `GET /v1/resolve/labels/{hashes}`.
- Editor autocomplete for `{{entity>}}` via the search endpoint.