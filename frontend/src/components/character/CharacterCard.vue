<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import type { Character } from '@/types/character'

const props = withDefaults(defineProps<{
  character: Character
  mode?: 'feed' | 'space-owner' | 'friend' | 'studio'
}>(), {
  mode: 'feed',
})

const emit = defineEmits<{
  open: [character: Character]
  chat: [character: Character]
  edit: [character: Character]
  remove: [character: Character]
}>()

const isStudioMode = computed(() => props.mode === 'studio')

const actionLabel = computed(() => {
  if (props.mode === 'studio') return '继续配置'
  if (props.mode === 'space-owner') return '编辑角色'
  if (props.mode === 'friend') return '继续聊天'
  return '开始对话'
})

const styleLabels = {
  natural: '自然',
  warm: '热情',
  restrained: '克制',
  playful: '俏皮',
} as const

const memoryLabels = {
  off: '关闭',
  standard: '标准',
  enhanced: '加强',
} as const

const voiceSummary = computed(() => props.character.voice?.name || '未配音色')
const aiSummary = computed(() => styleLabels[props.character.ai_config?.reply_style || 'natural'])
const memorySummary = computed(() => memoryLabels[props.character.ai_config?.memory_mode || 'standard'])
const statusSummary = computed(() => (
  props.character.friend_id ? '已可聊天' : '待试聊'
))
</script>

<template>
  <article
    class="group overflow-hidden border transition"
    :class="isStudioMode
      ? 'rounded-[30px] border-[#d9cfbe] bg-[linear-gradient(180deg,rgba(255,250,241,0.98),rgba(250,246,236,0.94))] shadow-[0_16px_46px_rgba(15,23,42,0.06)] hover:-translate-y-1 hover:shadow-[0_24px_58px_rgba(15,23,42,0.10)]'
      : 'rounded-[28px] border-base-200 bg-base-100 shadow-sm hover:-translate-y-1 hover:shadow-md'"
  >
    <button
      type="button"
      class="block w-full text-left"
      @click="emit('open', character)"
    >
      <div class="relative bg-base-200" :class="isStudioMode ? 'h-52' : 'h-64'">
        <img
          v-if="character.background_image"
          :src="character.background_image"
          :alt="character.name"
          class="h-full w-full object-cover transition duration-300 group-hover:scale-[1.02]"
        >
        <div
          v-else
          class="h-full w-full bg-[radial-gradient(circle_at_top,_rgba(251,191,36,0.28),_transparent_52%),linear-gradient(135deg,#fff7ed,#f8fafc)]"
        />

        <div v-if="isStudioMode" class="absolute left-4 top-4 flex flex-wrap gap-2">
          <span class="rounded-full border border-white/16 bg-black/20 px-3 py-1 text-[11px] font-bold text-white/88 backdrop-blur">
            {{ aiSummary }}
          </span>
          <span class="rounded-full border border-white/16 bg-black/20 px-3 py-1 text-[11px] font-bold text-white/88 backdrop-blur">
            {{ statusSummary }}
          </span>
        </div>

        <div class="absolute inset-x-0 bottom-0 bg-linear-to-t from-black/60 to-transparent px-5 pb-5 pt-14 text-white">
          <div class="flex items-end gap-3">
            <div class="h-14 w-14 overflow-hidden rounded-2xl border border-white/30 bg-white/15 shadow-sm backdrop-blur">
              <img
                v-if="character.photo"
                :src="character.photo"
                :alt="character.name"
                class="h-full w-full object-cover"
              >
              <div v-else class="grid h-full w-full place-items-center text-xl font-black">
                {{ character.name.slice(0, 1) }}
              </div>
            </div>

            <div class="min-w-0">
              <div class="truncate text-lg font-black">{{ character.name }}</div>
              <div class="truncate text-sm text-white/80">
                @{{ character.author.display_name || character.author.username }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </button>

    <div class="p-5">
      <RouterLink
        :to="`/space/${character.author.id}`"
        class="inline-flex items-center rounded-full bg-base-200 px-3 py-1 text-xs font-bold text-base-content/70 transition hover:bg-base-300"
        @click.stop
      >
        来自 {{ character.author.display_name || character.author.username }}
      </RouterLink>

      <p class="mt-4 line-clamp-4 min-h-24 text-sm leading-7 text-base-content/65">
        {{ character.profile || '这个角色还没有写介绍。' }}
      </p>

      <div
        v-if="mode === 'studio'"
        class="mt-4 grid grid-cols-2 gap-2 rounded-[24px] border border-[#ded4c3] bg-white/78 p-3 text-xs text-[#55635c]"
      >
        <div>
          <div class="font-bold text-[#8a7757]">AI 风格</div>
          <div class="mt-1">{{ aiSummary }}</div>
        </div>
        <div>
          <div class="font-bold text-[#8a7757]">记忆模式</div>
          <div class="mt-1">{{ memorySummary }}</div>
        </div>
        <div>
          <div class="font-bold text-[#8a7757]">音色状态</div>
          <div class="mt-1">{{ voiceSummary }}</div>
        </div>
        <div>
          <div class="font-bold text-[#8a7757]">运行状态</div>
          <div class="mt-1">{{ statusSummary }}</div>
        </div>
      </div>

      <div class="mt-5 flex gap-3">
        <button
          type="button"
          class="btn btn-sm flex-1"
          :class="isStudioMode
            ? 'border-none bg-[#16231f] text-[#f7f1e5] hover:bg-[#22362f]'
            : 'btn-primary'"
          @click.stop="mode === 'space-owner' || mode === 'studio' ? emit('edit', character) : emit('open', character)"
        >
          {{ actionLabel }}
        </button>
        <button
          v-if="mode === 'space-owner' || mode === 'studio'"
          type="button"
          class="btn btn-ghost btn-sm flex-1"
          :class="isStudioMode ? 'border border-[#d6ccb8] bg-white/70 hover:bg-[#fff7e8]' : 'border border-base-300'"
          @click.stop="emit('chat', character)"
        >
          {{ mode === 'studio' ? '试聊' : '进入聊天' }}
        </button>
        <button
          v-if="mode === 'space-owner' || mode === 'friend'"
          type="button"
          class="btn btn-ghost btn-sm text-error"
          @click.stop="emit('remove', character)"
        >
          {{ mode === 'friend' ? '移除好友' : '删除' }}
        </button>
      </div>
    </div>
  </article>
</template>
