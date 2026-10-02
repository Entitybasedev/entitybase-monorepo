<template>
  <div class="dropdown" data-testid="user-menu">
    <template v-if="isLoggedIn">
      <button
        class="btn btn-outline-secondary btn-sm dropdown-toggle"
        data-testid="user-menu-button"
        data-bs-toggle="dropdown"
      >
        {{ username }}
      </button>
      <ul class="dropdown-menu dropdown-menu-end" data-testid="user-dropdown">
        <li>
          <router-link
            class="dropdown-item"
            data-testid="user-menu-settings"
            :to="`/${userId}/settings`"
          >
            Settings
          </router-link>
        </li>
        <li>
          <button class="dropdown-item" data-testid="user-menu-logout" @click="doLogout">
            Log out
          </button>
        </li>
      </ul>
    </template>
    <template v-else>
      <router-link class="btn btn-primary btn-sm" data-testid="user-menu-login" to="/login">
        Log in
      </router-link>
      <router-link class="btn btn-outline-primary btn-sm" data-testid="user-menu-register" to="/register">
        Register
      </router-link>
    </template>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { isLoggedIn, logout, userId, username } from '../auth.js'

const router = useRouter()

function doLogout() {
  logout()
  router.push('/')
}
</script>
