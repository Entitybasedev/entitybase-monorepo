<?php

/**
 * Minimal Entitybase API client.
 *
 * Deliberately free of DokuWiki dependencies so it can be unit tested on its
 * own, and so the plugin only ever has to understand the API, never the
 * database behind it.
 *
 * The HTTP transport is injectable: production passes a curl/stream transport,
 * tests pass a fake.
 */
class EntitybaseClient
{
    /** @var callable(string):array{status:int,body:string}|null */
    private $transport;

    /** @var string */
    private $baseUrl;

    /**
     * @param string $baseUrl Entitybase API base, e.g. https://kb.example/api
     * @param callable|null $transport fn(string $url): array{status:int,body:string}|null
     */
    public function __construct(string $baseUrl, ?callable $transport = null)
    {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->transport = $transport ?? [$this, 'httpGet'];
    }

    /**
     * The label of an entity in one language.
     *
     * @param string $entityId Entity id, e.g. Q42
     * @param string $language Language code, e.g. en
     * @return string|null The label, or null when there is none
     */
    public function label(string $entityId, string $language): ?string
    {
        $response = $this->get('/v1/entities/' . rawurlencode($entityId) . '/labels/' . rawurlencode($language));
        if ($response === null) {
            return null;
        }
        $value = $response['value'] ?? null;
        return is_string($value) && $value !== '' ? $value : null;
    }

    /**
     * The lemma of a lexeme in one language.
     *
     * A lexeme has no labels; its lemma is the word itself, keyed by language
     * like a label is. The endpoint shape matches the label one, so the
     * language fallback chain works unchanged.
     *
     * @param string $lexemeId Lexeme id, e.g. L1
     * @param string $language Language code, e.g. en
     * @return string|null The lemma, or null when there is none
     */
    public function lemma(string $lexemeId, string $language): ?string
    {
        $path = '/v1/entities/lexemes/' . rawurlencode($lexemeId) . '/lemmas/' . rawurlencode($language);
        $response = $this->get($path);
        if ($response === null) {
            return null;
        }
        $value = $response['value'] ?? null;
        return is_string($value) && $value !== '' ? $value : null;
    }

    /**
     * The language of a lexeme, as the id of the language item: Q1860 for
     * English.
     *
     * @param string $lexemeId Lexeme id, e.g. L1
     * @return string|null The language item id, or null when there is none
     */
    public function lexemeLanguage(string $lexemeId): ?string
    {
        $path = '/v1/entities/lexemes/' . rawurlencode($lexemeId) . '/language';
        $response = $this->get($path);
        if ($response === null) {
            return null;
        }
        $value = $response['language'] ?? null;
        return is_string($value) && $value !== '' ? $value : null;
    }

    /**
     * The datatype of a property: wikibase-item or string.
     *
     * This one needs the whole entity, because the datatype is not a term of
     * its own but part of the property's revision data.
     *
     * @param string $propertyId Property id, e.g. P31
     * @return string|null The datatype, or null when the property has none
     */
    public function propertyDatatype(string $propertyId): ?string
    {
        $response = $this->get('/v1/entities/' . rawurlencode($propertyId));
        if ($response === null) {
            return null;
        }
        $datatype = $response['data']['revision']['datatype'] ?? null;
        return is_string($datatype) && $datatype !== '' ? $datatype : null;
    }

    /**
     * GET a JSON endpoint.
     *
     * A 404 is not an error here: a missing entity and a missing label are
     * both simply "no answer".
     *
     * @return array|null Decoded body, or null when absent or unreadable
     */
    public function get(string $path): ?array
    {
        $url = $this->baseUrl . $path;
        $raw = ($this->transport)($url);
        if ($raw === null || ($raw['status'] ?? 0) !== 200) {
            return null;
        }
        $decoded = json_decode($raw['body'] ?? '', true);
        return is_array($decoded) ? $decoded : null;
    }

    /**
     * Default HTTP transport: cURL when available, otherwise a stream request.
     *
     * @return array{status:int,body:string}|null
     */
    private function httpGet(string $url): ?array
    {
        $timeout = $this->timeout();

        if (function_exists('curl_init')) {
            $curl = curl_init($url);
            curl_setopt_array($curl, [
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_CONNECTTIMEOUT => $timeout,
                CURLOPT_TIMEOUT => $timeout,
                CURLOPT_FOLLOWLOCATION => false,
            ]);
            $body = curl_exec($curl);
            $status = (int) curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
            curl_close($curl);
            return is_string($body) ? ['status' => $status, 'body' => $body] : null;
        }

        $context = stream_context_create([
            'http' => [
                'method' => 'GET',
                'timeout' => $timeout,
                'ignore_errors' => true,
                'header' => "Accept: application/json\r\n",
            ],
        ]);
        $body = @file_get_contents($url, false, $context);
        if ($body === false) {
            return null;
        }
        $status = 0;
        foreach ($http_response_header ?? [] as $header) {
            if (preg_match('#^HTTP/\S+\s+(\d{3})#', $header, $match)) {
                $status = (int) $match[1];
            }
        }
        return ['status' => $status, 'body' => $body];
    }

    /** @return int Timeout in seconds */
    private function timeout(): int
    {
        global $conf;
        $timeout = (int) ($conf['plugin']['entitybase']['timeout'] ?? 5);
        return $timeout > 0 ? $timeout : 5;
    }
}