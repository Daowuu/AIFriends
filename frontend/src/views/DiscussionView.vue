<script setup lang="ts">
import axios from 'axios'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '@/api/http'
import AppIcon from '@/components/AppIcon.vue'
import MarkdownContent from '@/components/MarkdownContent.vue'
import type { Character } from '@/types/character'
import type { DiscussionEvent, DiscussionGroup, DiscussionGroupDetail, DiscussionSpeech } from '@/types/discussion'

const MIN_PARTICIPANTS = 2
const MAX_PARTICIPANTS = 8
const AUTO_ADVANCE_INTERVAL_MS = 2000
const DEMO_TITLE = '示例讨论：角色差异与流程约束'
const DEMO_TOPIC = '如果要让多角色讨论更像真实圆桌讨论，最该先改哪一层？'
const DEMO_CHARACTER_NAMES = ['爱莉希雅', '符华', '布洛妮娅']
const DEMO_MAX_ROUNDS = 2

const route = useRoute()
const router = useRouter()

const characters = ref<Character[]>([])
const groups = ref<DiscussionGroup[]>([])
const currentGroup = ref<DiscussionGroupDetail | null>(null)
const loading = ref(true)
const createPending = ref(false)
const actionPending = ref(false)
const errorMessage = ref('')
const observerNote = ref('')
const autoAdvanceEnabled = ref(true)

const groupTitle = ref('多角色讨论组')
const discussionTopic = ref('当 AI 角色进入同一个讨论组时，怎样避免内容同质化？')
const maxRounds = ref(2)
const selectedCharacterIds = ref<number[]>([])

const stageFlow = [
  { key: 'topic_opening', label: '开场' },
  { key: 'agenda_setup', label: '议题拆解' },
  { key: 'opening_turn', label: '角色立场' },
  { key: 'round_summary', label: '主持总结' },
  { key: 'focused_turn', label: '聚焦讨论' },
  { key: 'consensus_draft', label: '共识结论' },
  { key: 'final_response_turn', label: '异议补充' },
  { key: 'discussion_finish', label: '讨论完成' },
]

let autoAdvanceTimer: number | null = null

const selectedGroupId = computed<number | null>(() => {
  const rawValue = Number(route.params.groupId || 0)
  return Number.isFinite(rawValue) && rawValue > 0 ? rawValue : null
})

const selectedCount = computed(() => selectedCharacterIds.value.length)
const selectedModeratorName = computed(() => {
  const moderatorId = selectedCharacterIds.value[0]
  if (!moderatorId) return ''
  return characters.value.find((character) => character.id === moderatorId)?.name || ''
})
const rosterReady = computed(() => {
  const count = selectedCount.value
  return count >= MIN_PARTICIPANTS
    && count <= MAX_PARTICIPANTS
    && discussionTopic.value.trim().length > 0
})
const publicSpeeches = computed(() => currentGroup.value?.speeches.filter((speech) => speech.audience === 'public') || [])
const isModeratorSpeech = (speech: DiscussionSpeech) => Boolean(speech.metadata?.is_moderator_speech)
const stanceEntries = computed(() => {
  if (!currentGroup.value) return []
  return Object.values(currentGroup.value.stance_map || {})
})
const activeStageIndex = computed(() => {
  const currentStage = currentGroup.value?.group.current_stage || 'setup'
  const index = stageFlow.findIndex((item) => item.key === currentStage)
  return index >= 0 ? index : -1
})
const agendaItems = computed(() => currentGroup.value?.discussion_plan?.agenda_items || [])
const focusPoints = computed(() => currentGroup.value?.discussion_plan?.focus_points || [])
const resolvedPoints = computed(() => currentGroup.value?.consensus_state?.resolved_points || [])
const openQuestions = computed(() => currentGroup.value?.consensus_state?.open_questions || [])
const consensusDraft = computed(() => currentGroup.value?.consensus_state?.consensus_draft || '')
const isBlocked = computed(() => currentGroup.value?.runtime_status === 'blocked')
const latestModeratorSpeech = computed(() => {
  const reversed = [...publicSpeeches.value].reverse()
  return reversed.find((speech) => isModeratorSpeech(speech)) || null
})
const latestFailureEvent = computed(() => {
  if (!currentGroup.value) return null
  return [...currentGroup.value.events].reverse().find((event) => event.event_type === 'node_failed') || null
})

const currentPhaseSummary = computed(() => {
  if (!currentGroup.value) {
    return {
      title: '还没有讨论组',
      detail: `先选 ${MIN_PARTICIPANTS} 到 ${MAX_PARTICIPANTS} 个角色，再给出一个主题。`,
    }
  }

  const { group } = currentGroup.value
  if (group.status === 'finished') {
    return {
      title: '讨论已完成',
      detail: `围绕“${group.topic}”的讨论已经结束，可以回看事件流或重置后再跑一轮。`,
    }
  }

  if (group.phase === 'setup') {
    return {
      title: '准备阶段',
      detail: '讨论组已创建，系统会每 2 秒自动推进一个流程节点。',
    }
  }

  if (currentGroup.value.runtime_status === 'blocked') {
    return {
      title: '当前节点失败',
      detail: currentGroup.value.last_failure.failure_reason || '当前节点生成不合格，讨论已暂停，等待手动重试。',
    }
  }

  return {
    title: `${group.current_stage_label} · 第 ${Math.max(currentGroup.value?.discussion_plan?.current_round || group.round_number, 1)} / ${group.max_rounds} 轮`,
    detail: `当前主题：${group.topic}`,
  }
})

const loadCharacters = async () => {
  const response = await api.get<{ characters: Character[] }>('/character/list/')
  characters.value = response.data.characters
}

const loadGroups = async () => {
  const response = await api.get<{ groups: DiscussionGroup[] }>('/discussion/groups/')
  groups.value = response.data.groups
}

const loadGroupDetail = async (groupId: number) => {
  const response = await api.get<DiscussionGroupDetail>(`/discussion/groups/${groupId}/`)
  currentGroup.value = response.data
  observerNote.value = response.data.group.observer_note || ''
}

const recoverAdvanceProgress = async (groupId: number, previousUpdatedAt: string) => {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await new Promise((resolve) => {
      window.setTimeout(resolve, 2000)
    })
    try {
      const response = await api.get<DiscussionGroupDetail>(`/discussion/groups/${groupId}/`, { timeout: 10000 })
      if (response.data.group.updated_at === previousUpdatedAt) continue
      currentGroup.value = response.data
      observerNote.value = response.data.group.observer_note || ''
      await loadGroups()
      errorMessage.value = ''
      return true
    } catch {
      // ignore retry failures
    }
  }
  return false
}

const loadInitialData = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    await Promise.all([loadCharacters(), loadGroups()])
    if (selectedGroupId.value) {
      await loadGroupDetail(selectedGroupId.value)
    } else if (groups.value[0]) {
      await router.replace({ name: 'discussion-detail', params: { groupId: groups.value[0].id } })
    }
  } catch (error: unknown) {
    errorMessage.value = '讨论组页面加载失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    loading.value = false
  }
}

const toggleCharacter = (characterId: number) => {
  if (createPending.value || actionPending.value) return
  if (selectedCharacterIds.value.includes(characterId)) {
    selectedCharacterIds.value = selectedCharacterIds.value.filter((id) => id !== characterId)
    return
  }
  if (selectedCharacterIds.value.length >= MAX_PARTICIPANTS) return
  selectedCharacterIds.value = [...selectedCharacterIds.value, characterId]
}

const buildDemoCharacterIds = () => {
  const preferredIds = DEMO_CHARACTER_NAMES
    .map((name) => characters.value.find((character) => character.name === name)?.id || 0)
    .filter((id) => id > 0)

  if (preferredIds.length >= MIN_PARTICIPANTS) {
    return preferredIds.slice(0, MAX_PARTICIPANTS)
  }

  return characters.value.slice(0, Math.min(3, characters.value.length)).map((character) => character.id)
}

const applyDemoPreset = () => {
  if (createPending.value || actionPending.value) return
  groupTitle.value = DEMO_TITLE
  discussionTopic.value = DEMO_TOPIC
  maxRounds.value = DEMO_MAX_ROUNDS
  selectedCharacterIds.value = buildDemoCharacterIds()
}

const createDemoGroup = async () => {
  applyDemoPreset()
  if (!rosterReady.value) {
    errorMessage.value = `角色库里至少需要 ${MIN_PARTICIPANTS} 个角色，当前不足以创建示例讨论。`
    return
  }
  await createGroup()
}

const createGroup = async () => {
  if (!rosterReady.value || createPending.value) return
  createPending.value = true
  errorMessage.value = ''
  try {
    const response = await api.post<DiscussionGroupDetail>('/discussion/groups/create/', {
      title: groupTitle.value,
      topic: discussionTopic.value,
      character_ids: selectedCharacterIds.value,
      max_rounds: maxRounds.value,
    })
    currentGroup.value = response.data
    selectedCharacterIds.value = []
    await loadGroups()
    await router.push({ name: 'discussion-detail', params: { groupId: response.data.group.id } })
  } catch (error: unknown) {
    errorMessage.value = '创建讨论组失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    createPending.value = false
  }
}

const openGroup = async (groupId: number) => {
  if (selectedGroupId.value === groupId) return
  await router.push({ name: 'discussion-detail', params: { groupId } })
}

const removeCurrentGroup = async () => {
  if (!currentGroup.value || actionPending.value) return
  const groupId = currentGroup.value.group.id
  if (!window.confirm(`确定删除讨论组「${currentGroup.value.group.title}」吗？删除后无法恢复。`)) return

  actionPending.value = true
  errorMessage.value = ''
  try {
    await api.post(`/discussion/groups/${groupId}/remove/`, {})
    await loadGroups()
    if (groups.value[0]) {
      await router.replace({ name: 'discussion-detail', params: { groupId: groups.value[0].id } })
      await loadGroupDetail(groups.value[0].id)
    } else {
      currentGroup.value = null
      observerNote.value = ''
      await router.replace({ name: 'discussion' })
    }
  } catch (error: unknown) {
    errorMessage.value = '删除讨论组失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    actionPending.value = false
  }
}

const runGroupAction = async (action: 'advance' | 'reset', options?: { retryFailedNode?: boolean }) => {
  if (!currentGroup.value || actionPending.value) return
  const groupId = currentGroup.value.group.id
  const previousUpdatedAt = currentGroup.value.group.updated_at
  actionPending.value = true
  errorMessage.value = ''
  try {
    const response = await api.post<DiscussionGroupDetail>(
      `/discussion/groups/${groupId}/${action}/`,
      action === 'advance'
        ? {
            observer_note: observerNote.value,
            retry_failed_node: Boolean(options?.retryFailedNode),
          }
        : {},
      action === 'advance' ? { timeout: 120000 } : undefined,
    )
    currentGroup.value = response.data
    await loadGroups()
  } catch (error: unknown) {
    if (action === 'advance' && axios.isAxiosError(error) && error.code === 'ECONNABORTED') {
      errorMessage.value = '生成较慢，正在自动刷新结果...'
      const recovered = await recoverAdvanceProgress(groupId, previousUpdatedAt)
      if (!recovered) {
        errorMessage.value = '请求超时，系统可能仍在后台推进。请稍后重新打开该讨论组查看最新结果。'
      }
      return
    }
    errorMessage.value = action === 'advance' ? '推进讨论组失败。' : '重置讨论组失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    actionPending.value = false
  }
}

const runAutoAdvanceTick = async () => {
  if (!autoAdvanceEnabled.value) return
  if (!currentGroup.value) return
  if (currentGroup.value.group.status === 'finished') return
  if (currentGroup.value.runtime_status === 'blocked') return
  if (actionPending.value) return
  await runGroupAction('advance')
}

const stopAutoAdvance = () => {
  if (autoAdvanceTimer !== null) {
    window.clearInterval(autoAdvanceTimer)
    autoAdvanceTimer = null
  }
}

const startAutoAdvance = () => {
  stopAutoAdvance()
  autoAdvanceTimer = window.setInterval(() => {
    void runAutoAdvanceTick()
  }, AUTO_ADVANCE_INTERVAL_MS)
}

const eventPayloadHighlights = (event: DiscussionEvent) => {
  const lines: string[] = []
  const payload = event.payload || {}
  const isModeratorEvent = ['moderator_opening', 'agenda_setup', 'moderator_summary', 'consensus_draft'].includes(event.event_type)

  if (event.event_type === 'day_started') {
    const startName = typeof payload.start_participant_name === 'string' ? payload.start_participant_name : ''
    const names = Array.isArray(payload.participant_names) ? payload.participant_names.filter((item): item is string => typeof item === 'string' && item.length > 0) : []
    if (startName) lines.push(`随机首发：${startName}`)
    if (names.length > 0) lines.push(`本轮顺序：${names.join(' -> ')}`)
  }

  if (typeof payload.speech_count === 'number') {
    lines.push(`发言数：${payload.speech_count}`)
  }
  const route = typeof payload.route === 'string' ? payload.route : ''
  const failureCode = typeof payload.failure_code === 'string' ? payload.failure_code : ''
  const failureReason = typeof payload.failure_reason === 'string' ? payload.failure_reason : ''
  const stage = typeof payload.stage_label === 'string' ? payload.stage_label : ''

  if (stage) lines.push(`节点：${stage}`)
  if (!isModeratorEvent && route) lines.push(`下一步：${route}`)
  if (failureCode) lines.push(`失败码：${failureCode}`)
  if (failureReason) lines.push(`失败原因：${failureReason}`)

  return lines
}

watch(selectedGroupId, async (groupId) => {
  if (!groupId) {
    currentGroup.value = null
    return
  }
  try {
    await loadGroupDetail(groupId)
  } catch (error: unknown) {
    currentGroup.value = null
    errorMessage.value = '加载讨论组详情失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  }
}, { immediate: false })

onMounted(async () => {
  await loadInitialData()
  startAutoAdvance()
})

onBeforeUnmount(() => {
  stopAutoAdvance()
})
</script>

<template>
  <section class="mx-auto w-full max-w-[136rem] px-4 py-6 sm:px-6 xl:px-10">
    <div class="overflow-hidden rounded-[38px] border border-[#cfc2a5] bg-[linear-gradient(135deg,#f5ecd7_0%,#efe4cb_48%,#e7dbc2_100%)] shadow-[0_24px_80px_rgba(52,44,28,0.08)]">
      <div class="grid gap-8 px-6 py-8 lg:px-8 xl:grid-cols-[minmax(0,1.25fr)_minmax(19rem,0.75fr)] xl:items-end">
        <div>
          <div class="inline-flex items-center rounded-full border border-[#395244]/15 bg-white/70 px-3 py-1 text-xs font-black tracking-[0.24em] text-[#5c5a4f] backdrop-blur">
            ROUND TABLE STAGE
          </div>
          <h1 class="mt-5 max-w-5xl font-black tracking-tight text-[#1f241d] text-4xl sm:text-5xl xl:text-6xl">
            让主持人带着几位角色，围绕一个主题认真把话说透。
          </h1>
          <p class="mt-4 max-w-4xl text-sm leading-8 text-[#5f6256] sm:text-[15px]">
            这不是普通群聊，而是一张会逐步推进的讨论舞台。你提供主题、角色和轮次，系统按开场、议题拆解、角色立场、主持总结、聚焦讨论到共识收束的链路推进。第一个选中的角色会担任主持人。
          </p>
          <div class="mt-6 flex flex-wrap gap-3 text-xs font-bold text-[#4e5348]">
            <span class="rounded-full border border-[#395244]/15 bg-white/75 px-4 py-2">主持人：{{ currentGroup?.group.moderator_participant_name || selectedModeratorName || '等待指定' }}</span>
            <span class="rounded-full border border-[#395244]/15 bg-white/75 px-4 py-2">当前主题：{{ currentGroup?.group.topic || discussionTopic }}</span>
          </div>
        </div>

        <div class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          <div class="rounded-[28px] border border-[#d8cdb4] bg-white/75 p-5 backdrop-blur">
            <div class="text-sm text-[#6b685d]">参与人数</div>
            <div class="mt-2 text-xl font-black text-[#1f241d]">{{ MIN_PARTICIPANTS }} - {{ MAX_PARTICIPANTS }} 人</div>
            <div class="mt-1 text-xs text-[#6b685d]">主持人固定为第一个选中角色。</div>
          </div>
          <div class="rounded-[28px] border border-[#d8cdb4] bg-white/75 p-5 backdrop-blur">
            <div class="text-sm text-[#6b685d]">当前讨论组数</div>
            <div class="mt-2 text-3xl font-black text-[#1f241d]">{{ groups.length }}</div>
            <div class="mt-1 text-xs text-[#6b685d]">本地保存，可随时重新打开。</div>
          </div>
          <div class="rounded-[28px] border border-[#d8cdb4] bg-white/75 p-5 backdrop-blur">
            <div class="text-sm text-[#6b685d]">推进方式</div>
            <div class="mt-2 text-xl font-black text-[#1f241d]">自动 2 秒 / 节点</div>
            <div class="mt-1 text-xs text-[#6b685d]">失败时会暂停，等待手动重试。</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="alert alert-error mt-6">{{ errorMessage }}</div>

    <div
      v-if="loading"
      class="mt-6 grid min-h-[22rem] place-items-center rounded-[32px] border border-base-200 bg-base-100 text-base-content/50 shadow-sm"
    >
      正在加载讨论组工作台...
    </div>

    <template v-else>
      <div class="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.18fr)_minmax(24rem,0.82fr)]">
        <section class="rounded-[32px] border border-[#d8ccb3] bg-[#faf4e7] p-6 shadow-[0_20px_55px_rgba(52,44,28,0.05)]">
          <div class="flex items-center gap-3">
            <AppIcon name="game" icon-class="h-5 w-5" />
            <div>
              <h2 class="text-lg font-black text-[#1f241d]">新建讨论组</h2>
              <p class="text-sm text-[#6a675e]">先给主题，再从角色库里勾选参与者。</p>
            </div>
          </div>

          <div class="mt-5 grid gap-4 xl:grid-cols-[minmax(0,0.74fr)_minmax(16rem,0.26fr)]">
            <div>
              <label class="block">
                <div class="mb-2 text-sm font-bold text-[#4b4b43]">讨论组标题</div>
                <input v-model="groupTitle" type="text" class="input input-bordered w-full rounded-2xl border-[#d8ccb3] bg-white" placeholder="输入讨论组标题">
              </label>

              <label class="mt-4 block">
                <div class="mb-2 text-sm font-bold text-[#4b4b43]">讨论主题</div>
                <textarea
                  v-model="discussionTopic"
                  class="textarea textarea-bordered min-h-[148px] w-full rounded-2xl border-[#d8ccb3] bg-white"
                  placeholder="输入这组角色要围绕什么主题讨论"
                />
              </label>
            </div>

            <div class="space-y-4">
              <div class="rounded-[24px] border border-[#d8ccb3] bg-white p-4">
                <div class="text-sm font-black text-[#1f241d]">最大轮次</div>
                <div class="mt-1 text-xs leading-5 text-[#6a675e]">表示最多允许多少轮主持总结与聚焦讨论。</div>
                <input v-model.number="maxRounds" type="number" min="2" max="6" class="input input-bordered mt-4 w-full rounded-full border-[#d8ccb3] bg-[#faf6ec]">
              </div>

              <div class="rounded-[24px] border border-[#d8ccb3] bg-white p-4">
                <div class="text-sm font-black text-[#1f241d]">当前已选</div>
                <div class="mt-1 text-2xl font-black text-[#1f241d]">{{ selectedCount }}</div>
                <div class="mt-2 text-xs leading-5 text-[#6a675e]">
                  需要至少 {{ MIN_PARTICIPANTS }} 人，最多 {{ MAX_PARTICIPANTS }} 人。<span v-if="selectedModeratorName">当前主持人：{{ selectedModeratorName }}</span>
                </div>
              </div>

              <div class="rounded-[24px] border border-[#d8ccb3] bg-[#23352e] p-4 text-[#f8f2e5]">
                <div class="text-sm font-black">创建动作</div>
                <div class="mt-3 grid gap-2">
                  <button
                    class="btn btn-sm rounded-full border-none bg-white/12 text-white hover:bg-white/20"
                    :disabled="createPending || actionPending"
                    @click="applyDemoPreset"
                  >
                    加载示例配置
                  </button>
                  <button
                    class="btn btn-sm rounded-full border-none bg-white/12 text-white hover:bg-white/20"
                    :disabled="createPending || actionPending || characters.length < MIN_PARTICIPANTS"
                    @click="createDemoGroup"
                  >
                    一键创建示例讨论
                  </button>
                  <button
                    class="btn btn-sm rounded-full border-none bg-[#f3e7ce] px-5 text-[#1f241d] hover:bg-[#ead7b0]"
                    :disabled="!rosterReady || createPending"
                    @click="createGroup"
                  >
                    {{ createPending ? '正在创建...' : '创建讨论组' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-6">
            <div class="mb-3 flex items-center justify-between">
              <div class="text-sm font-bold text-[#4b4b43]">参与角色</div>
              <div class="text-xs text-[#6a675e]">已选 {{ selectedCount }} / {{ MAX_PARTICIPANTS }}</div>
            </div>
            <div class="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
              <button
                v-for="character in characters"
                :key="character.id"
                type="button"
                class="flex items-start gap-3 rounded-[22px] border px-4 py-4 text-left transition"
                :class="selectedCharacterIds.includes(character.id)
                  ? 'border-[#23352e] bg-[#efe4cd] shadow-sm'
                  : 'border-[#ddd0b5] bg-white hover:bg-[#fcf7ee]'"
                @click="toggleCharacter(character.id)"
              >
                <img v-if="character.photo" :src="character.photo" :alt="character.name" class="h-14 w-14 rounded-2xl object-cover">
                <div v-else class="grid h-14 w-14 place-items-center rounded-2xl bg-[#efe7d6] text-xs font-black text-[#625f56]">
                  {{ character.name.slice(0, 1) }}
                </div>
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <div class="truncate text-sm font-black text-[#1f241d]">{{ character.name }}</div>
                    <span class="rounded-full bg-[#f0eadc] px-2 py-0.5 text-[11px] font-bold text-[#5d5b52]">
                      {{ character.ai_config.reply_style }}
                    </span>
                  </div>
                  <p class="mt-1 line-clamp-2 text-xs leading-5 text-[#6a675e]">
                    {{ character.profile || '暂无角色介绍。' }}
                  </p>
                </div>
              </button>
            </div>
          </div>
        </section>

        <section class="rounded-[32px] border border-[#d8ccb3] bg-[#faf4e7] p-6 shadow-[0_20px_55px_rgba(52,44,28,0.05)]">
          <div class="flex items-center gap-3">
            <AppIcon name="spark" icon-class="h-5 w-5" />
            <div>
              <h2 class="text-lg font-black text-[#1f241d]">讨论组列表</h2>
              <p class="text-sm text-[#6a675e]">已创建的讨论组会保存在本地实例里。</p>
            </div>
          </div>

          <div v-if="groups.length === 0" class="mt-5 rounded-[24px] border border-dashed border-[#d8ccb3] px-4 py-8 text-center text-sm text-[#6a675e]">
            还没有讨论组。先从左侧创建一组。
          </div>

          <div v-else class="mt-5 space-y-3">
            <button
              v-for="group in groups"
              :key="group.id"
              type="button"
              class="w-full rounded-[24px] border px-4 py-4 text-left transition"
              :class="selectedGroupId === group.id
                ? 'border-[#23352e] bg-[#efe4cd] shadow-sm'
                : 'border-[#ddd0b5] bg-white hover:bg-[#fcf7ee]'"
              @click="openGroup(group.id)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="truncate text-base font-black text-[#1f241d]">{{ group.title }}</div>
                  <div class="mt-1 line-clamp-2 text-xs leading-5 text-[#6a675e]">
                    {{ group.topic }}
                  </div>
                  <div class="mt-2 text-xs text-[#6a675e]">
                    {{ group.current_stage_label }} · 第 {{ Math.max(group.round_number, 1) }} / {{ group.max_rounds }} 轮 · {{ group.participant_count }} 人
                  </div>
                </div>
                <span class="rounded-full px-3 py-1 text-[11px] font-bold"
                  :class="group.status === 'finished'
                    ? 'bg-[#e3eee7] text-[#244031]'
                    : group.runtime_status === 'blocked'
                      ? 'bg-[#f6dfdb] text-[#7a3d31]'
                      : 'bg-[#ece5d6] text-[#5f5b51]'"
                >
                  {{ group.status === 'finished' ? '已完成' : group.runtime_status === 'blocked' ? '已暂停' : '进行中' }}
                </span>
              </div>
            </button>
          </div>
        </section>
      </div>

      <section class="mt-6 rounded-[34px] border border-[#d3c6ab] bg-[linear-gradient(180deg,#fffaf0_0%,#f8efdf_100%)] p-6 shadow-[0_26px_75px_rgba(52,44,28,0.07)] sm:p-7">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="inline-flex rounded-full border border-[#395244]/15 bg-white/80 px-3 py-1 text-xs font-black tracking-[0.2em] text-[#5f6055]">
              DISCUSSION STAGE
            </div>
            <h2 class="mt-4 text-3xl font-black tracking-tight text-[#1f241d]">
              {{ currentGroup?.group.title || '讨论舞台' }}
            </h2>
            <p class="mt-3 max-w-4xl text-sm leading-7 text-[#636258]">
              {{ currentPhaseSummary.title }}。{{ currentPhaseSummary.detail }}
            </p>
          </div>

          <div v-if="currentGroup" class="flex flex-wrap gap-2">
            <label class="flex cursor-pointer items-center gap-2 rounded-full border border-[#d8ccb3] bg-white px-3 py-1.5 text-xs font-bold text-[#4f5349]">
              <input v-model="autoAdvanceEnabled" type="checkbox" class="checkbox checkbox-xs">
              自动推进（2s）
            </label>
            <button class="btn rounded-full border-none bg-[#23352e] px-5 text-white hover:bg-[#1d2c27]" :disabled="actionPending || currentGroup.group.status === 'finished' || isBlocked" @click="runGroupAction('advance')">
              {{ actionPending ? '处理中...' : '推进下一节点' }}
            </button>
            <button v-if="isBlocked" class="btn rounded-full border-none bg-[#d97757] px-5 text-white hover:bg-[#c36749]" :disabled="actionPending" @click="runGroupAction('advance', { retryFailedNode: true })">
              {{ actionPending ? '处理中...' : '重试当前节点' }}
            </button>
            <button class="btn rounded-full border border-[#d8ccb3] bg-white px-5 text-[#3d433b] hover:bg-[#f9f4ea]" :disabled="actionPending" @click="runGroupAction('reset')">
              重置讨论组
            </button>
            <button class="btn rounded-full border border-[#edc5bc] bg-[#fff5f2] px-5 text-[#8a4f43] hover:bg-[#fdebe6]" :disabled="actionPending" @click="removeCurrentGroup">
              删除讨论组
            </button>
          </div>
        </div>

        <div v-if="!currentGroup" class="mt-6 rounded-[24px] border border-dashed border-[#d8ccb3] px-4 py-12 text-center text-sm text-[#6a675e]">
          选择一个讨论组，或先在上方创建一组。
        </div>

        <template v-else>
          <div class="mt-6 grid gap-4 lg:grid-cols-4 xl:grid-cols-6">
            <div class="rounded-[22px] border border-[#d8ccb3] bg-white px-4 py-4 lg:col-span-1">
              <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7a776d]">主持人</div>
              <div class="mt-2 text-lg font-black text-[#1f241d]">{{ currentGroup.group.moderator_participant_name || '未指定' }}</div>
              <div class="mt-2 text-xs leading-5 text-[#6a675e]">第一位选中的角色会担任主持，不参与普通轮次的发言队列。</div>
            </div>
            <div class="rounded-[22px] border border-[#d8ccb3] bg-white px-4 py-4 lg:col-span-1">
              <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7a776d]">当前阶段</div>
              <div class="mt-2 text-lg font-black text-[#1f241d]">{{ currentGroup.group.current_stage_label }}</div>
              <div class="mt-2 text-xs leading-5 text-[#6a675e]">第 {{ Math.max(currentGroup.discussion_plan.current_round || currentGroup.group.round_number, 1) }} / {{ currentGroup.group.max_rounds }} 轮</div>
            </div>
            <div class="rounded-[22px] border border-[#d8ccb3] bg-white px-4 py-4 lg:col-span-1">
              <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7a776d]">运行状态</div>
              <div class="mt-2 text-lg font-black" :class="isBlocked ? 'text-[#8a4f43]' : 'text-[#244031]'">
                {{ isBlocked ? '已暂停' : currentGroup.group.status === 'finished' ? '已完成' : '正常' }}
              </div>
              <div class="mt-2 text-xs leading-5 text-[#6a675e]">公开发言 {{ publicSpeeches.length }} 段，事件 {{ currentGroup.events.length }} 条。</div>
            </div>
            <div class="rounded-[22px] border border-[#d8ccb3] bg-white px-4 py-4 lg:col-span-3">
              <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7a776d]">当前主题</div>
              <div class="mt-2 text-sm leading-7 text-[#44463f]">{{ currentGroup.group.topic }}</div>
            </div>
          </div>

          <div v-if="isBlocked" class="mt-6 rounded-[24px] border border-[#efc2b7] bg-[#fff1ed] px-4 py-4 text-sm text-[#4f3c37]">
            <div class="font-black">当前节点已暂停</div>
            <div class="mt-2">{{ currentGroup.last_failure.failure_reason || '节点生成失败。' }}</div>
            <div class="mt-2 text-xs text-[#7b655f]">
              失败节点：{{ currentGroup.last_failure.node_kind || currentGroup.failed_node.kind || 'unknown' }} ·
              阶段：{{ currentGroup.last_failure.stage || currentGroup.failed_node.stage || 'unknown' }}
            </div>
          </div>

          <div class="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.58fr)_minmax(20rem,0.92fr)]">
            <div class="space-y-6">
              <div class="rounded-[28px] border border-[#d8ccb3] bg-white px-5 py-5 shadow-[0_16px_40px_rgba(52,44,28,0.04)]">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <div class="text-xs font-bold uppercase tracking-[0.18em] text-[#7b7668]">主持人聚焦卡</div>
                    <div class="mt-2 text-lg font-black text-[#1f241d]">{{ latestModeratorSpeech?.participant_name || '主持人尚未发言' }}</div>
                  </div>
                  <span v-if="latestModeratorSpeech" class="rounded-full bg-[#f2ead9] px-3 py-1 text-[11px] font-bold text-[#605c52]">
                    {{ typeof latestModeratorSpeech.metadata.stage_label === 'string' && latestModeratorSpeech.metadata.stage_label ? latestModeratorSpeech.metadata.stage_label : latestModeratorSpeech.phase_label }}
                  </span>
                </div>
                <MarkdownContent v-if="latestModeratorSpeech?.content" :content="latestModeratorSpeech.content" class="mt-4 text-[15px] leading-8 text-[#40433c]" />
                <div v-else class="mt-4 text-sm text-[#6a675e]">主持人尚未输出公开内容。</div>
              </div>

              <div class="rounded-[28px] border border-[#d8ccb3] bg-white px-5 py-5 shadow-[0_16px_40px_rgba(52,44,28,0.04)]">
                <div class="flex items-center justify-between gap-3">
                  <div class="text-lg font-black text-[#1f241d]">公开发言回放</div>
                  <div class="text-xs text-[#7a766b]">{{ publicSpeeches.length }} 段</div>
                </div>
                <div class="mt-5 space-y-4">
                  <div
                    v-for="speech in publicSpeeches"
                    :key="speech.id"
                    class="rounded-[24px] border px-5 py-5"
                    :class="isModeratorSpeech(speech)
                      ? 'border-[#c8d6ca] bg-[linear-gradient(135deg,#f2f0e5_0%,#edf3ec_100%)]'
                      : 'border-[#e6ddca] bg-[#fcf8ef]'"
                  >
                    <div class="flex flex-wrap items-center gap-2">
                      <div class="text-base font-black text-[#1f241d]">{{ speech.participant_name }}</div>
                      <span v-if="isModeratorSpeech(speech)" class="rounded-full bg-[#23352e] px-2.5 py-1 text-[11px] font-bold text-white">
                        主持人
                      </span>
                      <span class="rounded-full bg-white px-2.5 py-1 text-[11px] font-bold text-[#625f55]">
                        第 {{ speech.round_number }} 轮
                      </span>
                      <span v-if="typeof speech.metadata.phase_label === 'string' && speech.metadata.phase_label" class="rounded-full bg-white px-2.5 py-1 text-[11px] font-bold text-[#625f55]">
                        {{ speech.metadata.phase_label }}
                      </span>
                      <span v-if="typeof speech.metadata.stance_label === 'string' && speech.metadata.stance_label" class="rounded-full bg-white px-2.5 py-1 text-[11px] font-bold text-[#625f55]">
                        {{ speech.metadata.stance_label }}
                      </span>
                    </div>
                    <MarkdownContent :content="speech.content" class="mt-4 text-[15px] leading-8 text-[#3d4139]" />
                  </div>
                </div>
              </div>
            </div>

            <div class="space-y-5">
              <div class="rounded-[26px] border border-[#d8ccb3] bg-[#f8f1e2] p-4">
                <div class="text-sm font-black text-[#1f241d]">主持人便签</div>
                <div class="mt-4 space-y-4 text-sm text-[#55584f]">
                  <div>
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7a776d]">本轮目标</div>
                    <div class="mt-1 leading-6">{{ currentGroup.discussion_plan.round_goal || '主持人尚未给出本轮目标。' }}</div>
                  </div>
                  <div>
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7a776d]">主持追问</div>
                    <div class="mt-1 leading-6">{{ currentGroup.discussion_plan.moderator_question || '当前暂无。' }}</div>
                  </div>
                </div>
              </div>

              <div class="rounded-[26px] border border-[#d8ccb3] bg-[#f8f1e2] p-4">
                <div class="text-sm font-black text-[#1f241d]">当前议题</div>
                <ul class="mt-3 space-y-2 text-sm leading-6 text-[#55584f]">
                  <li v-for="item in agendaItems" :key="item">{{ item }}</li>
                  <li v-if="agendaItems.length === 0" class="text-[#7a776d]">暂无。</li>
                </ul>
              </div>

              <div class="rounded-[26px] border border-[#d8ccb3] bg-[#f8f1e2] p-4">
                <div class="text-sm font-black text-[#1f241d]">当前焦点</div>
                <ul class="mt-3 space-y-2 text-sm leading-6 text-[#55584f]">
                  <li v-for="item in focusPoints" :key="item">{{ item }}</li>
                  <li v-if="focusPoints.length === 0" class="text-[#7a776d]">暂无。</li>
                </ul>
              </div>

              <div class="rounded-[26px] border border-[#d8ccb3] bg-[#f8f1e2] p-4">
                <div class="text-sm font-black text-[#1f241d]">讨论收束</div>
                <div class="mt-4 grid gap-3">
                  <div class="rounded-[20px] border border-[#ded2b8] bg-white px-4 py-3">
                    <div class="text-xs font-bold uppercase tracking-[0.14em] text-[#7a776d]">已成共识</div>
                    <ul class="mt-2 space-y-1 text-sm text-[#55584f]">
                      <li v-for="item in resolvedPoints" :key="item">{{ item }}</li>
                      <li v-if="resolvedPoints.length === 0" class="text-[#7a776d]">暂无。</li>
                    </ul>
                  </div>
                  <div class="rounded-[20px] border border-[#ded2b8] bg-white px-4 py-3">
                    <div class="text-xs font-bold uppercase tracking-[0.14em] text-[#7a776d]">待解问题</div>
                    <ul class="mt-2 space-y-1 text-sm text-[#55584f]">
                      <li v-for="item in openQuestions" :key="item">{{ item }}</li>
                      <li v-if="openQuestions.length === 0" class="text-[#7a776d]">暂无。</li>
                    </ul>
                  </div>
                  <div class="rounded-[20px] border border-[#ded2b8] bg-white px-4 py-3">
                    <div class="text-xs font-bold uppercase tracking-[0.14em] text-[#7a776d]">共识草案</div>
                    <div class="mt-2 text-sm leading-6 text-[#55584f]">
                      {{ consensusDraft || '主持人尚未输出共识草案。' }}
                    </div>
                  </div>
                </div>
              </div>

              <div class="rounded-[26px] border border-[#d8ccb3] bg-[#f8f1e2] p-4">
                <div class="flex items-center justify-between gap-3">
                  <div class="text-sm font-black text-[#1f241d]">参与角色</div>
                  <div class="text-xs text-[#7a776d]">{{ currentGroup.participants.length }} 人</div>
                </div>
                <div class="mt-4 space-y-3">
                  <div v-for="participant in currentGroup.participants" :key="participant.id" class="rounded-[20px] border border-[#e0d5bc] bg-white px-4 py-4">
                    <div class="flex items-start gap-3">
                      <img v-if="participant.photo" :src="participant.photo" :alt="participant.display_name" class="h-12 w-12 rounded-2xl object-cover">
                      <div v-else class="grid h-12 w-12 place-items-center rounded-2xl bg-[#efe7d6] text-xs font-black text-[#625f56]">
                        {{ participant.display_name.slice(0, 1) }}
                      </div>
                      <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-2">
                          <div class="truncate text-sm font-black text-[#1f241d]">{{ participant.display_name }}</div>
                          <span v-if="participant.is_moderator" class="rounded-full bg-[#23352e] px-2 py-0.5 text-[11px] font-bold text-white">
                            主持人
                          </span>
                        </div>
                        <div class="mt-1 text-xs text-[#7a776d]">
                          {{ participant.reply_style }} / {{ participant.reply_length }} / {{ participant.initiative_level }}
                        </div>
                        <p class="mt-2 line-clamp-2 text-xs leading-5 text-[#6a675e]">
                          {{ participant.profile || '暂无角色简介。' }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="rounded-[28px] border border-[#d8ccb3] bg-white px-5 py-5 shadow-[0_16px_40px_rgba(52,44,28,0.04)]">
                <div class="flex items-center justify-between gap-3">
                  <div class="text-lg font-black text-[#1f241d]">事件时间线</div>
                  <div class="text-xs text-[#7a766b]">{{ currentGroup.events.length }} 条</div>
                </div>
                <div class="mt-5 space-y-3">
                  <div v-for="event in currentGroup.events" :key="event.id" class="rounded-[22px] border border-[#ece3d0] bg-[#fffaf2] px-4 py-4">
                    <div class="flex flex-wrap items-center gap-2">
                      <div class="text-sm font-black text-[#1f241d]">{{ event.title }}</div>
                      <span class="rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-[#625f55]">
                        {{ event.phase_label || '通用事件' }}
                      </span>
                    </div>
                    <p v-if="event.content" class="mt-2 text-sm leading-7 text-[#55584f]">{{ event.content }}</p>
                    <ul v-if="eventPayloadHighlights(event).length > 0" class="mt-2 space-y-1 text-xs leading-5 text-[#69675e]">
                      <li v-for="line in eventPayloadHighlights(event)" :key="line">{{ line }}</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div class="rounded-[26px] border border-[#d8ccb3] bg-[#f8f1e2] p-4">
                <div class="text-sm font-black text-[#1f241d]">观察者备注</div>
                <textarea
                  v-model="observerNote"
                  class="textarea textarea-bordered mt-3 min-h-[120px] w-full rounded-2xl border-[#d8ccb3] bg-white"
                  placeholder="给下一次推进补一条观察备注。会写进事件流。"
                />
                <div v-if="latestFailureEvent" class="mt-3 rounded-[18px] border border-[#efc2b7] bg-[#fff7f4] px-3 py-3 text-xs leading-5 text-[#7c615b]">
                  最近一次失败：{{ latestFailureEvent.content }}
                </div>
              </div>
            </div>
          </div>
        </template>
      </section>
    </template>
  </section>
</template>
