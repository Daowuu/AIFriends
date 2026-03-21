<script setup lang="ts">
withDefaults(defineProps<{
  name: string
  photo?: string
}>(), {
  photo: '',
})
</script>

<template>
  <div class="h-12 w-12 overflow-hidden rounded-2xl border border-white/30 bg-white/20 shadow-sm backdrop-blur">
    <img
      v-if="photo"
      :src="photo"
      :alt="name"
      class="h-full w-full object-cover"
    >
    <div v-else class="grid h-full w-full place-items-center text-base font-black text-white">
      {{ name.slice(0, 1) }}
    </div>
  </div>
</template>
