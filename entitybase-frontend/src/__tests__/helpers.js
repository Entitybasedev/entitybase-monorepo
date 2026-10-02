// Shared test helpers for component tests.
import { token, userId, username } from '../auth.js'
import { logout } from '../auth.js'

// Mark the test as logged in against the real auth module.
export function loginState(id = 90001, name = 'tester') {
  token.value = 'test-token'
  userId.value = id
  username.value = name
}

export function logoutState() {
  logout()
}
