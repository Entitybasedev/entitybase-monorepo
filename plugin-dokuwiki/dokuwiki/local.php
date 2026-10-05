<?php

/**
 * Plugin configuration for the containerised wiki.
 *
 * The API is reached over the compose network by service name, not over the
 * published host port, so the wiki works without depending on the host.
 *
 * Mounted over the generated conf/local.php, which is what makes the plugin
 * work out of the box in `docker compose up`. A real deployment should set
 * these in Admin -> Configuration Settings instead and drop the mount.
 */

$conf['plugin']['entitybase']['api'] = 'http://entitybase-api:8080';

// Where an item's page lives in Entitybase, as the browser sees it
$conf['plugin']['entitybase']['entity_url'] = 'http://localhost:8080/entity';

// Short-lived cache: the point of this wiki is looking things up while writing
$conf['plugin']['entitybase']['cache_ttl'] = 300;