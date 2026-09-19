import { Role, UserPublic } from '@/types'

export type { Role, UserPublic }

const TOKEN_KEY = 'campusiq_token'
const USER_KEY = 'campusiq_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getUser(): UserPublic | null {
  const data = localStorage.getItem(USER_KEY)
  return data ? JSON.parse(data) : null
}

export function setUser(user: UserPublic): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function removeUser(): void {
  localStorage.removeItem(USER_KEY)
}

export function isAuthenticated(): boolean {
  return getToken() !== null
}

export function getRole(): Role | null {
  const user = getUser()
  return user?.role ?? null
}

export function logout(): void {
  removeToken()
  removeUser()
}

export function login(token: string, user: UserPublic): void {
  setToken(token)
  setUser(user)
}
