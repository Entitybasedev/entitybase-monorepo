const API_URL = process.env.API_URL || 'http://localhost:8083'
const USER_ID = Number(process.env.E2E_USER_ID || 90001)

export async function registerUser() {
  const res = await fetch(`${API_URL}/v1/users`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Edit-Summary': 'e2e setup',
      'X-User-ID': String(USER_ID),
    },
    body: JSON.stringify({ user_id: USER_ID }),
  })
  // Idempotent: 409/400 for already-existing user is fine.
  if (!res.ok && res.status !== 400 && res.status !== 409) {
    throw new Error(`Registering user ${USER_ID} failed: ${res.status} ${await res.text()}`)
  }
}

export default async function globalSetup() {
  await registerUser()
}
