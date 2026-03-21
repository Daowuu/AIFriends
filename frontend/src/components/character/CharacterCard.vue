<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import type { Character } from '@/types/character'

const props = withDefaults(defineProps<{
  character: Character
  mode?: 'feed' | 'space-owner' | 'friend'
}>(), {
  mode: 'feed',
})

const emit = defineEmits<{
  open: [character: Character]
  chat: [character: Character]
  edit: [character: Character]
  remove: [character: Character]
}>()

const actionLabel = computed(() => {
  if (props.mode === 'space-owner') return '编辑角色'
  if (props.mode === 'friend') return '继续聊天'
  return '开始对话'
})
</script>

<template>
  <article
    class="group overflow-hidden rounded-[28px] border border-base-200 bg-base-100 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
  >
    <button
      type="button"
      class="block w-full text-left"
      @click="emit('open', character)"
    >
      <div class="relative h-64 bg-base-200">
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

      <div class="mt-5 flex gap-3">
        <button
          type="button"
          class="btn btn-primary btn-sm flex-1"
          @click.stop="mode === 'space-owner' ? emit('edit', character) : emit('open', character)"
        >
          {{ actionLabel }}
        </button>
        <button
          v-if="mode === 'space-owner'"
          type="button"
          class="btn btn-ghost btn-sm flex-1 border border-base-300"
          @click.stop="emit('chat', character)"
        >
          进入聊天
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
