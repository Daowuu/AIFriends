<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { ChatMessage } from '@/types/message'

import MessageBubble from './message/MessageBubble.vue'

const props = defineProps<{
  messages: ChatMessage[]
  loadingHistory?: boolean
  hasMore?: boolean
}>()

const emit = defineEmits<{
  loadMore: []
}>()

const scrollRef = ref<HTMLDivElement | null>(null)
const sentinelRef = ref<HTMLDivElement | null>(null)
let observer: IntersectionObserver | null = null
let previousScrollHeight = 0

const scrollToBottom = async () => {
  await nextTick()
  if (!scrollRef.value) return
  scrollRef.value.scrollTop = scrollRef.value.scrollHeight
}

const captureScrollSnapshot = () => {
  previousScrollHeight = scrollRef.value?.scrollHeight || 0
}

const restoreScrollAfterPrepend = async () => {
  await nextTick()
  if (!scrollRef.value) return

  const currentScrollHeight = scrollRef.value.scrollHeight
  const delta = currentScrollHeight - previousScrollHeight
  scrollRef.value.scrollTop += delta
}

const setupObserver = () => {
  observer?.disconnect()

  if (!scrollRef.value || !sentinelRef.value) return

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && props.hasMore && !props.loadingHistory) {
          emit('loadMore')
        }
      })
    },
    {
      root: scrollRef.value,
      rootMargin: '24px',
      threshold: 0,
    },
  )

  observer.observe(sentinelRef.value)
}

watch(() => props.loadingHistory, () => {
  setupObserver()
})

onMounted(() => {
  setupObserver()
})

onBeforeUnmount(() => {
  observer?.disconnect()
})

defineExpose({
  scrollToBottom,
  captureScrollSnapshot,
  restoreScrollAfterPrepend,
})
</script>

<template>
  <div ref="scrollRef" class="no-scrollbar flex-1 overflow-y-auto rounded-[28px] border border-white/15 bg-white/10 p-5 backdrop-blur">
    <div ref="sentinelRef" class="h-1" />

    <div v-if="hasMore" class="mb-4 flex justify-center">
      <button type="button" class="btn btn-sm border-white/20 bg-white/15 text-white hover:bg-white/25" @click="emit('loadMore')">
        {{ loadingHistory ? '加载中...' : '加载更早消息' }}
      </button>
    </div>

    <div class="space-y-4">
      <MessageBubble
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />
    </div>
  </div>
</template>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}

.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
