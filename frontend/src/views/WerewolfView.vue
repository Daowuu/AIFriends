<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '@/api/http'
import AppIcon from '@/components/AppIcon.vue'
import MarkdownContent from '@/components/MarkdownContent.vue'
import type { Character } from '@/types/character'
import type { WerewolfDraftSeat, WerewolfGame, WerewolfGameDetail } from '@/types/werewolf'

const route = useRoute()
const router = useRouter()

const createEmptyCustomSeat = (id: string): WerewolfDraftSeat => ({
  id,
  source_type: 'custom',
  character_id: null,
  display_name: '',
  profile: '',
  custom_prompt: '',
})

const characters = ref<Character[]>([])
const games = ref<WerewolfGame[]>([])
const currentGame = ref<WerewolfGameDetail | null>(null)
const loading = ref(true)
const createPending = ref(false)
const actionPending = ref(false)
const errorMessage = ref('')
const observerNote = ref('')

const gameTitle = ref('爱莉希雅的狼人杀实验局')
const selectedCharacterIds = ref<number[]>([])
const customSeats = ref<WerewolfDraftSeat[]>([
  createEmptyCustomSeat('custom-1'),
])

const selectedGameId = computed<number | null>(() => {
  const rawValue = Number(route.params.gameId || 0)
  return Number.isFinite(rawValue) && rawValue > 0 ? rawValue : null
})

const selectedCharacters = computed(() => (
  selectedCharacterIds.value
    .map((characterId) => characters.value.find((character) => character.id === characterId) || null)
    .filter(Boolean) as Character[]
)

const normalizedCustomSeats = computed(() => customSeats.value.filter((seat) => seat.display_name.trim()))
const totalSelectedSeats = computed(() => selectedCharacterIds.value.length + normalizedCustomSeats.value.length)
const rosterReady = computed(() => totalSelectedSeats.value === 5)
const remainingSeatCount = computed(() => Math.max(0, 5 - totalSelectedSeats.value))

const aliveSeats = computed(() => currentGame.value?.seats.filter((seat) => seat.is_alive) || [])
const eliminatedSeats = computed(() => currentGame.value?.seats.filter((seat) => !seat.is_alive) || [])
const publicSpeeches = computed(() => currentGame.value?.speeches.filter((speech) => speech.audience === 'public') || [])

const currentPhaseSummary = computed(() => {
  if (!currentGame.value) {
    return {
      title: '还没有狼人杀房间',
      detail: '先从角色库中选 5 个席位，建一局基础狼人杀。',
    }
  }

  const { game } = currentGame.value
  if (game.status === 'finished') {
    return {
      title: '对局已结束',
      detail: game.winner_label || '本局已经完成，可以回看事件流或重置房间。',
    }
  }

  return {
    title: `${game.phase_label} · 第 ${Math.max(game.day_number, 1)} 天 / 第 ${game.night_number} 夜`,
    detail: game.phase === 'setup'
      ? '房间已建好，点击“推进下一阶段”开始夜晚。'
      : '系统主持会按夜晚、白天发言、投票的顺序推进。',
  }
})

const loadCharacters = async () => {
  const response = await api.get<{ characters: Character[] }>('/character/list/')
  characters.value = response.data.characters
}

const loadGames = async () => {
  const response = await api.get<{ games: WerewolfGame[] }>('/werewolf/games/')
  games.value = response.data.games
}

const loadGameDetail = async (gameId: number) => {
  const response = await api.get<WerewolfGameDetail>(`/werewolf/games/${gameId}/`)
  currentGame.value = response.data
  observerNote.value = response.data.game.observer_note || ''
}

const loadInitialData = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    await Promise.all([loadCharacters(), loadGames()])
    if (selectedGameId.value) {
      await loadGameDetail(selectedGameId.value)
    } else if (games.value[0]) {
      await router.replace({ name: 'werewolf-detail', params: { gameId: games.value[0].id } })
    }
  } catch (error: unknown) {
    errorMessage.value = '狼人杀页面加载失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    loading.value = false
  }
}

const toggleCharacterSeat = (characterId: number) => {
  if (createPending.value || actionPending.value) return
  if (selectedCharacterIds.value.includes(characterId)) {
    selectedCharacterIds.value = selectedCharacterIds.value.filter((id) => id !== characterId)
    return
  }
  if (totalSelectedSeats.value >= 5) return
  selectedCharacterIds.value = [...selectedCharacterIds.value, characterId]
}

const addCustomSeat = () => {
  customSeats.value.push(createEmptyCustomSeat(`custom-${Date.now()}-${customSeats.value.length}`))
}

const removeCustomSeat = (seatId: string) => {
  if (customSeats.value.length === 1) {
    customSeats.value = [createEmptyCustomSeat(customSeats.value[0]?.id || 'custom-1')]
    return
  }
  customSeats.value = customSeats.value.filter((seat) => seat.id !== seatId)
}

const createGame = async () => {
  if (!rosterReady.value || createPending.value) return
  createPending.value = true
  errorMessage.value = ''
  try {
    const response = await api.post<WerewolfGameDetail>('/werewolf/games/create/', {
      title: gameTitle.value,
      character_ids: selectedCharacterIds.value,
      custom_seats: normalizedCustomSeats.value.map((seat) => ({
        display_name: seat.display_name,
        profile: seat.profile,
        custom_prompt: seat.custom_prompt,
      })),
    })
    currentGame.value = response.data
    await loadGames()
    selectedCharacterIds.value = []
    customSeats.value = [createEmptyCustomSeat('custom-1')]
    await router.push({ name: 'werewolf-detail', params: { gameId: response.data.game.id } })
  } catch (error: unknown) {
    errorMessage.value = '创建狼人杀房间失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    createPending.value = false
  }
}

const openGame = async (gameId: number) => {
  if (selectedGameId.value === gameId) return
  await router.push({ name: 'werewolf-detail', params: { gameId } })
}

const runGameAction = async (action: 'advance' | 'reset') => {
  if (!currentGame.value || actionPending.value) return
  actionPending.value = true
  errorMessage.value = ''
  try {
    const response = await api.post<WerewolfGameDetail>(
      `/werewolf/games/${currentGame.value.game.id}/${action}/`,
      action === 'advance' ? { observer_note: observerNote.value } : {},
    )
    currentGame.value = response.data
    await loadGames()
  } catch (error: unknown) {
    errorMessage.value = action === 'advance' ? '推进狼人杀阶段失败。' : '重置狼人杀房间失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    actionPending.value = false
  }
}

watch(selectedGameId, async (gameId) => {
  if (!gameId) {
    currentGame.value = null
    return
  }
  try {
    await loadGameDetail(gameId)
  } catch (error: unknown) {
    currentGame.value = null
    errorMessage.value = '加载狼人杀房间详情失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  }
}, { immediate: false })

onMounted(async () => {
  await loadInitialData()
})
</script>

<template>
  <section class="mx-auto w-full max-w-[104rem] px-4 py-6 sm:px-6 xl:px-8">
    <div class="mb-6 overflow-hidden rounded-[34px] border border-base-200 bg-base-100 shadow-sm">
      <div class="grid gap-6 p-7 xl:grid-cols-[minmax(0,1.2fr)_minmax(22rem,0.8fr)] xl:items-center">
        <div>
          <div class="inline-flex items-center rounded-full bg-base-200 px-3 py-1 text-xs font-black tracking-[0.22em] text-base-content/60">
            WEREWOLF MODE
          </div>
          <h1 class="mt-4 text-4xl font-black tracking-tight text-base-content">
            用角色库开一局基础狼人杀，系统主持自动推进。
          </h1>
          <p class="mt-3 max-w-3xl text-sm leading-7 text-base-content/60">
            这是一个观察者视角的原型模式。你负责建局、选席位、看流程；夜晚结算、白天发言、投票与胜负判断都由系统主持自动完成。
          </p>
        </div>

        <div class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          <div class="rounded-[28px] border border-base-200 bg-base-50 p-5">
            <div class="text-sm text-base-content/45">基础模板</div>
            <div class="mt-2 text-lg font-black">5 人局</div>
            <div class="mt-1 text-xs text-base-content/55">2 狼人 · 1 预言家 · 2 平民</div>
          </div>
          <div class="rounded-[28px] border border-base-200 bg-base-50 p-5">
            <div class="text-sm text-base-content/45">当前房间数</div>
            <div class="mt-2 text-3xl font-black">{{ games.length }}</div>
          </div>
          <div class="rounded-[28px] border border-base-200 bg-base-50 p-5">
            <div class="text-sm text-base-content/45">当前模式</div>
            <div class="mt-2 text-lg font-black">观察者 / 导演</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="alert alert-error mb-6">{{ errorMessage }}</div>

    <div
      v-if="loading"
      class="grid min-h-[22rem] place-items-center rounded-[32px] border border-base-200 bg-base-100 text-base-content/50 shadow-sm"
    >
      正在加载狼人杀工作台...
    </div>

    <div
      v-else
      class="grid gap-6 xl:grid-cols-[minmax(22rem,0.86fr)_minmax(0,1.44fr)]"
    >
      <div class="space-y-6">
        <section class="rounded-[30px] border border-base-200 bg-base-100 p-6 shadow-sm">
          <div class="flex items-center gap-3">
            <AppIcon name="game" icon-class="h-5 w-5" />
            <div>
              <h2 class="text-lg font-black">新建房间</h2>
              <p class="text-sm text-base-content/55">从角色库和临时席位中凑满 5 个席位。</p>
            </div>
          </div>

          <label class="mt-5 block">
            <div class="mb-2 text-sm font-bold text-base-content/75">房间标题</div>
            <input
              v-model="gameTitle"
              type="text"
              class="input input-bordered w-full rounded-2xl"
              placeholder="输入一局狼人杀的标题"
            >
          </label>

          <div class="mt-6">
            <div class="mb-3 flex items-center justify-between">
              <div class="text-sm font-bold text-base-content/75">角色库席位</div>
              <div class="text-xs text-base-content/50">已选 {{ selectedCharacterIds.length }} / 5</div>
            </div>
            <div class="grid gap-3">
              <button
                v-for="character in characters"
                :key="character.id"
                type="button"
                class="flex items-start gap-3 rounded-[22px] border px-4 py-4 text-left transition"
                :class="selectedCharacterIds.includes(character.id)
                  ? 'border-[#2b3a35] bg-[#f4f0e3] shadow-sm'
                  : 'border-base-200 bg-base-50 hover:bg-base-100'"
                @click="toggleCharacterSeat(character.id)"
              >
                <img
                  v-if="character.photo"
                  :src="character.photo"
                  :alt="character.name"
                  class="h-14 w-14 rounded-2xl object-cover"
                >
                <div
                  v-else
                  class="grid h-14 w-14 place-items-center rounded-2xl bg-base-200 text-xs font-black text-base-content/45"
                >
                  {{ character.name.slice(0, 1) }}
                </div>
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <div class="truncate text-sm font-black">{{ character.name }}</div>
                    <span class="rounded-full bg-base-200 px-2 py-0.5 text-[11px] font-bold text-base-content/60">
                      {{ character.ai_config.reply_style }}
                    </span>
                  </div>
                  <p class="mt-1 line-clamp-2 text-xs leading-5 text-base-content/55">
                    {{ character.profile || '暂无角色介绍。' }}
                  </p>
                </div>
              </button>
            </div>
          </div>

          <div class="mt-6">
            <div class="mb-3 flex items-center justify-between">
              <div class="text-sm font-bold text-base-content/75">临时席位</div>
              <button class="btn btn-sm btn-ghost rounded-full" type="button" @click="addCustomSeat">
                新增席位
              </button>
            </div>

            <div class="space-y-4">
              <div
                v-for="seat in customSeats"
                :key="seat.id"
                class="rounded-[24px] border border-base-200 bg-base-50 p-4"
              >
                <div class="mb-3 flex items-center justify-between">
                  <div class="text-sm font-black">自定义席位</div>
                  <button class="btn btn-xs btn-ghost rounded-full" type="button" @click="removeCustomSeat(seat.id)">
                    移除
                  </button>
                </div>
                <div class="grid gap-3">
                  <input
                    v-model="seat.display_name"
                    type="text"
                    class="input input-bordered w-full rounded-2xl"
                    placeholder="席位名字"
                  >
                  <textarea
                    v-model="seat.profile"
                    class="textarea textarea-bordered min-h-[92px] w-full rounded-2xl"
                    placeholder="席位设定"
                  />
                  <textarea
                    v-model="seat.custom_prompt"
                    class="textarea textarea-bordered min-h-[110px] w-full rounded-2xl"
                    placeholder="自定义 Prompt（可选）"
                  />
                </div>
              </div>
            </div>
          </div>

          <div class="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-base-200 bg-base-50 px-4 py-4">
            <div>
              <div class="text-sm font-black">当前席位数：{{ totalSelectedSeats }} / 5</div>
              <div class="text-xs text-base-content/55">
                <template v-if="remainingSeatCount > 0">
                  还差 {{ remainingSeatCount }} 个席位。
                </template>
                <template v-else>
                  已满足基础局人数，可以直接建局。
                </template>
              </div>
            </div>
            <button
              class="btn rounded-full px-6"
              :class="rosterReady ? 'btn-neutral' : 'btn-disabled'"
              :disabled="!rosterReady || createPending"
              @click="createGame"
            >
              {{ createPending ? '正在建局...' : '创建狼人杀房间' }}
            </button>
          </div>
        </section>

        <section class="rounded-[30px] border border-base-200 bg-base-100 p-6 shadow-sm">
          <div class="flex items-center gap-3">
            <AppIcon name="spark" icon-class="h-5 w-5" />
            <div>
              <h2 class="text-lg font-black">房间列表</h2>
              <p class="text-sm text-base-content/55">已创建的房间会保存在本地实例里，可随时恢复。</p>
            </div>
          </div>

          <div v-if="games.length === 0" class="mt-5 rounded-[24px] border border-dashed border-base-300 px-4 py-8 text-center text-sm text-base-content/50">
            还没有狼人杀房间。先从上面建一局。
          </div>

          <div v-else class="mt-5 space-y-3">
            <button
              v-for="game in games"
              :key="game.id"
              type="button"
              class="w-full rounded-[24px] border px-4 py-4 text-left transition"
              :class="selectedGameId === game.id
                ? 'border-[#2b3a35] bg-[#f4f0e3] shadow-sm'
                : 'border-base-200 bg-base-50 hover:bg-base-100'"
              @click="openGame(game.id)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="truncate text-base font-black">{{ game.title }}</div>
                  <div class="mt-1 text-xs text-base-content/55">
                    {{ game.phase_label }} · 第 {{ Math.max(game.day_number, 1) }} 天 / 第 {{ game.night_number }} 夜
                  </div>
                </div>
                <span class="rounded-full bg-base-200 px-3 py-1 text-[11px] font-bold text-base-content/60">
                  {{ game.status === 'finished' ? (game.winner_label || '已结束') : '进行中' }}
                </span>
              </div>
            </button>
          </div>
        </section>
      </div>

      <div class="space-y-6">
        <section class="rounded-[30px] border border-base-200 bg-base-100 p-6 shadow-sm">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div class="inline-flex rounded-full bg-base-200 px-3 py-1 text-xs font-black tracking-[0.2em] text-base-content/60">
                GAME STAGE
              </div>
              <h2 class="mt-3 text-2xl font-black">{{ currentGame?.game.title || '狼人杀房间详情' }}</h2>
              <p class="mt-2 text-sm leading-7 text-base-content/60">
                {{ currentPhaseSummary.title }}。{{ currentPhaseSummary.detail }}
              </p>
            </div>
            <div v-if="currentGame" class="flex flex-wrap gap-2">
              <button
                class="btn rounded-full"
                :disabled="actionPending || currentGame.game.status === 'finished'"
                @click="runGameAction('advance')"
              >
                {{ actionPending ? '处理中...' : '推进下一阶段' }}
              </button>
              <button
                class="btn btn-ghost rounded-full"
                :disabled="actionPending"
                @click="runGameAction('reset')"
              >
                重置房间
              </button>
            </div>
          </div>

          <div v-if="!currentGame" class="mt-6 rounded-[24px] border border-dashed border-base-300 px-4 py-12 text-center text-sm text-base-content/50">
            选择一个房间，或者先在左侧新建一局狼人杀。
          </div>

          <template v-else>
            <div class="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(20rem,0.9fr)]">
              <div class="rounded-[24px] border border-base-200 bg-base-50 p-4">
                <div class="text-sm font-black">席位与存活状态</div>
                <div class="mt-4 grid gap-3 sm:grid-cols-2">
                  <div
                    v-for="seat in currentGame.seats"
                    :key="seat.id"
                    class="rounded-[22px] border px-4 py-4"
                    :class="seat.is_alive ? 'border-base-200 bg-white' : 'border-base-200/70 bg-base-200/35 opacity-80'"
                  >
                    <div class="flex items-start gap-3">
                      <img
                        v-if="seat.photo"
                        :src="seat.photo"
                        :alt="seat.display_name"
                        class="h-14 w-14 rounded-2xl object-cover"
                      >
                      <div
                        v-else
                        class="grid h-14 w-14 place-items-center rounded-2xl bg-base-200 text-xs font-black text-base-content/45"
                      >
                        {{ seat.display_name.slice(0, 1) }}
                      </div>
                      <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-2">
                          <div class="truncate text-sm font-black">
                            {{ seat.seat_order }}号 · {{ seat.display_name }}
                          </div>
                          <span
                            class="rounded-full px-2 py-0.5 text-[11px] font-bold"
                            :class="seat.is_alive ? 'bg-emerald-100 text-emerald-700' : 'bg-base-200 text-base-content/55'"
                          >
                            {{ seat.is_alive ? '存活' : '出局' }}
                          </span>
                        </div>
                        <div class="mt-1 text-xs text-base-content/55">
                          {{ seat.identity_label }}
                          <span v-if="seat.is_revealed"> · 已翻牌</span>
                        </div>
                        <p class="mt-2 line-clamp-3 text-xs leading-5 text-base-content/55">
                          {{ seat.profile || '暂无角色简介。' }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="space-y-4">
                <div class="rounded-[24px] border border-base-200 bg-base-50 p-4">
                  <div class="text-sm font-black">对局摘要</div>
                  <div class="mt-4 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                    <div class="rounded-[20px] border border-base-200 bg-white px-4 py-3">
                      <div class="text-xs font-bold uppercase tracking-[0.14em] text-base-content/45">当前阶段</div>
                      <div class="mt-1 text-sm font-black">{{ currentGame.game.phase_label }}</div>
                    </div>
                    <div class="rounded-[20px] border border-base-200 bg-white px-4 py-3">
                      <div class="text-xs font-bold uppercase tracking-[0.14em] text-base-content/45">存活人数</div>
                      <div class="mt-1 text-sm font-black">{{ aliveSeats.length }}</div>
                    </div>
                    <div class="rounded-[20px] border border-base-200 bg-white px-4 py-3">
                      <div class="text-xs font-bold uppercase tracking-[0.14em] text-base-content/45">出局人数</div>
                      <div class="mt-1 text-sm font-black">{{ eliminatedSeats.length }}</div>
                    </div>
                  </div>
                </div>

                <div class="rounded-[24px] border border-base-200 bg-base-50 p-4">
                  <div class="text-sm font-black">观察者备注</div>
                  <textarea
                    v-model="observerNote"
                    class="textarea textarea-bordered mt-3 min-h-[110px] w-full rounded-2xl"
                    placeholder="给系统主持写一条备注。会在下次推进阶段时记进事件流。"
                  />
                </div>
              </div>
            </div>

            <div class="mt-6 grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
              <div class="rounded-[24px] border border-base-200 bg-base-50 p-4">
                <div class="flex items-center justify-between gap-3">
                  <div class="text-sm font-black">事件时间线</div>
                  <div class="text-xs text-base-content/50">{{ currentGame.events.length }} 条</div>
                </div>
                <div class="mt-4 space-y-3">
                  <div
                    v-for="event in currentGame.events"
                    :key="event.id"
                    class="rounded-[20px] border border-base-200 bg-white px-4 py-4"
                  >
                    <div class="flex flex-wrap items-center gap-2">
                      <div class="text-sm font-black">{{ event.title }}</div>
                      <span class="rounded-full bg-base-200 px-2 py-0.5 text-[11px] font-bold text-base-content/60">
                        {{ event.phase_label || '通用事件' }}
                      </span>
                    </div>
                    <p v-if="event.content" class="mt-2 text-sm leading-6 text-base-content/65">
                      {{ event.content }}
                    </p>
                  </div>
                </div>
              </div>

              <div class="rounded-[24px] border border-base-200 bg-base-50 p-4">
                <div class="flex items-center justify-between gap-3">
                  <div class="text-sm font-black">公开发言回放</div>
                  <div class="text-xs text-base-content/50">{{ publicSpeeches.length }} 段</div>
                </div>
                <div v-if="publicSpeeches.length === 0" class="mt-4 rounded-[20px] border border-dashed border-base-300 px-4 py-10 text-center text-sm text-base-content/50">
                  当前还没有公开发言。推进到白天发言阶段后会在这里展示。
                </div>
                <div v-else class="mt-4 space-y-4">
                  <article
                    v-for="speech in publicSpeeches"
                    :key="speech.id"
                    class="rounded-[20px] border border-base-200 bg-white px-4 py-4"
                  >
                    <div class="mb-3 flex flex-wrap items-center gap-2">
                      <div class="text-sm font-black">{{ speech.seat_name }}</div>
                      <span class="rounded-full bg-base-200 px-2 py-0.5 text-[11px] font-bold text-base-content/60">
                        {{ speech.phase_label }}
                      </span>
                      <span class="rounded-full bg-base-200 px-2 py-0.5 text-[11px] font-bold text-base-content/60">
                        第 {{ speech.day_number }} 天
                      </span>
                    </div>
                    <MarkdownContent :content="speech.content" />
                  </article>
                </div>
              </div>
            </div>
          </template>
        </section>
      </div>
    </div>
  </section>
</template>
