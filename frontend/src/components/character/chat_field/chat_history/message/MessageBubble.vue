<script setup lang="ts">
import MarkdownContent from '@/components/MarkdownContent.vue'
import type { ChatMessage } from '@/types/message'

defineProps<{
  message: ChatMessage
}>()
</script>

<template>
  <div :class="message.role === 'user' ? 'flex justify-end' : 'flex justify-start'">
    <div
      :class="message.role === 'user'
        ? 'max-w-[84%] rounded-3xl rounded-tr-md bg-primary px-4 py-3 text-sm leading-7 text-primary-content shadow-sm sm:max-w-[80%]'
        : 'max-w-[84%] rounded-3xl rounded-tl-md bg-white/92 px-4 py-3 text-sm leading-7 text-base-content shadow-sm sm:max-w-[80%]'"
    >
      <MarkdownContent :content="message.content" />
    </div>
  </div>
</template>
