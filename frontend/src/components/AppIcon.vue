<script setup lang="ts">
withDefaults(defineProps<{
  name: 'create' | 'friend' | 'game' | 'home' | 'keyboard' | 'logout' | 'menu' | 'profile' | 'search' | 'settings' | 'spark'
  iconClass?: string
}>(), {
  iconClass: 'h-5 w-5',
})
</script>

<template>
  <svg
    v-if="name === 'create'"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
  >
    <rect x="3" y="3" width="18" height="18" rx="4" ry="4" />
    <line x1="12" y1="7" x2="12" y2="17" />
    <line x1="7" y1="12" x2="17" y2="12" />
  </svg>

  <svg
    v-else-if="name === 'friend'"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
  >
    <circle cx="12" cy="8" r="4" />
    <path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
  </svg>

  <svg
    v-else-if="name === 'game'"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
  >
    <rect x="3" y="3" width="18" height="18" rx="4" ry="4" />
    <path d="M8 8h.01" />
    <path d="M16 8h.01" />
    <path d="M8 16h.01" />
    <path d="M16 16h.01" />
    <path d="M12 12h.01" />
  </svg>

  <svg
    v-else-if="name === 'home'"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
  >
    <path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8" />
    <path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
  </svg>

  <svg
    v-else-if="name === 'keyboard'"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
  >
    <rect x="2" y="6" width="20" height="12" rx="2" ry="2" />
    <line x1="6" y1="10" x2="6.01" y2="10" />
    <line x1="10" y1="10" x2="10.01" y2="10" />
    <line x1="14" y1="10" x2="14.01" y2="10" />
    <line x1="18" y1="10" x2="18.01" y2="10" />
    <line x1="5" y1="13" x2="5.01" y2="13" />
    <line x1="9" y1="13" x2="9.01" y2="13" />
    <line x1="13" y1="13" x2="13.01" y2="13" />
    <line x1="17" y1="13" x2="17.01" y2="13" />
    <line x1="7" y1="16" x2="17" y2="16" />
  </svg>

  <svg
    v-else-if="name === 'settings'"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
  >
    <circle cx="12" cy="12" r="3.2" />
    <path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a1.8 1.8 0 0 1 0 2.5 1.8 1.8 0 0 1-2.5 0l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a1.8 1.8 0 0 1-1.8 1.8 1.8 1.8 0 0 1-1.8-1.8v-.2a1 1 0 0 0-.7-.9 1 1 0 0 0-1.1.2l-.1.1a1.8 1.8 0 0 1-2.5 0 1.8 1.8 0 0 1 0-2.5l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a1.8 1.8 0 0 1-1.8-1.8A1.8 1.8 0 0 1 4 10.4h.2a1 1 0 0 0 .9-.7 1 1 0 0 0-.2-1.1l-.1-.1a1.8 1.8 0 0 1 0-2.5 1.8 1.8 0 0 1 2.5 0l.1.1a1 1 0 0 0 1.1.2 1 1 0 0 0 .6-.9V4A1.8 1.8 0 0 1 10.9 2.2 1.8 1.8 0 0 1 12.7 4v.2a1 1 0 0 0 .7.9 1 1 0 0 0 1.1-.2l.1-.1a1.8 1.8 0 0 1 2.5 0 1.8 1.8 0 0 1 0 2.5l-.1.1a1 1 0 0 0-.2 1.1 1 1 0 0 0 .9.6h.2a1.8 1.8 0 0 1 1.8 1.8 1.8 1.8 0 0 1-1.8 1.8h-.2a1 1 0 0 0-.9.7z" />
  </svg>

  <svg
    v-else-if="name === 'spark'"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
  >
    <path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6L12 3z" />
    <path d="M5 16l.8 2.2L8 19l-2.2.8L5 22l-.8-2.2L2 19l2.2-.8L5 16z" />
    <path d="M19 14l1 2.8L23 18l-3 1.2L19 22l-1-2.8L15 18l3-1.2L19 14z" />
  </svg>

  <svg
    v-else-if="name === 'menu'"
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
  >
    <path d="M4 6h16M4 12h16M4 18h16" />
  </svg>

  <svg
    v-else-if="name === 'profile'"
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke-width="1.8"
    stroke="currentColor"
    :class="iconClass"
  >
    <path
      stroke-linecap="round"
      stroke-linejoin="round"
      d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
    />
    <path
      stroke-linecap="round"
      stroke-linejoin="round"
      d="M4.5 20.25a7.5 7.5 0 0115 0"
    />
  </svg>

  <svg
    v-else-if="name === 'logout'"
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke-width="1.8"
    stroke="currentColor"
    :class="iconClass"
  >
    <path
      stroke-linecap="round"
      stroke-linejoin="round"
      d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6A2.25 2.25 0 005.25 5.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15"
    />
    <path
      stroke-linecap="round"
      stroke-linejoin="round"
      d="M19.2 12H8.5"
    />
    <path
      stroke-linecap="round"
      stroke-linejoin="round"
      d="M15.5 7.8l3.7 4.2-3.7 4.2"
    />
  </svg>

  <svg
    v-else
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 64 64"
    fill="none"
    :class="iconClass"
    role="img"
    aria-label="Search icon"
  >
    <g stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="26" cy="26" r="14" />
      <path d="M37.5 37.5L50 50" />
    </g>
  </svg>
</template>
