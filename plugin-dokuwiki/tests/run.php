<?php

/**
 * Tests for EntitybaseClient and the language resolution.
 *
 * No PHPUnit and no network: the HTTP transport is faked, so this runs with
 * nothing but a PHP binary:
 *
 *     php plugin-dokuwiki/tests/run.php
 */

require_once __DIR__ . '/../entitybase/client.php';

/** Minimal assertions, so the tests need no framework. */
final class TestRunner
{
    private int $passed = 0;
    /** @var list<string> */
    private array $failures = [];

    public function test(string $name, callable $body): void
    {
        try {
            $body($this);
            $this->passed++;
        } catch (Throwable $e) {
            $this->failures[] = $name . ': ' . $e->getMessage();
        }
    }

    public function same(mixed $expected, mixed $actual, string $note = ''): void
    {
        if ($expected !== $actual) {
            throw new RuntimeException(sprintf(
                '%sexpected %s, got %s',
                $note === '' ? '' : $note . ': ',
                var_export($expected, true),
                var_export($actual, true)
            ));
        }
    }

    public function true(bool $value, string $note = ''): void
    {
        $this->same(true, $value, $note);
    }

    public function summary(): int
    {
        echo $this->passed . " passed, " . count($this->failures) . " failed\n";
        foreach ($this->failures as $failure) {
            echo "  FAIL " . $failure . "\n";
        }
        return $this->failures === [] ? 0 : 1;
    }
}

/**
 * A transport that answers from a fixed table, and records the URLs asked for.
 *
 * @param array<string,array{status:int,body:string}> $responses
 */
function fakeTransport(array $responses, ?array &$asked = null): callable
{
    return static function (string $url) use ($responses, &$asked): ?array {
        $asked[] = $url;
        return $responses[$url] ?? ['status' => 404, 'body' => '{"error":"http_error"}'];
    };
}

$API = 'http://kb.test:8083';

$t = new TestRunner();

$t->test('label returns the value from a 200', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/Q42/labels/en" => ['status' => 200, 'body' => '{"value":"Douglas Adams"}'],
    ]));

    $t->same('Douglas Adams', $client->label('Q42', 'en'));
});

$t->test('a missing label is null, not an error', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/Q42/labels/de" => ['status' => 404, 'body' => '{"message":"Label not found"}'],
    ]));

    $t->same(null, $client->label('Q42', 'de'));
});

$t->test('a missing entity is null', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([]));

    $t->same(null, $client->label('Q999', 'en'));
});

$t->test('an empty label counts as no label', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/Q42/labels/en" => ['status' => 200, 'body' => '{"value":""}'],
    ]));

    $t->same(null, $client->label('Q42', 'en'));
});

$t->test('unreadable JSON is null rather than an exception', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/Q42/labels/en" => ['status' => 200, 'body' => 'not json at all'],
    ]));

    $t->same(null, $client->label('Q42', 'en'));
});

$t->test('a transport that gives up is null', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, static fn(string $url) => null);

    $t->same(null, $client->label('Q42', 'en'));
});

$t->test('the id and language are url-encoded', function (TestRunner $t) use ($API): void {
    $asked = [];
    $client = new EntitybaseClient($API, fakeTransport([], $asked));
    $client->label('Q42', 'en');

    $t->same("$API/v1/entities/Q42/labels/en", $asked[0]);
});

$t->test('a trailing slash on the base url is ignored', function (TestRunner $t) use ($API): void {
    $asked = [];
    $client = new EntitybaseClient($API . '/', fakeTransport([], $asked));
    $client->label('Q42', 'en');

    $t->same("$API/v1/entities/Q42/labels/en", $asked[0]);
});

$t->test('a non-200 that still parses is not used', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/Q42/labels/en" => ['status' => 500, 'body' => '{"value":"stale"}'],
    ]));

    $t->same(null, $client->label('Q42', 'en'), 'a 500 must not be treated as a label');
});

exit($t->summary());