<?php

use dokuwiki\Extension\HelperPlugin;

/**
 * Label lookup for Entitybase, with caching.
 *
 * Caching matters: a page can mention dozens of entities and the API call is
 * far slower than reading a file.
 */
class helper_plugin_entitybase extends HelperPlugin
{
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
     * Languages to try, in order: an explicit one, the wiki interface
     * language, then the configured fallback.
     *
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

        $add($language);
        $add($conf['lang'] ?? '');
        $add($conf['plugin']['entitybase']['fallback_lang'] ?? 'en');
        return $codes;
    }

    /**
     * The label for one language, cached.
     *
     * @return string|null
     */
    private function cachedLabel(string $entityId, string $language): ?string
    {
        $file = getCacheName('entitybase_' . $entityId . '_' . $language, '.txt');

        $cached = @file_get_contents($file);
        if ($cached !== false) {
            $parts = explode("\n", $cached, 2);
            $expires = (int) ($parts[0] ?? '0');
            if ($expires > time()) {
                $value = $parts[1] ?? '';
                return $value === '' ? null : $value;
            }
        }

        $label = $this->client()->label($entityId, $language);
        // An empty label is cached too, so a missing one is not re-requested on
        // every page render.
        $this->write($file, $this->expiry(), (string) $label);
        return $label;
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