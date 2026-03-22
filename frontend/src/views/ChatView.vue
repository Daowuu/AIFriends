<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import api from '@/api/http'
import AppIcon from '@/components/AppIcon.vue'
import ChatField from '@/components/character/chat_field/ChatField.vue'
import type { Character } from '@/types/character'

const route = useRoute()

const character = ref<Character | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const actionMessage = ref('')
const conversationActionPending = ref(false)
const chatFieldKey = ref(0)

const characterId = computed(() => Number(route.params.characterId))

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

const refreshChatField = () => {
  chatFieldKey.value += 1
}

const handleConversationReset = async () => {
  if (!character.value?.id || conversationActionPending.value) return

  if (typeof window !== 'undefined' && !window.confirm('重置聊天窗口会清空当前消息记录，但会保留这段会话记忆。是否继续？')) {
    return
  }

  conversationActionPending.value = true
  errorMessage.value = ''
  actionMessage.value = ''

  try {
    const response = await api.post<{ detail: string }>('/session/reset/', {
      character_id: character.value.id,
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
        <div class="absolute inset-0 scale-[1.06] opacity-[0.22] blur-2xl" :style="backgroundBackdropStyle" />
        <div class="absolute inset-x-0 top-8 mx-auto h-[280px] w-[220px] opacity-[0.18] sm:h-[340px] sm:w-[260px] md:hidden" :style="backgroundFigureStyle" />
      </template>
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,214,170,0.28),transparent_34%),radial-gradient(circle_at_bottom_left,rgba(125,211,252,0.22),transparent_28%)]" />
      <div class="absolute inset-0 bg-[linear-gradient(180deg,rgba(247,247,248,0.82)_0%,rgba(247,247,248,0.54)_24%,rgba(247,247,248,0.3)_48%,rgba(247,247,248,0.52)_72%,rgba(247,247,248,0.84)_100%)]" />
    </div>

    <div class="relative mx-auto w-full max-w-[108rem] px-4 py-4 sm:px-5 xl:px-6">
      <div class="xl:grid xl:grid-cols-[minmax(9.75rem,0.62fr)_minmax(40rem,1.84fr)_minmax(18rem,1fr)] xl:items-start xl:gap-6 2xl:grid-cols-[minmax(10.25rem,0.66fr)_minmax(42rem,1.9fr)_minmax(19rem,1fr)] 2xl:gap-7">
        <div v-if="character" class="hidden xl:flex xl:flex-col xl:items-end xl:gap-4 xl:pt-10">
          <div class="w-full max-w-[10.75rem] xl:translate-x-1 2xl:translate-x-2 overflow-hidden rounded-[26px] border border-white/65 bg-white/58 p-3 shadow-[0_26px_70px_-42px_rgba(15,23,42,0.5)] backdrop-blur-2xl">
            <div class="relative overflow-hidden rounded-[24px] bg-[linear-gradient(145deg,rgba(255,255,255,0.9),rgba(240,244,255,0.72))]">
              <div v-if="character.photo" class="aspect-[11/14] w-full bg-cover bg-center" :style="{ backgroundImage: `url(${character.photo})` }" />
              <div v-else class="grid aspect-[11/14] w-full place-items-center bg-[linear-gradient(145deg,rgba(253,230,138,0.55),rgba(125,211,252,0.5))] text-4xl font-black text-base-content/65">
                {{ character.name.slice(0, 1) }}
              </div>
              <div class="absolute inset-x-0 bottom-0 h-24 bg-[linear-gradient(180deg,rgba(255,255,255,0)_0%,rgba(255,255,255,0.82)_100%)]" />
            </div>

            <div class="mt-3">
              <p class="text-[10px] font-semibold uppercase tracking-[0.28em] text-base-content/35">Session</p>
              <h2 class="mt-2 text-[1.05rem] font-black tracking-tight text-base-content">{{ character.name }}</h2>
              <p class="mt-2 max-h-[64px] overflow-hidden text-[12px] leading-5 text-base-content/58">
                {{ character.profile || '已进入角色会话。' }}
              </p>
            </div>

            <div class="mt-3 flex flex-wrap gap-2">
              <span class="rounded-full bg-base-100/92 px-2.5 py-1 text-[11px] font-medium text-base-content/65 shadow-sm">
                {{ character.voice ? character.voice.name : '文本角色' }}
              </span>
              <span class="rounded-full bg-base-100/92 px-2.5 py-1 text-[11px] font-medium text-base-content/65 shadow-sm">
                {{ character.ai_config.memory_mode }}
              </span>
            </div>
          </div>
        </div>

        <div class="flex min-w-0 flex-col gap-4 xl:col-start-2">
          <div class="flex w-full flex-wrap items-center justify-between gap-3 px-1 py-1">
            <div class="flex min-w-0 items-center gap-3 sm:gap-4">
              <RouterLink :to="backTarget" class="btn btn-ghost btn-sm rounded-full">
                <AppIcon name="home" icon-class="h-4 w-4" />
                返回
              </RouterLink>

              <template v-if="character">
                <div class="min-w-0">
                  <h1 class="truncate text-xl font-black tracking-tight text-base-content sm:text-2xl">
                    {{ character.name }}
                  </h1>
                  <p class="mt-1 truncate text-xs font-medium text-base-content/45">
                    {{ character.voice?.name || '文本角色' }} · {{ character.ai_config.reply_style }} · {{ character.ai_config.memory_mode }}
                  </p>
                </div>
              </template>
            </div>

            <div class="flex items-center gap-2">
              <button
                type="button"
                class="btn btn-ghost btn-sm rounded-full border border-base-300 bg-white/72"
                :disabled="conversationActionPending || !character"
                @click="handleConversationReset"
              >
                重置聊天窗口
              </button>
              <RouterLink to="/studio" class="btn btn-ghost btn-sm rounded-full border border-base-300 bg-white/72">
                打开 Studio
              </RouterLink>
            </div>
          </div>

          <div v-if="actionMessage" class="rounded-2xl border border-success/20 bg-success/5 px-4 py-3 text-sm text-success">
            {{ actionMessage }}
          </div>
          <div v-if="errorMessage" class="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">
            {{ errorMessage }}
          </div>

          <div class="min-h-[68vh] lg:h-[clamp(39rem,calc(100vh-11.5rem),50rem)] lg:min-h-[39rem] lg:max-h-[50rem]">
            <div v-if="loading" class="grid h-full place-items-center rounded-[28px] border border-base-200 bg-base-100 shadow-sm">
              正在加载角色会话...
            </div>
            <ChatField
              v-else
              :key="chatFieldKey"
              :character="character"
            />
          </div>
        </div>

        <div v-if="character && backgroundFigureStyle" class="hidden xl:flex xl:min-h-[70vh] xl:items-center xl:justify-center xl:pt-8">
          <div class="relative h-[clamp(33rem,72vh,50rem)] w-[min(100%,28rem)] min-w-[17.5rem]">
            <div class="absolute inset-0 rounded-[42px] bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.26),rgba(255,255,255,0.03)_56%,transparent_78%)]" />
            <div
              class="absolute inset-0 scale-[1.05] rounded-[42px] bg-contain bg-center bg-no-repeat opacity-[0.16] blur-lg"
              :style="backgroundFigureStyle"
            />
            <div
              class="absolute inset-0 rounded-[42px] bg-contain bg-center bg-no-repeat opacity-[0.46] saturate-[0.9] drop-shadow-[0_22px_42px_rgba(15,23,42,0.10)]"
              :style="backgroundFigureStyle"
            />
            <div class="absolute inset-0 rounded-[42px] bg-[linear-gradient(90deg,rgba(247,247,248,0.22)_0%,rgba(247,247,248,0.08)_24%,rgba(247,247,248,0.02)_52%,rgba(247,247,248,0.18)_100%)]" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
