<?php

/** Base URL of the Entitybase API, without a trailing slash */
$conf['api'] = 'http://localhost:8083';

/** Where an entity's page lives in the knowledge base; empty renders plain text */
$conf['entity_url'] = '';

/** Language to use when a page names none; empty means the wiki interface language */
$conf['default_lang'] = '';

/**
 * Languages to try after that, comma separated, at most five: "en, de, fr".
 *
 * Every label and lemma lookup walks this chain until one is found, so a
 * language with few labels does not leave a wiki full of bare ids.
 */
$conf['fallback_chain'] = 'en';

/** Seconds a cached label stays fresh; 0 uses the wiki's cachetime */
$conf['cache_ttl'] = 0;

/** Seconds before an API request is given up on */
$conf['timeout'] = 5;