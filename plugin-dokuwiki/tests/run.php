<?php

/**
 * Tests for EntitybaseClient, the syntax component and the language
 * resolution.
 *
 * No PHPUnit and no network: the HTTP transport is faked and DokuWiki's own
 * classes are stubbed, so this runs with nothing but a PHP binary:
 *
 *     php plugin-dokuwiki/tests/run.php
 */

// Just enough DokuWiki for syntax.php to be loaded outside a wiki. Declared in
// its own namespace because syntax.php imports these names.
namespace dokuwiki\Parsing {
    class Handler
    {
    }

    class ModeRegistry
    {
        public const CATEGORY_SUBSTITUTION = 'substitution';
    }
}

namespace dokuwiki\Extension {
    class Plugin
    {
        /** @var object|null The lexer, as DokuWiki sets it before connecting */
        public $Lexer = null;

        /** @var object|null Set by the test to skip loadHelper() */
        public $stubHelper = null;

        public function getLexer()
        {
            return $this->Lexer;
        }

        protected function loadHelper($name, $prefix = '', $autoload = false)
        {
            return $this->stubHelper;
        }

        protected function getLang($id)
        {
            return $id;
        }
    }

    class SyntaxPlugin extends Plugin
    {
    }
}

namespace {
    require_once __DIR__ . '/../entitybase/client.php';
    require_once __DIR__ . '/../entitybase/syntax.php';
    require_once __DIR__ . '/../entitybase/helper.php';

    /** Where the stubbed cache writes; removed again when the tests are done. */
    $cacheDir = sys_get_temp_dir() . '/entitybase-plugin-tests-' . getmypid();
    @mkdir($cacheDir);
    register_shutdown_function(static function () use (&$cacheDir): void {
        foreach (glob($cacheDir . '/*') ?: [] as $file) {
            @unlink($file);
        }
        @rmdir($cacheDir);
    });

    /** Records the patterns a syntax component connects. */
    final class TestLexer
    {
        /** @var list<string> */
        public array $patterns = [];

        public function addSpecialPattern($pattern, $mode, $name): void
        {
            $this->patterns[] = $pattern;
        }
    }

    /** DokuWiki's renderer base, of which only the output string matters here. */
    class Doku_Renderer
    {
        public string $doc = '';
    }

    /** DokuWiki's cache naming, reduced to a directory the test may write to. */
    function getCacheName($id, $ext)
    {
        global $cacheDir;

        return $cacheDir . '/' . md5($id) . $ext;
    }

    final class TestRenderer extends Doku_Renderer
    {
    }

    /** The helper, with its answers given instead of looked up. */
    final class StubHelper
    {
        /** @var array<string,array{lemmas:array<string,string>,language:?string,labels:array<string,string>}> */
        public array $entities;

        public function __construct(array $entities)
        {
            $this->entities = $entities;
        }

        public function label(string $entityId, ?string $language = null): ?string
        {
            return $this->in($entityId, 'labels', $language);
        }

        public function lemma(string $lexemeId, ?string $language = null): ?string
        {
            return $this->in($lexemeId, 'lemmas', $language);
        }

        /**
         * One term in one language, with the same fallback the helper does:
         * the language asked for, then English.
         */
        private function in(string $entityId, string $kind, ?string $language): ?string
        {
            $terms = $this->entities[$entityId][$kind] ?? [];
            foreach ([$language, 'en'] as $code) {
                if ($code !== null && isset($terms[$code])) {
                    return $terms[$code];
                }
            }
            return null;
        }

        public function lexemeLanguage(string $lexemeId, ?string $language = null): array
        {
            $id = $this->entities[$lexemeId]['language'] ?? null;
            return ['id' => $id, 'label' => $id === null ? null : $this->label($id, $language)];
        }

        public function datatype(string $propertyId): ?string
        {
            return $this->entities[$propertyId]['datatype'] ?? null;
        }
    }

    /** Parse and render wikitext, the way DokuWiki does. */
    function render(string $wikitext, array $entities): string
    {
        global $conf;

        $plugin = new syntax_plugin_entitybase();
        $plugin->Lexer = new TestLexer();
        $plugin->stubHelper = new StubHelper($entities);
        $plugin->connectTo('base');

        $pattern = '/' . $plugin->Lexer->patterns[0] . '/';
        if (!preg_match($pattern, $wikitext, $match)) {
            throw new RuntimeException("the pattern did not match: $wikitext");
        }

        $renderer = new TestRenderer();
        $plugin->render('xhtml', $renderer, $plugin->handle($match[0], 0, 0, new dokuwiki\Parsing\Handler()));
        return $renderer->doc;
    }

    /** The ids the rendered output links to, in order. */
    function linkedIds(string $html): array
    {
        preg_match_all('#<a href="[^"]*/entity/([^"/]+)"#', $html, $matches);
        return $matches[1];
    }

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

// The knowledge base the plugin links to, as the admin settings would set it
$conf['plugin']['entitybase']['entity_url'] = 'http://kb.test/entity';

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

$t->test('a lemma comes from the lexemes endpoint', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/lexemes/L1/lemmas/en" => ['status' => 200, 'body' => '{"value":"demo"}'],
    ]));

    $t->same('demo', $client->lemma('L1', 'en'));
});

$t->test('a lexeme without a lemma in that language is null', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/lexemes/L1/lemmas/de" => ['status' => 404, 'body' => '{"message":"Lemma not found"}'],
    ]));

    $t->same(null, $client->lemma('L1', 'de'));
});

$t->test('a lexeme language is the id of the language item', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/lexemes/L1/language" => ['status' => 200, 'body' => '{"language":"Q1860"}'],
    ]));

    $t->same('Q1860', $client->lexemeLanguage('L1'));
});

$t->test('a lexeme without a language is null', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([]));

    $t->same(null, $client->lexemeLanguage('L1'));
});

$t->test('lemma and language lookups use different urls', function (TestRunner $t) use ($API): void {
    $asked = [];
    $client = new EntitybaseClient($API, fakeTransport([], $asked));
    $client->lemma('L1', 'en');
    $client->lexemeLanguage('L1');

    $t->same("$API/v1/entities/lexemes/L1/lemmas/en", $asked[0]);
    $t->same("$API/v1/entities/lexemes/L1/language", $asked[1]);
});

$t->test('a language item label comes from the ordinary label endpoint', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/Q1860/labels/en" => ['status' => 200, 'body' => '{"value":"English"}'],
    ]));

    $t->same('English', $client->label('Q1860', 'en'));
});

$t->test('a datatype is read out of the entity data', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/P31" => ['status' => 200, 'body' => '{"id":"P31","data":{"revision":{"id":"P31","datatype":"wikibase-item"}}}'],
    ]));

    $t->same('wikibase-item', $client->propertyDatatype('P31'));
});

$t->test('an item has no datatype', function (TestRunner $t) use ($API): void {
    $client = new EntitybaseClient($API, fakeTransport([
        "$API/v1/entities/Q42" => ['status' => 200, 'body' => '{"id":"Q42","data":{"revision":{"id":"Q42"}}}'],
    ]));

    $t->same(null, $client->propertyDatatype('Q42'));
});

/** Set the plugin settings a language lookup reads. */
function withLanguages(array $settings, string $wikiLang, callable $body): void
{
    global $conf;

    $before = $conf['plugin']['entitybase'] ?? [];
    $conf['lang'] = $wikiLang;
    $conf['plugin']['entitybase'] = $settings;

    try {
        $body(new helper_plugin_entitybase());
    } finally {
        $conf['plugin']['entitybase'] = $before;
    }
}

$t->test('the wiki interface language is used when the page names none', function (TestRunner $t): void {
    withLanguages(['default_lang' => '', 'fallback_chain' => 'en,fr'], 'de', function (helper_plugin_entitybase $helper) use ($t): void {
        $t->same(['de', 'en', 'fr'], $helper->languages());
    });
});

$t->test('a language named in the page comes first', function (TestRunner $t): void {
    withLanguages(['default_lang' => 'es', 'fallback_chain' => 'en'], 'de', function (helper_plugin_entitybase $helper) use ($t): void {
        $t->same(['nl', 'es', 'de', 'en'], $helper->languages('nl'));
    });
});

$t->test('the default language comes before the wiki language', function (TestRunner $t): void {
    withLanguages(['default_lang' => 'es', 'fallback_chain' => 'en'], 'de', function (helper_plugin_entitybase $helper) use ($t): void {
        $t->same(['es', 'de', 'en'], $helper->languages());
    });
});

$t->test('a language is never asked for twice', function (TestRunner $t): void {
    withLanguages(['default_lang' => 'de', 'fallback_chain' => 'de, en ,de'], 'de', function (helper_plugin_entitybase $helper) use ($t): void {
        $t->same(['de', 'en'], $helper->languages());
    });
});

$t->test('the fallback chain stops at five languages', function (TestRunner $t): void {
    withLanguages(['default_lang' => '', 'fallback_chain' => 'aa,bb,cc,dd,ee,ff,gg'], 'de', function (helper_plugin_entitybase $helper) use ($t): void {
        $t->same(['aa', 'bb', 'cc', 'dd', 'ee'], $helper->fallbackChain());
        $t->same(['de', 'aa', 'bb', 'cc', 'dd', 'ee'], $helper->languages());
    });
});

$t->test('an empty chain is no chain', function (TestRunner $t): void {
    withLanguages(['default_lang' => '', 'fallback_chain' => ''], 'de', function (helper_plugin_entitybase $helper) use ($t): void {
        $t->same(['de'], $helper->languages());
    });
});

/** The entities the syntax tests resolve against. */
$ENTITIES = [
    'Q42' => ['labels' => ['en' => 'Douglas Adams'], 'lemmas' => [], 'language' => null, 'datatype' => null],
    'P31' => ['labels' => ['en' => 'instance of'], 'lemmas' => [], 'language' => null, 'datatype' => 'wikibase-item'],
    'P2' => ['labels' => ['en' => 'named after'], 'lemmas' => [], 'language' => null, 'datatype' => 'string'],
    'P3' => ['labels' => [], 'lemmas' => [], 'language' => null, 'datatype' => 'wikibase-item'],
    'Q1860' => ['labels' => ['en' => 'English'], 'lemmas' => [], 'language' => null, 'datatype' => null],
    'L1' => ['labels' => [], 'lemmas' => ['en' => 'demo', 'de' => 'Vorführung'], 'language' => 'Q1860', 'datatype' => null],
    'L2' => ['labels' => [], 'lemmas' => ['en' => 'taught'], 'language' => 'Q1860', 'datatype' => null],
    'L3' => ['labels' => [], 'lemmas' => [], 'language' => 'Q1860', 'datatype' => null],
    'L4' => ['labels' => [], 'lemmas' => ['en' => 'silent'], 'language' => null, 'datatype' => null],
];

$t->test('an item renders as its label', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{entity>Q42}}', $ENTITIES);

    $t->same('Douglas Adams', strip_tags($html));
    $t->same(['Q42'], linkedIds($html));
    $t->true(!str_contains($html, 'entitybase-missing'));
});

$t->test('a property renders as its label and datatype', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{property>P31}}', $ENTITIES);

    $t->same('instance of (item)', strip_tags($html));
    // Only the property is an entity, so only it is linked
    $t->same(['P31'], linkedIds($html));
});

$t->test('the entity macro renders a property like the property macro', function (TestRunner $t) use ($ENTITIES): void {
    $t->same(render('{{property>P31}}', $ENTITIES), render('{{entity>P31}}', $ENTITIES));
});

$t->test('a datatype without the wikibase prefix keeps its own name', function (TestRunner $t) use ($ENTITIES): void {
    $t->same('named after (string)', strip_tags(render('{{property>P2}}', $ENTITIES)));
});

$t->test('the label mode leaves the datatype out', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{property>P31||label}}', $ENTITIES);

    $t->same('instance of', strip_tags($html));
    $t->true(!str_contains($html, 'entitybase-datatype'));
});

$t->test('the datatype mode leaves the label out', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{property>P31||datatype}}', $ENTITIES);

    $t->same('(item)', strip_tags($html));
    $t->true(!str_contains($html, 'entitybase-item'));
});

$t->test('a property without a datatype shows just its label', function (TestRunner $t) use ($ENTITIES): void {
    $entities = array_replace($ENTITIES, ['P31' => ['labels' => ['en' => 'instance of'], 'lemmas' => [], 'language' => null, 'datatype' => null]]);

    $t->same('instance of', strip_tags(render('{{property>P31}}', $entities)));
});

$t->test('a property without a label shows its id, and keeps the datatype', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{property>P3}}', $ENTITIES);

    $t->same('P3 (item)', strip_tags($html));
    $t->true(str_contains($html, 'entitybase-missing'));
});

$t->test('an item without a label shows its id, marked as missing', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{entity>Q999}}', $ENTITIES);

    $t->same('Q999', strip_tags($html));
    $t->true(str_contains($html, 'entitybase-missing'));
});

$t->test('a lexeme renders as lemma and language', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{lexeme>L1}}', $ENTITIES);

    $t->same('demo (English)', strip_tags($html));
    // The lemma links to the lexeme, the language to the language item
    $t->same(['L1', 'Q1860'], linkedIds($html));
});

$t->test('the entity macro renders a lexeme like the lexeme macro', function (TestRunner $t) use ($ENTITIES): void {
    $t->same(render('{{lexeme>L1}}', $ENTITIES), render('{{entity>L1}}', $ENTITIES));
});

$t->test('a lexeme looks its lemma up in a chosen language', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{lexeme>L1|de}}', $ENTITIES);

    $t->same('Vorführung (English)', strip_tags($html));
});

$t->test('a lexeme lemma falls back to the next language of the chain', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{lexeme>L2|de}}', $ENTITIES);

    $t->same('taught (English)', strip_tags($html), 'L2 has no German lemma');
});

$t->test('a lexeme without a lemma shows its id, and keeps the language', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{lexeme>L3|de}}', $ENTITIES);

    $t->same('L3 (English)', strip_tags($html));
    $t->true(str_contains($html, 'entitybase-missing'));
});

$t->test('a lexeme without a language shows just the lemma', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{lexeme>L4}}', $ENTITIES);

    $t->same('silent', strip_tags($html));
    $t->same(['L4'], linkedIds($html));
    $t->true(!str_contains($html, 'entitybase-missing'));
});

$t->test('the lemma mode leaves the language out', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{lexeme>L1||lemma}}', $ENTITIES);

    $t->same('demo', strip_tags($html));
    $t->same(['L1'], linkedIds($html));
});

$t->test('the language mode leaves the lemma out', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{lexeme>L1||lang}}', $ENTITIES);

    $t->same('(English)', strip_tags($html));
    $t->same(['Q1860'], linkedIds($html));
});

$t->test('a lexeme language without a label falls back to its id', function (TestRunner $t) use ($ENTITIES): void {
    // The language item exists but has no label at all
    $entities = array_replace($ENTITIES, ['Q1860' => ['labels' => [], 'lemmas' => [], 'language' => null]]);
    $html = render('{{lexeme>L1||lang}}', $entities);

    $t->same('(Q1860)', strip_tags($html));
    $t->true(str_contains($html, 'entitybase-missing'));
});

$t->test('a language and a mode are read in order', function (TestRunner $t) use ($ENTITIES): void {
    $html = render('{{lexeme>L1|de|lemma}}', $ENTITIES);

    $t->same('Vorführung', strip_tags($html));
});

$t->test('the language mode of a lexeme without a language renders nothing', function (TestRunner $t) use ($ENTITIES): void {
    $t->same('', render('{{lexeme>L4||lang}}', $ENTITIES));
});

$t->test('a lexeme is matched inside surrounding text', function (TestRunner $t) use ($ENTITIES): void {
    // Only the macro itself is rendered here; the words around it are DokuWiki's
    // business, and it is their presence that must not stop the match.
    $html = render('The {{lexeme>L1}} is a lexeme.', $ENTITIES);

    $t->same('demo (English)', strip_tags($html));
});

exit($t->summary());
}