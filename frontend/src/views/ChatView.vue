<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import api from '@/api/http'
import AppIcon from '@/components/AppIcon.vue'
import ChatField from '@/components/character/chat_field/ChatField.vue'
import { useUserStore } from '@/stores/user'
import type { Character } from '@/types/character'
import type { Friend } from '@/types/friend'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const character = ref<Character | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const actionMessage = ref('')
const friendActionPending = ref(false)
const suppressAutoSession = ref(false)
const conversationActionPending = ref(false)
const chatFieldKey = ref(0)

const characterId = computed(() => Number(route.params.characterId))
const isDemoMode = computed(() => !user.isAuthenticated)

const seedCharacterFromHistory = () => {
  const stateCharacter = window.history.state?.character as Character | undefined
  if (stateCharacter?.id === characterId.value) {
    character.value = stateCharacter
  }
}

const loadCharacter = async () => {
  loading.value = true
  errorMessage.value = ''
  actionMessage.value = ''
  suppressAutoSession.value = false

  seedCharacterFromHistory()

  try {
    const response = await api.get<{ character: Character }>(`/character/public/${characterId.value}/`)
    character.value = response.data.character
  } catch (error: unknown) {
    errorMessage.value = '角色信息加载失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    loading.value = false
  }
}

const ensureChatSession = async () => {
  if (!character.value || !user.isAuthenticated || character.value.friend_id || friendActionPending.value) return

  friendActionPending.value = true
  errorMessage.value = ''

  try {
    const response = await api.post<{ friend: Friend }>('/friend/get_or_create/', {
      character_id: character.value.id,
    })
    character.value = {
      ...character.value,
      friend_id: response.data.friend.id,
    }
  } catch (error: unknown) {
    errorMessage.value = '聊天会话初始化失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    friendActionPending.value = false
  }
}

const loginToChat = async () => {
  await router.push({
    name: 'login',
    query: { redirect: route.fullPath },
  })
}

const refreshChatField = () => {
  chatFieldKey.value += 1
}

const handleConversationReset = async () => {
  if (conversationActionPending.value) return

  if (isDemoMode.value) {
    const confirmMessage = '重置聊天窗口会清空当前演示对话。是否继续？'
    if (typeof window !== 'undefined' && !window.confirm(confirmMessage)) {
      return
    }

    errorMessage.value = ''
    actionMessage.value = '已清空当前演示对话。'
    refreshChatField()
    return
  }

  if (!character.value?.friend_id) return

  const confirmMessage = '重置聊天窗口会清空当前消息记录，但会保留这段关系记忆。是否继续？'

  if (typeof window !== 'undefined' && !window.confirm(confirmMessage)) {
    return
  }

  conversationActionPending.value = true
  errorMessage.value = ''
  actionMessage.value = ''

  try {
    const response = await api.post<{ detail: string }>('/friend/message/reset/', {
      friend_id: character.value.friend_id,
      mode: 'history',
    })
    actionMessage.value = response.data.detail
    refreshChatField()
  } catch (error: unknown) {
    errorMessage.value = '重置聊天窗口失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    conversationActionPending.value = false
  }
}

watch(characterId, () => {
  character.value = null
  void loadCharacter()
}, { immediate: true })

watch(
  () => [character.value?.id, character.value?.friend_id, user.isAuthenticated, suppressAutoSession.value] as const,
  async ([nextCharacterId, friendId, isAuthenticated, isSuppressed]) => {
    if (!nextCharacterId || friendId || !isAuthenticated || isSuppressed) return
    await ensureChatSession()
  },
  { immediate: true },
)

const backTarget = computed(() => {
  const from = window.history.state?.from
  return typeof from === 'string' && from ? from : '/'
})

const backgroundImageUrl = computed(() => character.value?.background_image || character.value?.photo || '')

const backgroundBackdropStyle = computed(() => {
  if (!backgroundImageUrl.value) return null

  return {
    backgroundImage: `url(${backgroundImageUrl.value})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
  }
})

const backgroundFigureStyle = computed(() => {
  if (!backgroundImageUrl.value) return null

  return {
    backgroundImage: `url(${backgroundImageUrl.value})`,
    backgroundSize: 'contain',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
  }
})
</script>

<template>
  <section class="relative min-h-[calc(100vh-74px)] overflow-x-hidden overflow-y-visible bg-[#f7f7f8]">
    <div class="pointer-events-none absolute inset-0">
      <template v-if="backgroundBackdropStyle">
        <div
          class="absolute inset-0 scale-[1.06] opacity-[0.22] blur-2xl"
          :style="backgroundBackdropStyle"
        />
        <div
          class="absolute right-[-2%] top-1/2 hidden h-[68vh] max-h-[760px] w-[38vw] max-w-[540px] -translate-y-1/2 opacity-[0.42] md:block"
          :style="backgroundFigureStyle"
        />
        <div
          class="absolute inset-x-0 top-8 mx-auto h-[280px] w-[220px] opacity-[0.18] sm:h-[340px] sm:w-[260px] md:hidden"
          :style="backgroundFigureStyle"
        />
      </template>
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,214,170,0.28),transparent_34%),radial-gradient(circle_at_bottom_left,rgba(125,211,252,0.22),transparent_28%)]" />
      <div class="absolute inset-0 bg-[linear-gradient(180deg,rgba(247,247,248,0.82)_0%,rgba(247,247,248,0.54)_24%,rgba(247,247,248,0.3)_48%,rgba(247,247,248,0.52)_72%,rgba(247,247,248,0.84)_100%)]" />
    </div>

    <div class="relative mx-auto max-w-[1520px] px-4 py-4 sm:px-6 xl:px-8">
      <div class="xl:grid xl:grid-cols-[190px_minmax(760px,840px)_minmax(220px,1fr)] xl:items-start xl:gap-8">
        <div
          v-if="character"
          class="hidden xl:flex xl:flex-col xl:gap-4 xl:pt-2"
        >
          <div class="overflow-hidden rounded-[30px] border border-white/65 bg-white/58 p-4 shadow-[0_30px_90px_-42px_rgba(15,23,42,0.55)] backdrop-blur-2xl">
            <div class="relative overflow-hidden rounded-[24px] bg-[linear-gradient(145deg,rgba(255,255,255,0.9),rgba(240,244,255,0.72))]">
              <div
                v-if="character.photo"
                class="aspect-[4/5] w-full bg-cover bg-center"
                :style="{ backgroundImage: `url(${character.photo})` }"
              />
              <div
                v-else
                class="grid aspect-[4/5] w-full place-items-center bg-[linear-gradient(145deg,rgba(253,230,138,0.55),rgba(125,211,252,0.5))] text-4xl font-black text-base-content/65"
              >
                {{ character.name.slice(0, 1) }}
              </div>
              <div class="absolute inset-x-0 bottom-0 h-24 bg-[linear-gradient(180deg,rgba(255,255,255,0)_0%,rgba(255,255,255,0.82)_100%)]" />
            </div>

            <div class="mt-4">
              <p class="text-[10px] font-semibold uppercase tracking-[0.28em] text-base-content/35">
                Companion
              </p>
              <h2 class="mt-2 text-xl font-black tracking-tight text-base-content">
                {{ character.name }}
              </h2>
              <p class="mt-2 max-h-[78px] overflow-hidden text-sm leading-6 text-base-content/58">
                {{ character.profile || '已进入角色会话。' }}
              </p>
            </div>

            <div class="mt-4 flex flex-wrap gap-2">
              <span class="rounded-full bg-base-100/92 px-3 py-1 text-xs font-medium text-base-content/65 shadow-sm">
                {{ character.voice ? character.voice.name : '文本角色' }}
              </span>
              <span class="rounded-full bg-base-100/92 px-3 py-1 text-xs font-medium text-base-content/65 shadow-sm">
                {{ character.friend_id ? '已连接' : '待开始' }}
              </span>
            </div>

            <div class="mt-4 border-t border-white/60 pt-4 text-xs text-base-content/48">
              创作者 {{ character.author.display_name }}
            </div>
          </div>
        </div>

        <div class="flex min-w-0 flex-col gap-4 xl:col-start-2 xl:translate-x-10">
          <div class="flex w-full flex-wrap items-center justify-between gap-3 px-1 py-1">
            <div class="flex min-w-0 items-center gap-3 sm:gap-4">
              <RouterLink :to="backTarget" class="btn btn-ghost btn-sm rounded-full">
                <AppIcon name="home" icon-class="h-4 w-4" />
                返回
              </RouterLink>

              <template v-if="character">
                <div class="min-w-0">
                  <h1 class="truncate text-lg font-black sm:text-xl">{{ character.name }}</h1>
                </div>
              </template>
            </div>

            <div class="flex items-center gap-2">
              <template v-if="!user.isAuthenticated">
                <button
                  type="button"
                  class="btn btn-sm rounded-full"
                  @click="loginToChat"
                >
                  登录
                </button>
              </template>
              <button
                v-else-if="!character?.friend_id"
                type="button"
                class="btn btn-sm rounded-full"
                :disabled="friendActionPending || !user.isAuthenticated"
                @click="ensureChatSession"
              >
                {{ friendActionPending ? '处理中...' : '开始聊天' }}
              </button>
              <template v-else>
                <button
                  type="button"
                  class="btn btn-sm rounded-full"
                  :disabled="conversationActionPending"
                  @click="handleConversationReset"
                >
                  {{ conversationActionPending ? '处理中...' : '重置聊天窗口' }}
                </button>
              </template>
            </div>
          </div>

          <div v-if="errorMessage" class="alert alert-error border-0 shadow-lg">
            {{ errorMessage }}
          </div>

          <div v-if="actionMessage" class="alert alert-success border-0 shadow-lg">
            {{ actionMessage }}
          </div>

          <div
            v-if="loading"
            class="grid min-h-[60vh] place-items-center rounded-[28px] border border-base-200 bg-base-100 text-base-content/55 shadow-sm"
          >
            正在加载角色聊天页...
          </div>

          <div v-else-if="!character" class="grid min-h-[60vh] place-items-center rounded-[28px] border border-base-200 bg-base-100 text-base-content/60 shadow-sm">
            当前角色不存在。
          </div>

          <div
            v-else
            class="flex h-[calc(100vh-92px)] min-h-[520px] w-full max-w-[760px] max-h-[920px] sm:min-h-[620px] xl:min-w-[760px] xl:max-w-[840px]"
          >
            <ChatField
              :key="chatFieldKey"
              :character="character"
              :pending="friendActionPending"
              :can-manage-friend="user.isAuthenticated"
              :demo-enabled="isDemoMode"
            />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
