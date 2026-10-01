<template>
  <section class="panel" data-testid="create-lexeme-section">
    <h2>Create lexeme</h2>
    <div class="row">
      <label for="lemma-input">Lemma (en)</label>
      <input id="lemma-input" v-model="lemma" data-testid="lemma-input" placeholder="answer" />
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
    <div v-if="!isLoggedIn" class="row">
      <label for="user-id-input">User ID</label>
      <input id="user-id-input" v-model.number="userId" data-testid="user-id-input" type="number" />
    </div>
    <button
      :disabled="!lemma || creatingLexeme"
      data-testid="create-lexeme-button"
      @click="createLexeme"
    >
      {{ creatingLexeme ? 'Creating…' : 'Create lexeme' }}
    </button>
    <section v-if="error" class="error" data-testid="error-banner">{{ error }}</section>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { postLexeme } from '../api.js'
import { isLoggedIn, userId as authUserId } from '../auth.js'

const router = useRouter()
const userId = ref(authUserId.value || 90001)
const lemma = ref('')
const lexemeLanguage = ref('Q1860')
const lexemeCategory = ref('Q1084')
const creatingLexeme = ref(false)
const error = ref('')

async function createLexeme() {
  creatingLexeme.value = true
  error.value = ''
  try {
    const entityId = await postLexeme(
      {
        type: 'lexeme',
        lemmas: { en: { language: 'en', value: lemma.value } },
        language: lexemeLanguage.value,
        lexical_category: lexemeCategory.value,
      },
      userId.value
    )
    await router.push({ path: '/', query: { entity: entityId } })
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    creatingLexeme.value = false
  }
}
</script>
