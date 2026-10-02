<template>
  <section class="card card-body mb-3" data-testid="create-lexeme-section">
    <h2>Create lexeme</h2>
    <section v-if="!isLoggedIn" class="login-required" data-testid="login-required">
      <p>You need to log in to create entities.</p>
      <router-link to="/login" data-testid="login-required-link">Log in</router-link>
    </section>
    <template v-else>
    <form @submit.prevent="createLexeme">
      <div class="row">
        <label for="lemma-input">Lemma</label>
        <select
          class="form-select form-select-sm"
          style="width: auto"
          data-testid="lemma-lang-select"
          v-model="lemmaLanguage"
        >
          <option v-for="l in SUPPORTED_LANGUAGES" :key="l.code" :value="l.code">
            {{ l.code }}
          </option>
        </select>
        <input id="lemma-input" v-model="lemma" data-testid="lemma-input" placeholder="answer" @keyup.enter="createLexeme" />
      </div>
      <div class="row">
        <label for="lexeme-language-input">Language QID</label>
        <input
          id="lexeme-language-input"
          v-model="lexemeLanguage"
          data-testid="lexeme-language-input"
          placeholder="Q1860"
        />
      </div>
      <div class="row">
        <label for="lexeme-category-input">Lexical category QID</label>
        <input
          id="lexeme-category-input"
          v-model="lexemeCategory"
          data-testid="lexeme-category-input"
          placeholder="Q1084"
        />
      </div>
      <button type="submit" class="btn btn-primary btn-sm"
        :disabled="!lemma || creatingLexeme"
        data-testid="create-lexeme-button"
        @click="createLexeme"
      >
        {{ creatingLexeme ? 'Creating…' : 'Create lexeme' }}
      </button>
    </form>
    </template>
    <section v-if="error" class="alert alert-danger" data-testid="error-banner">{{ error }}</section>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { postLexeme } from '../api.js'
import { SUPPORTED_LANGUAGES, language } from '../settings.js'
import { isLoggedIn } from '../auth.js'

const router = useRouter()
const lemma = ref('')
const lemmaLanguage = ref(language.value)
const lexemeLanguage = ref('Q1860')
const lexemeCategory = ref('Q1084')
const creatingLexeme = ref(false)
const error = ref('')

async function createLexeme() {
  if (creatingLexeme.value) return
  creatingLexeme.value = true
  error.value = ''
  try {
    const entityId = await postLexeme({
      type: 'lexeme',
      lemmas: {
        [lemmaLanguage.value]: {
          language: lemmaLanguage.value,
          value: lemma.value,
        },
      },
      language: lexemeLanguage.value,
      lexical_category: lexemeCategory.value,
    })
    await router.push(`/entity/${entityId}`)
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creatingLexeme.value = false
  }
}
</script>
