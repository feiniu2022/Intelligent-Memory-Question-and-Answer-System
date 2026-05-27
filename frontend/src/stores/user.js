import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { auth } from '../api/modules'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userId = ref(localStorage.getItem('userId') || '')
  const username = ref(localStorage.getItem('username') || '')

  const isLoggedIn = computed(() => !!token.value)

  async function login(user, pass) {
    const res = await auth.login(user, pass)
    token.value = res.data.access_token
    userId.value = String(res.data.user_id)
    username.value = res.data.username
    localStorage.setItem('token', token.value)
    localStorage.setItem('userId', userId.value)
    localStorage.setItem('username', username.value)
  }

  async function register(user, pass) {
    const res = await auth.register(user, pass)
    token.value = res.data.access_token
    userId.value = String(res.data.user_id)
    username.value = res.data.username
    localStorage.setItem('token', token.value)
    localStorage.setItem('userId', userId.value)
    localStorage.setItem('username', username.value)
  }

  function logout() {
    token.value = ''
    userId.value = ''
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    localStorage.removeItem('username')
  }

  return { token, userId, username, isLoggedIn, login, register, logout }
})