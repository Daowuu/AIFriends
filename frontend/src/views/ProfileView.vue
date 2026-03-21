<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import ImageCropField from '@/components/ImageCropField.vue'
import { useUserStore } from '@/stores/user'

const user = useUserStore()

const username = ref('')
const displayName = ref('')
const bio = ref('')
const avatarPreview = ref('')
const avatarFile = ref<File | null>(null)
const pending = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

watch(() => user.userInfo, (info) => {
  username.value = info?.username ?? ''
  displayName.value = info?.display_name ?? ''
  bio.value = info?.bio ?? ''
  avatarPreview.value = info?.avatar ?? ''
  avatarFile.value = null
}, { immediate: true })

const avatarFallback = computed(() => user.avatarText)

const handleSubmit = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  pending.value = true

  try {
    const formData = new FormData()
    formData.append('username', username.value.trim())
    formData.append('display_name', displayName.value.trim())
    formData.append('bio', bio.value.trim())

    if (avatarFile.value) {
      formData.append('avatar', avatarFile.value)
    } else if (!avatarPreview.value && user.userInfo?.avatar) {
      formData.append('remove_avatar', 'true')
    }

    await user.updateProfile(formData)
    successMessage.value = '资料已更新。'
  } catch (error: unknown) {
    errorMessage.value = '保存失败，请稍后重试。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <section class="mx-auto max-w-6xl p-6">
    <div class="mb-8">
      <h1 class="text-3xl font-black tracking-tight">编辑资料</h1>
      <p class="mt-2 text-sm text-base-content/60">
        更新用户名、昵称、简介和头像，保存后导航栏会即时同步。
      </p>
      <RouterLink to="/settings/api" class="btn btn-ghost mt-4 rounded-full border border-base-300 px-5">
        进入模型 API 设置
      </RouterLink>
    </div>

    <div class="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
      <div class="space-y-6">
        <div class="rounded-[32px] border border-base-200 bg-base-100 p-6 shadow-sm">
          <div class="flex flex-col items-center text-center">
            <div class="grid h-28 w-28 place-items-center overflow-hidden rounded-full bg-base-200 text-3xl font-black">
              <img
                v-if="avatarPreview"
                :src="avatarPreview"
                alt="当前头像"
                class="h-full w-full object-cover"
              >
              <span v-else>{{ avatarFallback }}</span>
            </div>
            <h2 class="mt-4 text-xl font-black">{{ displayName || username || '未命名用户' }}</h2>
            <p class="mt-1 text-sm text-base-content/50">@{{ username || 'username' }}</p>
            <p class="mt-4 text-sm leading-7 text-base-content/60">
              {{ bio || '还没有填写简介。' }}
            </p>
          </div>
        </div>

        <ImageCropField
          title="用户头像"
          helper="建议使用主体靠中间的方图，头像会导出为轻量 WebP。"
          :model-value="avatarPreview"
          :viewport-type="'circle'"
          :output-width="512"
          :output-format="'webp'"
          :output-quality="0.9"
          :max-file-size-m-b="8"
          @change="({ file, preview }) => {
            avatarFile = file
            avatarPreview = preview
          }"
        />
      </div>

      <form class="space-y-6" @submit.prevent="handleSubmit">
        <div class="rounded-[32px] border border-base-200 bg-base-100 p-6 shadow-sm">
          <h2 class="text-lg font-black">基础信息</h2>
          <div class="mt-5 grid gap-5 md:grid-cols-2">
            <label class="form-control">
              <span class="mb-2 text-sm font-bold text-base-content/70">用户名</span>
              <input
                v-model="username"
                type="text"
                maxlength="64"
                class="input input-bordered h-12 w-full"
                placeholder="登录用户名"
              >
            </label>

            <label class="form-control">
              <span class="mb-2 text-sm font-bold text-base-content/70">展示名</span>
              <input
                v-model="displayName"
                type="text"
                maxlength="64"
                class="input input-bordered h-12 w-full"
                placeholder="页面显示昵称"
              >
            </label>
          </div>

          <div class="mt-6 border-t border-base-200 pt-5">
            <label for="profile-bio" class="block text-sm font-bold text-base-content/70">简介</label>
            <textarea
              id="profile-bio"
              v-model="bio"
              class="textarea textarea-bordered mt-3 min-h-44 w-full"
              maxlength="2000"
              placeholder="介绍一下你自己，或者写下你想让别人看到的风格说明。"
            />
          </div>
        </div>

        <div class="rounded-[32px] border border-base-200 bg-base-100 p-6 shadow-sm">
          <div v-if="errorMessage" class="alert alert-error mb-4 text-sm">{{ errorMessage }}</div>
          <div v-if="successMessage" class="alert alert-success mb-4 text-sm">{{ successMessage }}</div>
          <button type="submit" class="btn btn-primary w-full md:w-auto" :disabled="pending">
            {{ pending ? '保存中...' : '保存资料' }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>
