<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const form = reactive({
  username: '',
  password: '',
})

const pending = ref(false)
const errorMessage = ref('')

const handleSubmit = async () => {
  pending.value = true
  errorMessage.value = ''

  try {
    await user.login(form)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch (error: any) {
    errorMessage.value = error?.response?.data?.detail || '登录失败，请稍后再试。'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <section class="flex min-h-[calc(100vh-74px)] items-center justify-center p-4 sm:p-6">
    <div
      class="grid w-full max-w-5xl overflow-hidden rounded-[2rem] border border-base-200 bg-base-100 shadow-[0_20px_70px_rgba(15,23,42,0.08)] lg:grid-cols-[0.95fr_1.05fr]"
    >
      <aside
        class="relative hidden overflow-hidden border-r border-base-200 bg-[linear-gradient(180deg,#f8fafc_0%,#eef2ff_100%)] p-10 lg:block"
      >
        <div class="relative z-10 max-w-sm">
          <p class="text-sm font-semibold uppercase tracking-[0.28em] text-base-content/45">
            Welcome Back
          </p>
          <h1 class="mt-4 text-4xl font-black leading-tight text-base-content">
            登录你的
            <span class="text-primary">AIFriends</span>
            工作区
          </h1>
          <p class="mt-5 text-base leading-8 text-base-content/65">
            进入好友、创作和后续聊天工作台。当前这块区域保留成品牌说明区，右侧专注表单输入。
          </p>

          <div class="mt-10 space-y-3">
            <div class="rounded-2xl border border-white/70 bg-white/70 px-4 py-4 backdrop-blur">
              <p class="text-sm text-base-content/45">当前接入</p>
              <p class="mt-1 text-lg font-bold text-base-content">JWT + Refresh Token</p>
            </div>
            <div class="rounded-2xl border border-white/70 bg-white/70 px-4 py-4 backdrop-blur">
              <p class="text-sm text-base-content/45">页面定位</p>
              <p class="mt-1 text-lg font-bold text-base-content">单域前后端一体化</p>
            </div>
          </div>
        </div>

        <div class="absolute -right-16 top-10 h-56 w-56 rounded-full bg-primary/10 blur-3xl"></div>
        <div class="absolute bottom-0 left-0 h-40 w-40 rounded-full bg-info/10 blur-3xl"></div>
      </aside>

      <div class="p-6 sm:p-8 lg:p-10">
        <div class="mx-auto w-full max-w-md">
          <div class="mb-8">
            <div class="badge badge-outline badge-primary px-3 py-3">账号登录</div>
            <h2 class="mt-4 text-3xl font-black text-base-content">欢迎回来</h2>
            <p class="mt-2 text-sm leading-7 text-base-content/60">
              输入用户名和密码继续访问你的账号。
            </p>
          </div>

          <form class="space-y-5" @submit.prevent="handleSubmit">
            <label class="form-control w-full">
              <span class="mb-2 text-sm font-semibold text-base-content/65">用户名</span>
              <input
                v-model.trim="form.username"
                type="text"
                class="input input-bordered h-12 w-full rounded-2xl border-base-300 bg-base-100 px-4"
                placeholder="请输入用户名"
              />
            </label>

            <label class="form-control w-full">
              <span class="mb-2 text-sm font-semibold text-base-content/65">密码</span>
              <input
                v-model="form.password"
                type="password"
                class="input input-bordered h-12 w-full rounded-2xl border-base-300 bg-base-100 px-4"
                placeholder="请输入密码"
              />
            </label>

            <div v-if="errorMessage" class="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">
              {{ errorMessage }}
            </div>

            <button type="submit" class="btn btn-primary mt-3 h-12 w-full rounded-2xl border-0 text-base" :disabled="pending">
              {{ pending ? '登录中...' : '登录' }}
            </button>
          </form>

          <div class="mt-6 flex items-center justify-between text-sm text-base-content/55">
            <span>还没有账号？</span>
            <RouterLink
              :to="{ name: 'register', query: route.query.redirect ? { redirect: route.query.redirect } : {} }"
              class="font-semibold text-primary"
            >
              去注册
            </RouterLink>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
