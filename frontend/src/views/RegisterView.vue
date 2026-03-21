<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const user = useUserStore()

const form = reactive({
  username: '',
  password: '',
  password_confirm: '',
})

const pending = ref(false)
const errorMessage = ref('')

const handleSubmit = async () => {
  pending.value = true
  errorMessage.value = ''

  try {
    await user.register(form)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch (error: any) {
    errorMessage.value = error?.response?.data?.detail || '注册失败，请稍后再试。'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <section class="flex min-h-[calc(100vh-74px)] items-center justify-center p-4 sm:p-6">
    <div
      class="grid w-full max-w-5xl overflow-hidden rounded-[2rem] border border-base-200 bg-base-100 shadow-[0_20px_70px_rgba(15,23,42,0.08)] lg:grid-cols-[1.02fr_0.98fr]"
    >
      <div class="p-6 sm:p-8 lg:p-10">
        <div class="mx-auto w-full max-w-md">
          <div class="mb-8">
            <div class="badge badge-outline badge-secondary px-3 py-3">创建账号</div>
            <h2 class="mt-4 text-3xl font-black text-base-content">注册 AIFriends</h2>
            <p class="mt-2 text-sm leading-7 text-base-content/60">
              创建新账号后会自动登录，并进入主界面。
            </p>
          </div>

          <form class="space-y-5" @submit.prevent="handleSubmit">
            <label class="form-control w-full">
              <span class="mb-2 text-sm font-semibold text-base-content/65">用户名</span>
              <input
                v-model.trim="form.username"
                type="text"
                class="input input-bordered h-12 w-full rounded-2xl border-base-300 bg-base-100 px-4"
                placeholder="至少 3 个字符"
              />
            </label>

            <label class="form-control w-full">
              <span class="mb-2 text-sm font-semibold text-base-content/65">密码</span>
              <input
                v-model="form.password"
                type="password"
                class="input input-bordered h-12 w-full rounded-2xl border-base-300 bg-base-100 px-4"
                placeholder="至少 6 个字符"
              />
            </label>

            <label class="form-control w-full">
              <span class="mb-2 text-sm font-semibold text-base-content/65">确认密码</span>
              <input
                v-model="form.password_confirm"
                type="password"
                class="input input-bordered h-12 w-full rounded-2xl border-base-300 bg-base-100 px-4"
                placeholder="请再次输入密码"
              />
            </label>

            <div v-if="errorMessage" class="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">
              {{ errorMessage }}
            </div>

            <button type="submit" class="btn btn-primary mt-3 h-12 w-full rounded-2xl border-0 text-base" :disabled="pending">
              {{ pending ? '注册中...' : '注册' }}
            </button>
          </form>

          <div class="mt-6 flex items-center justify-between text-sm text-base-content/55">
            <span>已有账号？</span>
            <RouterLink
              :to="{ name: 'login', query: route.query.redirect ? { redirect: route.query.redirect } : {} }"
              class="font-semibold text-primary"
            >
              去登录
            </RouterLink>
          </div>
        </div>
      </div>

      <aside
        class="relative hidden overflow-hidden border-l border-base-200 bg-[linear-gradient(180deg,#fff7ed_0%,#fef3c7_100%)] p-10 lg:block"
      >
        <div class="relative z-10 max-w-sm">
          <p class="text-sm font-semibold uppercase tracking-[0.28em] text-base-content/45">
            New Account
          </p>
          <h1 class="mt-4 text-4xl font-black leading-tight text-base-content">
            从这里开始搭建你的
            <span class="text-secondary">AIFriends</span>
            账号
          </h1>
          <p class="mt-5 text-base leading-8 text-base-content/65">
            这一页保持更轻的注册引导风格，和登录页形成一组，但不完全镜像，看起来不会太模板化。
          </p>

          <div class="mt-10 grid gap-3">
            <div class="rounded-2xl border border-white/70 bg-white/70 px-4 py-4 backdrop-blur">
              <p class="text-sm text-base-content/45">注册完成后</p>
              <p class="mt-1 text-lg font-bold text-base-content">自动建立基础用户资料</p>
            </div>
            <div class="rounded-2xl border border-white/70 bg-white/70 px-4 py-4 backdrop-blur">
              <p class="text-sm text-base-content/45">下一步可继续</p>
              <p class="mt-1 text-lg font-bold text-base-content">好友、创作和路由守卫</p>
            </div>
          </div>
        </div>

        <div class="absolute -left-20 top-12 h-56 w-56 rounded-full bg-secondary/10 blur-3xl"></div>
        <div class="absolute bottom-0 right-0 h-40 w-40 rounded-full bg-warning/20 blur-3xl"></div>
      </aside>
    </div>
  </section>
</template>
