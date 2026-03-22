<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import AppIcon from './components/AppIcon.vue'

const route = useRoute()
const router = useRouter()
const searchQuery = ref('')

const primaryNavItems = [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/studio', label: 'Studio', icon: 'create' },
] as const

const isChatRoute = computed(() => route.name === 'chat')

const handleSearch = async () => {
  const query = searchQuery.value.trim()
  await router.push({
    name: 'home',
    query: query ? { q: query } : {},
  })
}

watch(() => route.query.q, (value) => {
  searchQuery.value = String(value || '')
}, { immediate: true })
</script>

<template>
  <div
    data-theme="cupcake"
    class="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(244,211,94,0.18),_transparent_24%),radial-gradient(circle_at_bottom_right,_rgba(52,211,153,0.14),_transparent_22%),linear-gradient(180deg,#fcfbf7_0%,#f6f3ec_100%)]"
  >
    <div class="flex min-h-screen">
      <aside
        v-if="!isChatRoute"
        class="hidden w-[248px] shrink-0 border-r border-[#ded4c3] bg-[linear-gradient(180deg,rgba(255,251,243,0.9),rgba(248,243,232,0.92))] backdrop-blur lg:flex lg:flex-col"
      >
        <div class="border-b border-[#e6ddcd] px-5 py-6">
          <RouterLink to="/" class="inline-flex items-center gap-3 text-[#1b2c27]">
            <span class="grid h-11 w-11 place-items-center rounded-2xl bg-[#16231f] text-[#f6ead2] shadow-[0_10px_24px_rgba(22,35,31,0.18)]">
              <AppIcon name="spark" icon-class="h-5 w-5" />
            </span>
            <span>
              <span class="block text-lg font-black tracking-tight">AIFriends</span>
              <span class="block text-xs font-bold uppercase tracking-[0.24em] text-[#8a7757]">AI Character Studio</span>
            </span>
          </RouterLink>
        </div>

        <nav class="flex-1 px-5 py-5">
          <ul class="space-y-2">
            <li v-for="item in primaryNavItems" :key="item.to">
              <RouterLink
                :to="item.to"
                class="flex items-center gap-3 rounded-2xl px-4 py-3 text-[15px] font-semibold text-[#43514b] transition hover:bg-white/80 hover:text-[#15231f]"
                active-class="bg-[#16231f] text-[#f7f1e5] shadow-[0_10px_22px_rgba(22,35,31,0.14)]"
                exact-active-class="bg-[#16231f] text-[#f7f1e5] shadow-[0_10px_22px_rgba(22,35,31,0.14)]"
              >
                <AppIcon :name="item.icon" icon-class="h-5 w-5" />
                {{ item.label }}
              </RouterLink>
            </li>
          </ul>
        </nav>
        <div class="px-5 pb-6">
          <div class="rounded-[24px] border border-[#e3d9c7] bg-white/72 px-4 py-4 text-sm text-[#56635d] shadow-sm">
            <div class="text-xs font-black uppercase tracking-[0.2em] text-[#8a7757]">Workflow</div>
            <div class="mt-2 font-bold text-[#1b2c27]">角色定义 · 试聊试听 · 正式聊天</div>
            <div class="mt-1 text-xs">单实例 AI 项目，只保留角色、会话和运行时配置。</div>
          </div>
        </div>
      </aside>

      <div class="flex min-h-screen min-w-0 flex-1 flex-col">
        <header
          v-if="!isChatRoute"
          class="sticky top-0 z-20 border-b border-[#e5dccd] bg-[rgba(252,249,242,0.82)] backdrop-blur supports-[backdrop-filter]:bg-[rgba(252,249,242,0.72)]"
        >
          <div class="flex h-[74px] items-center gap-4 px-4 sm:px-6">
            <div class="dropdown lg:hidden">
              <label tabindex="0" class="btn btn-ghost btn-square">
                <AppIcon name="menu" icon-class="h-5 w-5" />
              </label>
              <ul
                tabindex="0"
                class="menu dropdown-content z-20 mt-3 w-56 rounded-box border border-base-200 bg-base-100 p-2 shadow"
              >
                <li v-for="item in primaryNavItems" :key="item.to">
                  <RouterLink :to="item.to" active-class="active" exact-active-class="active">
                    <AppIcon :name="item.icon" icon-class="h-4 w-4" />
                    {{ item.label }}
                  </RouterLink>
                </li>
              </ul>
            </div>

            <div class="flex min-w-[180px] items-center gap-3 border-r border-[#e6ddcd] pr-6">
              <AppIcon name="menu" icon-class="hidden h-5 w-5 lg:block" />
              <RouterLink to="/" class="text-[18px] font-black tracking-tight text-[#15231f]">
                AIFriends
              </RouterLink>
            </div>

            <div class="flex flex-1 justify-center">
              <label
                class="flex h-12 w-full max-w-[580px] items-center gap-3 rounded-full border border-[#d9cdb6] bg-white/86 px-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]"
              >
                <AppIcon name="search" icon-class="h-4 w-4 shrink-0 text-[#7e6e56]" />
                <input
                  v-model="searchQuery"
                  type="text"
                  class="h-full grow bg-transparent text-[15px] font-semibold leading-none text-[#22302b] outline-none placeholder:font-semibold placeholder:text-[#9b9387]"
                  placeholder="搜索角色、设定或 Prompt"
                  @keydown.enter.prevent="handleSearch"
                >
              </label>
              <button
                class="ml-2 hidden h-12 items-center gap-2 rounded-full border border-[#d4c7ae] bg-white/72 px-6 text-[15px] font-bold leading-none text-[#22302b] transition hover:bg-[#fff7e7] lg:inline-flex"
                @click="handleSearch"
              >
                <AppIcon name="search" icon-class="h-4 w-4" />
                搜索
              </button>
            </div>
          </div>
        </header>

        <main class="min-w-0 flex-1">
          <RouterView />
        </main>
      </div>
    </div>
  </div>
</template>
