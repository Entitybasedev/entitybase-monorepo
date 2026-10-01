<template>
  <div class="user-menu" data-testid="user-menu">
    <template v-if="isLoggedIn">
      <button data-testid="user-menu-button" @click="open = !open">
        {{ username }} ▾
      </button>
      <div v-if="open" class="user-dropdown" data-testid="user-dropdown">
        <router-link
          data-testid="user-menu-settings"
          :to="`/${userId}/settings`"
          @click="open = false"
        >
          Settings
        </router-link>
        <button data-testid="user-menu-logout" @click="doLogout">Log out</button>
      </div>
    </template>
    <template v-else>
      <router-link class="login-link" data-testid="user-menu-login" to="/login">
        Log in
      </router-link>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { isLoggedIn, logout, userId, username } from '../auth.js'

const open = ref(false)
const router = useRouter()

function doLogout() {
  open.value = false
  logout()
  router.push('/')
}
</script>

<style>
.user-menu { position: relative; }
.user-menu button, .user-menu .login-link {
  padding: .4rem 1rem;
  border: 1px solid #ddd;
  background: #f5f5f5;
  border-radius: 6px;
  cursor: pointer;
  text-decoration: none;
  color: #333;
}
.user-dropdown {
  position: absolute;
  top: 110%;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  min-width: 10rem;
  box-shadow: 0 4px 12px rgba(0,0,0,.08);
  z-index: 10;
  display: flex;
  flex-direction: column;
}
.user-dropdown a, .user-dropdown button {
  padding: .5rem .9rem;
  text-align: left;
  text-decoration: none;
  color: #333;
  border: none;
  background: none;
  cursor: pointer;
}
.user-dropdown a:hover, .user-dropdown button:hover { background: #f0f6ff; }
</style>
