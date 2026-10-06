<?php

/** Admin field types: see the config plugin's metadata reference */
$meta['api'] = array('string', '_caution' => 'security');
$meta['entity_url'] = array('string');
$meta['cache_ttl'] = array('numeric', '_min' => 0);
$meta['timeout'] = array('numeric', '_min' => 1);