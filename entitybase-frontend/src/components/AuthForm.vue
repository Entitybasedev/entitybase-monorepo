<template>
  <section class="card card-body mb-3" data-testid="auth-section">
    <h2>{{ mode === 'login' ? 'Log in' : 'Register' }}</h2>
    <form class="auth-form" data-testid="auth-form" @submit.prevent="submit">
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
      <button type="submit" :disabled="busy" data-testid="auth-submit">
        {{ busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Register' }}
      </button>
    </form>
    <p>
      <router-link
          v-if="mode === 'login'"
          data-testid="auth-switch-link"
          to="/register"
      >
        No account yet? Register
      </router-link>
      <router-link
          v-else
          data-testid="auth-switch-link"
          to="/login"
      >
        Already registered? Log in
      </router-link>
    </p>
    <section v-if="error" class="alert alert-danger" data-testid="auth-error">{{ error }}</section>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, register } from '../auth.js'

const props = defineProps({
  mode: {
    type: String,
    default: 'login',
    validator: (value) => ['login', 'register'].includes(value),
  },
})

const router = useRouter()
const user = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  busy.value = true
  error.value = ''
  try {
    if (props.mode === 'login') {
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
</script>

<style>
.auth-form { display: flex; flex-direction: column; gap: .5rem; }
.auth-form .row input { flex: 1; }
</style>
