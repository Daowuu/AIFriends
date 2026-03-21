<script setup lang="ts">
import { computed } from 'vue'

import type { CharacterAuthor } from '@/types/character'

const props = defineProps<{
  author: CharacterAuthor
}>()

const avatarFallback = computed(() => (
  props.author.display_name?.slice(0, 1).toUpperCase()
  || props.author.username.slice(0, 1).toUpperCase()
))
</script>

<template>
  <section class="overflow-hidden rounded-[34px] border border-base-200 bg-base-100 shadow-sm">
    <div class="h-36 bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.35),_transparent_42%),linear-gradient(135deg,#fff7ed,#f8fafc_60%,#eef2ff)]" />
    <div class="relative px-6 pb-6">
      <div class="-mt-12 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div class="flex items-end gap-4">
          <div class="grid h-24 w-24 place-items-center overflow-hidden rounded-[28px] border-4 border-base-100 bg-base-200 text-3xl font-black shadow-sm">
            <img
              v-if="author.avatar"
              :src="author.avatar"
              :alt="author.display_name || author.username"
              class="h-full w-full object-cover"
            >
            <span v-else>{{ avatarFallback }}</span>
          </div>
          <div class="pb-1">
            <h1 class="text-3xl font-black">{{ author.display_name || author.username }}</h1>
            <p class="mt-1 text-sm text-base-content/50">@{{ author.username }}</p>
          </div>
        </div>

        <div class="rounded-2xl bg-base-50 px-4 py-3 text-sm leading-7 text-base-content/60 md:max-w-md">
          {{ author.bio || '这个人还没有写简介。' }}
        </div>
      </div>
    </div>
  </section>
</template>
