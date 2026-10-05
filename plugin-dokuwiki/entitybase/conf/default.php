<?php

/** Base URL of the Entitybase API, without a trailing slash */
$conf['api'] = 'http://localhost:8083';

/** Where an entity's page lives in the knowledge base; empty renders plain text */
$conf['entity_url'] = '';

/** Language to try when the wiki interface language has no label */
$conf['fallback_lang'] = 'en';

/** Seconds a cached label stays fresh; 0 uses the wiki's cachetime */
$conf['cache_ttl'] = 0;

/** Seconds before an API request is given up on */
$conf['timeout'] = 5;
