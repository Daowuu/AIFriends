import axios from 'axios'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const ACCOUNT_BASE_URL = '/api/user/account'
const PROFILE_BASE_URL = '/api/user/profile'

export type UserInfo = {
  id: number
  username: string
  display_name: string
  bio: string
  avatar: string
}

type AuthPayload = {
  access: string
  user: UserInfo
}

type Credentials = {
  username: string
  password: string
}

type RegisterPayload = Credentials & {
  password_confirm: string
}

let pullUserInfoPromise: Promise<void> | null = null

export const useUserStore = defineStore('user', () => {
  const accessToken = ref('')
  const userInfo = ref<UserInfo | null>(null)
  const hasPulledUserInfo = ref(false)

  const isAuthenticated = computed(() => Boolean(accessToken.value && userInfo.value))
  const displayName = computed(() => userInfo.value?.display_name || userInfo.value?.username || '游客')
  const avatarText = computed(() => displayName.value.slice(0, 1).toUpperCase())

  const getAuthHeaders = () => (
    accessToken.value
      ? { Authorization: `Bearer ${accessToken.value}` }
      : undefined
  )

  const setAuthPayload = (payload: AuthPayload) => {
    accessToken.value = payload.access
    userInfo.value = payload.user
  }

  const setAccessToken = (token: string) => {
    accessToken.value = token
  }

  const clearAuth = () => {
    accessToken.value = ''
    userInfo.value = null
  }

  const login = async (payload: Credentials) => {
    const response = await axios.post<AuthPayload>(
      `${ACCOUNT_BASE_URL}/login/`,
      payload,
      { withCredentials: true },
    )

    setAuthPayload(response.data)
    hasPulledUserInfo.value = true
  }

  const register = async (payload: RegisterPayload) => {
    const response = await axios.post<AuthPayload>(
      `${ACCOUNT_BASE_URL}/register/`,
      payload,
      { withCredentials: true },
    )

    setAuthPayload(response.data)
    hasPulledUserInfo.value = true
  }

  const refreshToken = async () => {
    const response = await axios.post<{ access: string }>(
      `${ACCOUNT_BASE_URL}/refresh_token/`,
      {},
      { withCredentials: true, timeout: 5000 },
    )

    setAccessToken(response.data.access)
    return response.data.access
  }

  const fetchUserInfo = async () => {
    const response = await axios.get<{ user: UserInfo }>(
      `${ACCOUNT_BASE_URL}/get_user_info/`,
      {
        withCredentials: true,
        headers: getAuthHeaders(),
      },
    )

    userInfo.value = response.data.user
  }

  const pullUserInfo = async () => {
    if (!accessToken.value) {
      try {
        await refreshToken()
      } catch {
        clearAuth()
        hasPulledUserInfo.value = true
        return
      }
    }

    try {
      await fetchUserInfo()
    } catch {
      clearAuth()
    } finally {
      hasPulledUserInfo.value = true
    }
  }

  const ensureUserLoaded = async () => {
    if (hasPulledUserInfo.value) return

    if (!pullUserInfoPromise) {
      pullUserInfoPromise = pullUserInfo().finally(() => {
        pullUserInfoPromise = null
      })
    }

    await pullUserInfoPromise
  }

  const logout = async () => {
    try {
      await axios.post(
        `${ACCOUNT_BASE_URL}/logout/`,
        {},
        { withCredentials: true },
      )
    } finally {
      clearAuth()
      hasPulledUserInfo.value = true
    }
  }

  const updateProfile = async (payload: FormData) => {
    const response = await axios.post<{ user: UserInfo }>(
      `${PROFILE_BASE_URL}/update/`,
      payload,
      {
        withCredentials: true,
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'multipart/form-data',
        },
      },
    )

    userInfo.value = response.data.user
    hasPulledUserInfo.value = true
  }

  return {
    accessToken,
    userInfo,
    hasPulledUserInfo,
    isAuthenticated,
    displayName,
    avatarText,
    setAccessToken,
    clearAuth,
    login,
    register,
    refreshToken,
    fetchUserInfo,
    pullUserInfo,
    ensureUserLoaded,
    logout,
    updateProfile,
  }
})
