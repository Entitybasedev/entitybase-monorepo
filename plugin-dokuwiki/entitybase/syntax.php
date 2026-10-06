<?php

use dokuwiki\Extension\SyntaxPlugin;
use dokuwiki\Parsing\Handler;
use dokuwiki\Parsing\ModeRegistry;

/**
 * Entitybase Plugin: refer to Entitybase entities in a wiki page.
 *
 * Syntax:
 *   {{entity>Q42}}           an item as its label
 *   {{entity>Q42|de}}        the label in a chosen language
 *   {{lexeme>L1}}            a lexeme as its lemma and language: "demo (English)"
 *   {{lexeme>L1|de}}         the lemma looked up in German first
 *   {{lexeme>L1||lemma}}     only the lemma
 *   {{lexeme>L1||lang}}      only the language
 *   {{property>P1}}          a property as its label and datatype: "instance of (item)"
 *   {{property>P1|de}}       the label in a chosen language
 *   {{property>P1||label}}   only the label
 *   {{property>P1||datatype}} only the datatype
 *
 * The three names are interchangeable: what a macro renders is decided from
 * the id, so {{entity>L1}} is a lexeme and {{lexeme>P1}} is a property. The
 * names are there to say what the writer means, not to pick a different
 * lookup.
 *
 * Renders the label, linking to the entity in the knowledge base. When the
 * entity has no label, the id itself is shown, so the page still reads well.
 */
class syntax_plugin_entitybase extends SyntaxPlugin
{
    /** @inheritDoc */
    public function getType()
    {
        return ModeRegistry::CATEGORY_SUBSTITUTION;
    }

    /** @inheritDoc */
    public function getPType()
    {
        return 'block';
    }

    /** @inheritDoc */
    public function getSort()
    {
        // After the info plugin, with the other substitution plugins
        return 160;
    }

    /** @inheritDoc */
    public function connectTo($mode)
    {
        // {{entity>Q42}}, {{lexeme>L1|de|lemma}}, {{property>P1||datatype}}
        // Ids are letters plus digits, so items, properties and lexemes all
        // match; what one renders as is decided from the id, not from the
        // name the writer typed.
        $this->Lexer->addSpecialPattern(
            '\{\{(?:entity|lexeme|property)>[A-Za-z]+\d+(?:\|[a-zA-Z-]*){0,2}\}\}',
            $mode,
            'plugin_entitybase'
        );
    }

    /**
     * @param string $match The matched text
     * @param int $state The lexer state
     * @param int $pos The character position
     * @param Handler $handler The handler
     * @return array Data for render()
     */
    public function handle($match, $state, $pos, Handler $handler)
    {
        $inner = preg_replace('#^\{\{[a-z]+>#', '', $match);
        $inner = substr($inner, 0, -2); // strip the opening '}}' marker too
        $args = array_map('trim', explode('|', $inner));

        $entityId = array_shift($args);

        // An empty part is a skipped argument: {{lexeme>L1||lemma}} leaves the
        // lemma language at its default while still naming the mode. The
        // positions therefore matter, so the parts are read by index.
        return [
            $entityId,
            ($args[0] ?? '') === '' ? null : $args[0], // a language, in every mode
            ($args[1] ?? '') === '' ? null : $args[1], // a mode: lemma, lang, or nothing
        ];
    }

    /**
     * @param string $format Output format
     * @param Doku_Renderer $renderer The renderer
     * @param array $data Data from handle()
     * @return bool Rendered correctly
     */
    public function render($format, Doku_Renderer $renderer, $data)
    {
        if ($format !== 'xhtml') {
            return false;
        }

        /** @var Doku_Renderer_xhtml $renderer */
        [$entityId, $language, $mode] = [$data[0], $data[1] ?? null, $data[2] ?? null];

        $helper = $this->loadHelper('entitybase');

        // What an entity renders as follows from its id, not from the macro
        // name: a lexeme has no label, a property has a datatype.
        if (preg_match('#^[Ll]\d+$#', $entityId)) {
            $renderer->doc .= $this->renderLexeme($helper, $entityId, $language, $mode);
            return true;
        }

        $label = $helper->label($entityId, $language);

        if (preg_match('#^[Pp]\d+$#', $entityId)) {
            $renderer->doc .= $this->renderProperty($helper, $entityId, $mode, $label);
            return true;
        }

        $renderer->doc .= $this->renderItem($label ?? $entityId, $entityId, $label !== null);
        return true;
    }

    /**
     * A property: its label, then its datatype in brackets.
     *
     * The datatype is not an entity, so unlike the lemma of a lexeme or the
     * label of an item there is nothing to link it to; it names the kind of
     * value the property takes, which is what a reader cannot tell from the
     * label alone.
     *
     * @param helper_plugin_entitybase $helper The plugin helper
     * @param string|null $label The label already looked up, if any
     * @return string HTML
     */
    private function renderProperty(
        $helper,
        string $propertyId,
        ?string $mode,
        ?string $label
    ): string {
        $mode = strtolower((string) $mode);
        $datatype = $helper->datatype($propertyId);

        if ($mode === 'datatype' || $mode === 'type') {
            return $datatype === null ? '' : $this->renderDatatype($datatype);
        }

        $html = $this->renderItem($label ?? $propertyId, $propertyId, $label !== null, 'entitybase-property');
        if ($mode === 'label' || $datatype === null) {
            return $html;
        }

        return $html . ' ' . $this->renderDatatype($datatype);
    }

    /**
     * The datatype of a property, in brackets: "(item)".
     *
     * The 'wikibase-' prefix is dropped because it names the software the
     * datatype came from, not the kind of value: 'wikibase-item' and 'item'
     * mean the same to anyone writing in the wiki.
     */
    private function renderDatatype(string $datatype): string
    {
        $readable = preg_replace('#^wikibase-#', '', $datatype);

        return '<span class="entitybase-datatype" title="' . $this->escape($datatype) . '">('
            . $this->escape((string) $readable) . ')</span>';
    }

    /**
     * A lexeme: its lemma, then its language in brackets, both linked.
     *
     * Neither part is dropped when the other is missing. A lemma without a
     * language still names a word, and a language without a lemma is still
     * what the id referred to.
     *
     * @param helper_plugin_entitybase $helper The plugin helper
     * @return string HTML
     */
    private function renderLexeme($helper, string $lexemeId, ?string $language, ?string $mode = null): string
    {
        $mode = strtolower((string) $mode);

        if ($mode === 'lemma') {
            $lemma = $helper->lemma($lexemeId, $language);
            return $this->renderItem($lemma ?? $lexemeId, $lexemeId, $lemma !== null, 'entitybase-lexeme');
        }

        if ($mode === 'lang' || $mode === 'language') {
            $html = $this->renderLanguage($helper->lexemeLanguage($lexemeId, $language));
            return $html === '' ? '' : '<span class="entitybase-language">' . $html . '</span>';
        }

        $lemma = $helper->lemma($lexemeId, $language);
        $lemmaHtml = $this->renderItem($lemma ?? $lexemeId, $lexemeId, $lemma !== null, 'entitybase-lexeme');

        $languageHtml = $this->renderLanguage($helper->lexemeLanguage($lexemeId, $language));
        if ($languageHtml === '') {
            return $lemmaHtml;
        }

        return $lemmaHtml . ' <span class="entitybase-language">' . $languageHtml . '</span>';
    }

    /**
     * The language of a lexeme, shown as the label of the language item.
     *
     * @param array{id:?string,label:?string} $lexemeLanguage
     * @return string HTML, or '' when the lexeme has no language at all
     */
    private function renderLanguage(array $lexemeLanguage): string
    {
        if (($lexemeLanguage['id'] ?? null) === null) {
            return '';
        }

        $languageId = $lexemeLanguage['id'];
        $label = $lexemeLanguage['label'] ?? null;

        return '(' . $this->renderItem(
            $label ?? $languageId,
            $languageId,
            $label !== null,
            'entitybase-lexeme-language'
        ) . ')';
    }

    /**
     * One linked item: the label when there is one, otherwise the id, which is
     * styled to show that the entity has no label in this language.
     *
     * @param string $text What to show
     * @param string $entityId The entity being shown
     * @param bool $hasLabel Whether the text is a real label
     * @param string $extraClass An additional class for this use of the item
     * @return string HTML
     */
    private function renderItem(string $text, string $entityId, bool $hasLabel, string $extraClass = ''): string
    {
        $url = $this->entityUrl($entityId);
        $class = 'entitybase-item' . ($extraClass === '' ? '' : ' ' . $extraClass)
            . ($hasLabel ? '' : ' entitybase-missing');
        $attributes = 'class="' . $class . '"';
        $title = $hasLabel ? $entityId : $this->getLang('entitybase_missing') . ' (' . $entityId . ')';
        $title = ' title="' . $this->escape($title) . '"';

        if ($url !== '') {
            return '<a href="' . $this->escape($url) . '"' . $title . $attributes
                . ' rel="noopener noreferrer">' . $this->escape($text) . '</a>';
        }

        // No knowledge base URL configured: plain text, still marked up
        return '<span' . $attributes . $title . ' data-entity-id="' . $this->escape($entityId) . '">'
            . $this->escape($text) . '</span>';
    }

    /**
     * The entity's page in the knowledge base, when one is configured.
     *
     * @return string URL, or '' when not configured
     */
    private function entityUrl(string $entityId): string
    {
        global $conf;

        $base = trim((string) ($conf['plugin']['entitybase']['entity_url'] ?? ''));
        if ($base === '') {
            return '';
        }
        return rtrim($base, '/') . '/' . rawurlencode($entityId);
    }

    private function escape(string $text): string
    {
        return htmlspecialchars($text, ENT_QUOTES, 'UTF-8');
    }
}