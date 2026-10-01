<template>
  <main class="app">
    <h1>Entitybase</h1>
    <nav class="tabs" data-testid="nav">
      <router-link
        data-testid="nav-entities"
        :class="{ active: isActive('/') }"
        :to="{ path: '/', query: navQuery }"
      >
        Entities
      </router-link>
      <router-link
        data-testid="nav-stream"
        :class="{ active: isActive('/stream') }"
        to="/stream"
      >
        Change stream
      </router-link>
      <div class="header-controls">
        <label class="control">
          Language
          <select
            data-testid="language-select"
            v-model="language"
          >
            <option v-for="l in SUPPORTED_LANGUAGES" :key="l.code" :value="l.code">
              {{ l.name }}
            </option>
          </select>
        </label>
        <label class="control" title="Append the entity ID to labels">
          <input
            type="checkbox"
            data-testid="show-qid-toggle"
            v-model="showQid"
          />
          Show IDs
        </label>
      </div>
      <UserMenu />
      <div class="docs-menu">
        <button data-testid="nav-docs" @click="docsOpen = !docsOpen">
          Docs ▾
        </button>
        <div v-if="docsOpen" class="docs-dropdown" data-testid="docs-dropdown">
          <a
            href="https://entitybasedev.github.io/entitybase-monorepo/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Documentation ↗
          </a>
          <a href="/docs" target="_blank" rel="noopener noreferrer">
            API docs (entitybase) ↗
          </a>
          <a href="http://localhost:8888/docs" target="_blank" rel="noopener noreferrer">
            API docs (change stream) ↗
          </a>
        </div>
      </div>
    </nav>

    <router-view />
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import UserMenu from './components/UserMenu.vue'
import { language, showQid, SUPPORTED_LANGUAGES } from './settings.js'

const route = useRoute()
const docsOpen = ref(false)

// Preserve the current entity when switching tabs back to Entities
const navQuery = computed(() => {
  const entity = typeof route.query.entity === 'string' ? route.query.entity : ''
  return entity ? { entity } : {}
})

function isActive(path) {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}
</script>

<style>
.tabs { display: flex; gap: .5rem; margin-bottom: 1rem; align-items: center; }
.tabs > a { padding: .4rem 1rem; border: 1px solid #ddd; background: #f5f5f5; border-radius: 6px; cursor: pointer; text-decoration: none; color: #333; }
.tabs > a.active { background: #007bff; color: white; border-color: #007bff; }
.header-controls { display: flex; align-items: center; gap: 1rem; margin-left: auto; }
.header-controls .control { display: flex; align-items: center; gap: .4rem; font-size: .9rem; }
.header-controls select { padding: .25rem .4rem; }
.fallback-chip { background: #eef6ff; border: 1px solid #b6d4fe; border-radius: 999px; padding: .1rem .5rem; }
.fallback-remove { border: none; background: none; cursor: pointer; padding: 0; color: #b71c1c; }
.tabs .docs-menu { position: relative; }
.tabs .docs-menu button { padding: .4rem 1rem; border: 1px solid #ddd; background: #f5f5f5; border-radius: 6px; cursor: pointer; }
.tabs .docs-dropdown { position: absolute; top: 110%; left: 0; background: white; border: 1px solid #ddd; border-radius: 6px; min-width: 16rem; box-shadow: 0 4px 12px rgba(0,0,0,.08); z-index: 10; display: flex; flex-direction: column; }
.tabs .docs-dropdown a { padding: .5rem .9rem; text-decoration: none; color: #333; }
.tabs .docs-dropdown a:hover { background: #f0f6ff; }
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 40rem; }
.panel { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
.row { display: flex; gap: .5rem; margin: .5rem 0; align-items: center; }
.field-name { font-weight: 600; display: inline-block; min-width: 6rem; }
label { min-width: 8rem; }
input { padding: .25rem .5rem; }
button { padding: .35rem .8rem; cursor: pointer; }
.error { color: #b00020; padding: .5rem 1rem; border: 1px solid #b00020; border-radius: 8px; }
ul { list-style: none; padding-left: 0; }
li { padding: .25rem 0; }
.alias-chip { display: inline-block; background: #eef6ff; border: 1px solid #b6d4fe; border-radius: 999px; padding: .1rem .6rem; margin-right: .35rem; }
.history { width: 100%; border-collapse: collapse; font-size: .9rem; }
.history td { border-top: 1px solid #eee; padding: .3rem .4rem; }
.revision-banner { background: #fff8e1; border: 1px solid #ffe082; border-radius: 6px; padding: .4rem .8rem; margin: .5rem 0; }
.diff-old { background: #fdecea; color: #b71c1c; text-decoration: line-through; padding: 0 .25rem; }
.diff-new { background: #e8f5e9; color: #1b5e20; padding: 0 .25rem; }
</style>
