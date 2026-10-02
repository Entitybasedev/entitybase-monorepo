<template>
  <nav class="navbar navbar-expand-lg bg-body-tertiary border-bottom" data-testid="nav">
    <div class="container-fluid">
      <router-link class="navbar-brand fw-bold" to="/">Entitybase</router-link>

      <ul class="navbar-nav me-auto d-flex flex-row gap-2">
        <li class="nav-item">
          <router-link
            class="nav-link"
            :class="{ active: isActive('/list') }"
            data-testid="nav-list"
            to="/list"
          >
            Entity list
          </router-link>
        </li>
        <li class="nav-item">
          <router-link
            class="nav-link"
            :class="{ active: isActive('/list-users') }"
            data-testid="nav-users"
            to="/list-users"
          >
            Users
          </router-link>
        </li>
        <li class="nav-item">
          <router-link
            class="nav-link"
            :class="{ active: isActive('/recent') }"
            data-testid="nav-recent"
            to="/recent"
          >
            Recent changes
          </router-link>
        </li>
        <li class="nav-item">
          <router-link
            class="nav-link"
            :class="{ active: isActive('/stream') }"
            data-testid="nav-stream"
            to="/stream"
          >
            Change stream
          </router-link>
        </li>
      </ul>

      <div class="d-flex align-items-center gap-3">
        <div class="dropdown">
          <button
            class="btn btn-outline-secondary btn-sm dropdown-toggle"
            data-testid="nav-create"
            data-bs-toggle="dropdown"
          >
            Create
          </button>
          <ul class="dropdown-menu" data-testid="create-menu">
            <li>
              <router-link
                class="dropdown-item"
                data-testid="create-menu-item"
                to="/create-item"
              >
                Create item
              </router-link>
            </li>
            <li>
              <router-link
                class="dropdown-item"
                data-testid="create-menu-property"
                to="/create-property"
              >
                Create property
              </router-link>
            </li>
            <li>
              <router-link
                class="dropdown-item"
                data-testid="create-menu-lexeme"
                to="/create-lexeme"
              >
                Create lexeme
              </router-link>
            </li>
          </ul>
        </div>

        <div class="dropdown">
          <button
            class="btn btn-outline-secondary btn-sm dropdown-toggle"
            data-testid="nav-docs"
            data-bs-toggle="dropdown"
          >
            Docs
          </button>
          <ul class="dropdown-menu" data-testid="docs-dropdown">
            <li>
              <a
                class="dropdown-item"
                href="https://entitybasedev.github.io/entitybase-monorepo/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Documentation ↗
              </a>
            </li>
            <li>
              <a class="dropdown-item" href="/docs" target="_blank" rel="noopener noreferrer">
                API docs (entitybase) ↗
              </a>
            </li>
            <li>
              <a
                class="dropdown-item"
                href="http://localhost:8888/docs"
                target="_blank"
                rel="noopener noreferrer"
              >
                API docs (change stream) ↗
              </a>
            </li>
          </ul>
        </div>

        <UserMenu />
      </div>
    </div>
  </nav>

  <div class="container-fluid py-3">
    <router-view />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import UserMenu from './components/UserMenu.vue'

const route = useRoute()

function isActive(path) {
  return route.path.startsWith(path)
}
</script>

<style>
/* Keep rows compact inside panels */
.panel .row { display: flex; gap: .5rem; margin: .5rem 0; align-items: center; }
.panel .field-name { font-weight: 600; display: inline-block; min-width: 6rem; }
.panel label { min-width: 8rem; }
.history td { vertical-align: middle; }
.diff-old { background: #fdecea; color: #b71c1c; text-decoration: line-through; padding: 0 .25rem; }
.diff-new { background: #e8f5e9; color: #1b5e20; padding: 0 .25rem; }
.alias-chip { display: inline-block; background: #eef6ff; border: 1px solid #b6d4fe; border-radius: 999px; padding: .1rem .6rem; margin-right: .35rem; }
.fallback-chip { background: #eef6ff; border: 1px solid #b6d4fe; border-radius: 999px; padding: .1rem .5rem; }
.fallback-remove { border: none; background: none; cursor: pointer; padding: 0; color: #b71c1c; }
</style>
