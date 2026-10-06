<?php

use dokuwiki\Extension\Plugin;

/**
 * Label lookup for Entitybase, with caching.
 *
 * Caching matters: a page can mention dozens of entities and the API call is
 * far slower than reading a file.
 *
 * Helpers in this DokuWiki release extend Plugin; there is no HelperPlugin
 * base class.
 */
class helper_plugin_entitybase extends Plugin
{
    /** How many languages the configured fallback chain may hold */
    public const MAX_FALLBACK_LANGUAGES = 5;

    /** @var EntitybaseClient|null */
    private $client = null;

    /**
     * The label of an entity, in the wiki interface language or the configured
     * fallback.
     *
     * @param string $entityId Entity id, e.g. Q42
     * @param string|null $language Force a language, e.g. 'de'
     * @return string|null The label, or null when the entity has none
     */
    public function label(string $entityId, ?string $language = null): ?string
    {
        $entityId = trim($entityId);
        if ($entityId === '') {
            return null;
        }

        foreach ($this->languages($language) as $code) {
            $label = $this->cachedLabel($entityId, $code);
            if ($label !== null) {
                return $label;
            }
        }
        return null;
    }

    /**
     * The lemma of a lexeme, in the wiki interface language or the configured
     * fallback.
     *
     * @param string $lexemeId Lexeme id, e.g. L1
     * @param string|null $language Force a language, e.g. 'de'
     * @return string|null The lemma, or null when the lexeme has none
     */
    public function lemma(string $lexemeId, ?string $language = null): ?string
    {
        $lexemeId = trim($lexemeId);
        if ($lexemeId === '') {
            return null;
        }

        foreach ($this->languages($language) as $code) {
            $lemma = $this->cached($this->cacheKey($lexemeId, 'lemma', $code), function () use ($lexemeId, $code) {
                return $this->client()->lemma($lexemeId, $code);
            });
            if ($lemma !== null) {
                return $lemma;
            }
        }
        return null;
    }

    /**
     * The language of a lexeme, as the id of the language item, and the label to
     * show for it.
     *
     * A lexeme's language is a reference to another entity, so displaying it
     * needs a second lookup: Q1860 on its own means nothing to a reader.
     *
     * @param string $lexemeId Lexeme id, e.g. L1
     * @param string|null $language Language for the language label, e.g. 'de'
     * @return array{id:?string,label:?string} The language item id and its label
     */
    public function lexemeLanguage(string $lexemeId, ?string $language = null): array
    {
        $lexemeId = trim($lexemeId);
        $id = $lexemeId === '' ? null : $this->cached($this->cacheKey($lexemeId, 'language', ''), function () use ($lexemeId) {
            return $this->client()->lexemeLanguage($lexemeId);
        });

        return [
            'id' => $id,
            // The language label is an ordinary entity label, so it goes
            // through the same fallback chain as any other reference.
            'label' => $id === null ? null : $this->label($id, $language),
        ];
    }

    /**
     * The datatype of a property, e.g. wikibase-item.
     *
     * A datatype belongs to the property rather than to a language of it, so
     * this lookup has no language and no chain.
     *
     * @param string $propertyId Property id, e.g. P31
     * @return string|null The datatype, or null when the property has none
     */
    public function datatype(string $propertyId): ?string
    {
        $propertyId = trim($propertyId);
        if ($propertyId === '') {
            return null;
        }

        return $this->cached($this->cacheKey($propertyId, 'datatype', ''), function () use ($propertyId) {
            return $this->client()->propertyDatatype($propertyId);
        });
    }

    /**
     * Languages to try, in order: the one the page named, the configured
     * default, the wiki interface language, then the fallback chain.
     *
     * @param string|null $language A language named in the page
     * @return list<string>
     */
    public function languages(?string $language = null): array
    {
        global $conf;

        $codes = [];
        $add = static function (?string $code) use (&$codes): void {
            $code = trim((string) $code);
            if ($code !== '' && !in_array($code, $codes, true)) {
                $codes[] = $code;
            }
        };

        $add($language); // named in the page, as {{entity>Q42|de}}
        $add($conf['plugin']['entitybase']['default_lang'] ?? '');
        $add($conf['lang'] ?? ''); // the wiki interface language
        foreach ($this->fallbackChain() as $code) {
            $add($code);
        }
        return $codes;
    }

    /**
     * The configured fallback languages, in order and at most five of them.
     *
     * Five is a deliberate ceiling: a chain longer than that costs one request
     * per language for every entity on a page that is missing its label, and
     * the languages nobody labels anything in are the ones that should be cut.
     *
     * @return list<string>
     */
    public function fallbackChain(): array
    {
        global $conf;

        $configured = explode(',', (string) ($conf['plugin']['entitybase']['fallback_chain'] ?? ''));

        $codes = [];
        foreach ($configured as $code) {
            $code = trim($code);
            if ($code !== '') {
                $codes[] = $code;
            }
            if (count($codes) >= self::MAX_FALLBACK_LANGUAGES) {
                break;
            }
        }
        return $codes;
    }

    /**
     * The label for one language, cached.
     *
     * @return string|null
     */
    private function cachedLabel(string $entityId, string $language): ?string
    {
        return $this->cached($this->cacheKey($entityId, 'label', $language), function () use ($entityId, $language) {
            return $this->client()->label($entityId, $language);
        });
    }

    /**
     * Cache file name for one lookup.
     *
     * The kind keeps labels and lemmas of the same id apart, and an empty
     * language is allowed for lookups that are not per language.
     */
    private function cacheKey(string $entityId, string $kind, string $language): string
    {
        return 'entitybase_' . $entityId . '_' . $kind . ($language === '' ? '' : '_' . $language);
    }

    /**
     * One lookup, cached.
     *
     * An empty value is cached too, so a missing label is not re-requested on
     * every page render.
     *
     * @param callable():?string $fetch How to ask the API
     * @return string|null
     */
    private function cached(string $file, callable $fetch): ?string
    {
        $name = getCacheName($file, '.txt');

        $cached = @file_get_contents($name);
        if ($cached !== false) {
            $parts = explode("\n", $cached, 2);
            $expires = (int) ($parts[0] ?? '0');
            if ($expires > time()) {
                $value = $parts[1] ?? '';
                return $value === '' ? null : $value;
            }
        }

        $value = $fetch();
        $this->write($name, $this->expiry(), (string) $value);
        return $value;
    }

    /** Write a cache entry, ignoring failures: caching is best effort. */
    private function write(string $file, int $expires, string $label): void
    {
        $fh = @fopen($file, 'w');
        if ($fh === false) {
            return;
        }
        fwrite($fh, $expires . "\n" . $label);
        fclose($fh);
    }

    /** @return int Unix timestamp when a cached label goes stale */
    private function expiry(): int
    {
        global $conf;

        $ttl = (int) ($conf['plugin']['entitybase']['cache_ttl'] ?? 0);
        if ($ttl <= 0) {
            $ttl = (int) ($conf['cachetime'] ?? 86400);
        }
        return time() + max($ttl, 60);
    }

    /** @return EntitybaseClient */
    private function client(): EntitybaseClient
    {
        if ($this->client === null) {
            require_once __DIR__ . '/client.php';
            global $conf;
            $this->client = new EntitybaseClient((string) ($conf['plugin']['entitybase']['api'] ?? ''));
        }
        return $this->client;
    }
}