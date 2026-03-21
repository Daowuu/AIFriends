<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import AppIcon from './components/AppIcon.vue'
import { useUserStore } from './stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const searchQuery = ref('')

const primaryNavItems = [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/friends', label: '好友', icon: 'friend' },
  { to: '/workspace', label: '创作', icon: 'create' },
] as const

const isChatRoute = computed(() => route.name === 'chat')
const showSearchAction = computed(() => route.name !== 'login' && route.name !== 'register')

const handleSearch = async () => {
  const query = searchQuery.value.trim()
  await router.push({
    name: 'home',
    query: query ? { q: query } : {},
  })
}

const handleLogout = async () => {
  await user.logout()
  await router.push({ name: 'home' })
}

onMounted(() => {
  void user.ensureUserLoaded()
})

watch(() => route.query.q, (value) => {
  searchQuery.value = String(value || '')
}, { immediate: true })
</script>

<template>
  <div data-theme="cupcake" class="min-h-screen bg-[#f9fafb]">
    <div class="flex min-h-screen">
      <aside
        v-if="!isChatRoute"
        class="hidden w-[230px] shrink-0 border-r border-base-200 bg-base-100 lg:flex lg:flex-col"
      >
        <nav class="flex-1 px-5 py-4">
          <ul class="space-y-2">
            <li v-for="item in primaryNavItems" :key="item.to">
              <RouterLink
                :to="item.to"
                class="flex items-center gap-3 rounded-xl px-4 py-3 text-[15px] font-semibold text-base-content/80 transition hover:bg-base-200/70"
                active-class="bg-base-200 text-base-content"
                exact-active-class="bg-base-200 text-base-content"
              >
                <AppIcon :name="item.icon" icon-class="h-5 w-5" />
                {{ item.label }}
              </RouterLink>
            </li>
          </ul>
        </nav>
        <div class="px-10 pb-6 text-sm text-base-content/10">
          {{ user.isAuthenticated ? user.displayName : 'Guest' }}
        </div>
      </aside>

      <div class="flex min-h-screen min-w-0 flex-1 flex-col">
        <header
          v-if="!isChatRoute"
          class="sticky top-0 z-20 border-b border-base-200 bg-base-100/95 backdrop-blur supports-[backdrop-filter]:bg-base-100/80"
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
                  <RouterLink
                    :to="item.to"
                    active-class="active"
                    exact-active-class="active"
                  >
                    <AppIcon :name="item.icon" icon-class="h-4 w-4" />
                    {{ item.label }}
                  </RouterLink>
                </li>
              </ul>
            </div>

            <div class="flex min-w-[180px] items-center gap-3 border-r border-base-200 pr-6">
              <AppIcon name="menu" icon-class="hidden h-5 w-5 lg:block" />
              <RouterLink to="/" class="text-[18px] font-black tracking-tight text-base-content">
                AIFriends
              </RouterLink>
            </div>

            <div class="flex flex-1 justify-center">
              <label
                class="input input-bordered flex h-11 w-full max-w-[580px] items-center gap-3 rounded-full border-base-300 bg-base-100 px-4 shadow-none"
              >
                <AppIcon name="search" icon-class="h-4 w-4 text-base-content/45" />
                <input
                  v-model="searchQuery"
                  type="text"
                  class="grow text-sm"
                  placeholder="搜索你感兴趣的内容"
                  @keydown.enter.prevent="handleSearch"
                />
              </label>
              <button
                v-if="showSearchAction"
                class="btn btn-ghost ml-2 hidden rounded-full border border-base-300 px-5 lg:inline-flex"
                @click="handleSearch"
              >
                <AppIcon name="search" icon-class="h-4 w-4" />
                搜索
              </button>
            </div>

            <div v-if="!user.isAuthenticated" class="ml-auto flex items-center gap-2">
              <RouterLink to="/login" class="btn btn-ghost rounded-xl px-3 text-base font-bold">
                登录
              </RouterLink>
            </div>

            <div v-else class="dropdown dropdown-end ml-auto">
              <label tabindex="0" class="btn btn-ghost flex items-center gap-3 rounded-xl px-3">
                <div class="grid h-10 w-10 place-items-center overflow-hidden rounded-full bg-base-200 font-bold">
                  <img
                    v-if="user.userInfo?.avatar"
                    :src="user.userInfo.avatar"
                    alt="用户头像"
                    class="h-full w-full object-cover"
                  >
                  <span v-else>{{ user.avatarText }}</span>
                </div>
                <div class="hidden text-left sm:block">
                  <div class="text-sm font-bold">{{ user.displayName }}</div>
                  <div class="text-xs text-base-content/45">@{{ user.userInfo?.username }}</div>
                </div>
              </label>
              <ul
                tabindex="0"
                class="menu dropdown-content z-20 mt-3 w-52 rounded-box border border-base-200 bg-base-100 p-2 shadow"
              >
                <li class="menu-title">
                  <span>{{ user.displayName }}</span>
                </li>
                <li>
                  <RouterLink to="/profile">
                    <AppIcon name="profile" icon-class="h-4 w-4" />
                    编辑资料
                  </RouterLink>
                </li>
                <li>
                  <RouterLink to="/settings/api">
                    <AppIcon name="settings" icon-class="h-4 w-4" />
                    API 设置
                  </RouterLink>
                </li>
                <li v-if="user.userInfo">
                  <RouterLink :to="`/space/${user.userInfo.id}`">
                    <AppIcon name="friend" icon-class="h-4 w-4" />
                    我的空间
                  </RouterLink>
                </li>
                <li>
                  <RouterLink to="/workspace">
                    <AppIcon name="spark" icon-class="h-4 w-4" />
                    我的角色
                  </RouterLink>
                </li>
                <li>
                  <button type="button" @click="handleLogout">
                    <AppIcon name="logout" icon-class="h-4 w-4" />
                    退出登录
                  </button>
                </li>
              </ul>
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
