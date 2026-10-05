<?php

use dokuwiki\Extension\SyntaxPlugin;
use dokuwiki\Parsing\Handler;
use dokuwiki\Parsing\ModeRegistry;

/**
 * Entitybase Plugin: refer to Entitybase items in a wiki page.
 *
 * Syntax:
 *   {{entity>Q42}}       the label in the wiki interface language
 *   {{entity>Q42|de}}    the label in a chosen language
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
        // {{entity>Q42}} or {{entity>Q42|de}}
        $this->Lexer->addSpecialPattern('\{\{entity>[A-Za-z]+\d+(?:\|[a-zA-Z-]+)?\}\}', $mode, 'plugin_entitybase');
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
        $inner = substr($match, 9, -2); // strip '{{entity>' and '}}'
        [$entityId, $language] = array_pad(explode('|', $inner, 2), 2, null);
        return [trim($entityId), $language === null ? null : trim($language)];
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
        [$entityId, $language] = [$data[0], $data[1] ?? null];

        $helper = $this->loadHelper('entitybase');
        $label = $helper->label($entityId, $language);
        $text = $label ?? $entityId;

        $renderer->doc .= $this->renderItem($text, $entityId, (bool) $label);
        return true;
    }

    /**
     * One linked item: the label when there is one, otherwise the id, which is
     * styled to show that the entity has no label in this language.
     *
     * @return string HTML
     */
    private function renderItem(string $text, string $entityId, bool $hasLabel): string
    {
        $url = $this->entityUrl($entityId);
        $attributes = 'class="entitybase-item' . ($hasLabel ? '' : ' entitybase-missing') . '"';
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