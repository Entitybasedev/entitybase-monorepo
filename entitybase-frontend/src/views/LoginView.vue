<template>
  <section class="panel" data-testid="login-section">
    <h2>{{ mode === 'login' ? 'Log in' : 'Register' }}</h2>
    <form class="auth-form" data-testid="login-form" @submit.prevent="submit">
      <div class="row">
        <label for="username-input">Username</label>
        <input
          id="username-input"
          v-model="user"
          data-testid="username-input"
          autocomplete="username"
        />
      </div>
      <div class="row">
        <label for="password-input">Password</label>
        <input
          id="password-input"
          v-model="password"
          data-testid="password-input"
          type="password"
          autocomplete="current-password"
        />
      </div>
      <button type="submit" :disabled="busy" data-testid="login-submit">
        {{ busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Register' }}
      </button>
    </form>
    <p>
      <a
        href="#"
        data-testid="login-toggle-mode"
        @click.prevent="toggleMode"
      >{{
        mode === 'login'
          ? 'No account yet? Register'
          : 'Already registered? Log in'
      }}</a>
    </p>
    <section v-if="error" class="error" data-testid="login-error">{{ error }}</section>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, register } from '../auth.js'

const router = useRouter()
const mode = ref('login')
const user = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  busy.value = true
  error.value = ''
  try {
    if (mode.value === 'login') {
      await login(user.value, password.value)
    } else {
      await register(user.value, password.value)
    }
    await router.push('/')
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
}
</script>

<style>
.auth-form { display: flex; flex-direction: column; gap: .5rem; }
.auth-form .row input { flex: 1; }
</style>
