<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import api from '@/api/http'
import type {
  AIProviderOption,
  AIRuntimeChatProviderSummary,
  AISettings,
  AIRuntimeSummary,
} from '@/types/ai-settings'

const props = withDefaults(defineProps<{
  embedded?: boolean
}>(), {
  embedded: false,
})

const chatSavePending = ref(false)
const asrSavePending = ref(false)
const testPending = ref(false)
const testAsrPending = ref(false)
const loading = ref(true)
const chatErrorMessage = ref('')
const chatSuccessMessage = ref('')
const asrErrorMessage = ref('')
const asrSuccessMessage = ref('')
const testMessage = ref('')
const testErrorMessage = ref('')
const testAsrMessage = ref('')
const testAsrErrorMessage = ref('')

const provider = ref<AIProviderOption['value']>('openai')
const lastProvider = ref<AIProviderOption['value']>('openai')
const apiBase = ref('')
const modelName = ref('')
const apiKey = ref('')
const hasExistingApiKey = ref(false)
const maskedApiKey = ref('')
const asrApiBase = ref('')
const asrModelName = ref('')
const ttsModelName = ref('')
const asrApiKey = ref('')
const hasExistingAsrApiKey = ref(false)
const maskedAsrApiKey = ref('')
const providerOptions = ref<AIProviderOption[]>([])
const runtimeSummary = ref<AIRuntimeSummary | null>(null)
const chatProviders = ref<AIRuntimeChatProviderSummary[]>([])

const selectedProvider = computed(() => (
  providerOptions.value.find((item) => item.value === provider.value) || providerOptions.value[0]
))
const busy = computed(() => (
  chatSavePending.value
  || asrSavePending.value
  || testPending.value
  || testAsrPending.value
))

const resolvedApiBasePreview = computed(() => apiBase.value.trim() || selectedProvider.value?.default_api_base || '')
const resolvedModelPreview = computed(() => modelName.value.trim() || selectedProvider.value?.default_model_name || '')
const resolvedAsrApiBasePreview = computed(() => asrApiBase.value.trim() || 'https://dashscope.aliyuncs.com/compatible-mode/v1')
const resolvedAsrModelPreview = computed(() => asrModelName.value.trim() || 'qwen3-asr-flash')
const resolvedTtsModelPreview = computed(() => ttsModelName.value.trim() || 'cosyvoice-v3.5-plus')

const applySettings = (settings: AISettings) => {
  provider.value = settings.provider
  lastProvider.value = settings.provider
  apiBase.value = settings.api_base
  modelName.value = settings.model_name
  hasExistingApiKey.value = settings.has_api_key
  maskedApiKey.value = settings.masked_api_key
  apiKey.value = ''
  asrApiBase.value = settings.asr_api_base
  asrModelName.value = settings.asr_model_name
  ttsModelName.value = settings.tts_model_name
  hasExistingAsrApiKey.value = settings.has_asr_api_key
  maskedAsrApiKey.value = settings.masked_asr_api_key
  asrApiKey.value = ''
}

type SettingsResponse = {
  settings: AISettings
  chat_providers: AIRuntimeChatProviderSummary[]
  providers: AIProviderOption[]
  runtime_summary: AIRuntimeSummary
}

const applyResponse = (payload: SettingsResponse) => {
  providerOptions.value = payload.providers
  applySettings(payload.settings)
  chatProviders.value = payload.chat_providers
  runtimeSummary.value = payload.runtime_summary
}

const loadSettings = async () => {
  loading.value = true
  chatErrorMessage.value = ''
  asrErrorMessage.value = ''

  try {
    const response = await api.get<SettingsResponse>('/runtime/settings/')
    applyResponse(response.data)
  } catch (error: unknown) {
    const message = '加载 API 设置失败，请稍后重试。'
    chatErrorMessage.value = message
    asrErrorMessage.value = message
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      const detail = response?.data?.detail || message
      chatErrorMessage.value = detail
      asrErrorMessage.value = detail
    }
  } finally {
    loading.value = false
  }
}

const resetChatFeedback = () => {
  chatErrorMessage.value = ''
  chatSuccessMessage.value = ''
  testMessage.value = ''
  testErrorMessage.value = ''
}

const resetAsrFeedback = () => {
  asrErrorMessage.value = ''
  asrSuccessMessage.value = ''
  testAsrMessage.value = ''
  testAsrErrorMessage.value = ''
}

const handleProviderChange = () => {
  const previousProvider = providerOptions.value.find((item) => item.value === lastProvider.value)
  const nextProvider = providerOptions.value.find((item) => item.value === provider.value)
  const nextProviderSummary = chatProviders.value.find((item) => item.provider === provider.value)

  if (nextProviderSummary) {
    apiBase.value = nextProviderSummary.api_base || nextProvider?.default_api_base || ''
    modelName.value = nextProviderSummary.model_name || nextProvider?.default_model_name || ''
    hasExistingApiKey.value = nextProviderSummary.has_api_key
    maskedApiKey.value = nextProviderSummary.masked_api_key
    apiKey.value = ''
    lastProvider.value = provider.value
    resetChatFeedback()
    resetAsrFeedback()
    return
  }

  if (nextProvider) {
    const previousDefaultApiBase = previousProvider?.default_api_base || ''
    const previousDefaultModelName = previousProvider?.default_model_name || ''

    if (!apiBase.value.trim() || apiBase.value.trim() === previousDefaultApiBase) {
      apiBase.value = nextProvider.default_api_base || ''
    }

    if (!modelName.value.trim() || modelName.value.trim() === previousDefaultModelName) {
      modelName.value = nextProvider.default_model_name || ''
    }
  }

  hasExistingApiKey.value = false
  maskedApiKey.value = ''
  apiKey.value = ''
  lastProvider.value = provider.value
  resetChatFeedback()
  resetAsrFeedback()
}

const handleSaveChatConfig = async () => {
  chatSavePending.value = true
  resetChatFeedback()

  try {
    const response = await api.post<SettingsResponse>('/runtime/settings/', {
      provider: provider.value,
      api_base: apiBase.value.trim(),
      model_name: modelName.value.trim(),
      api_key: apiKey.value.trim(),
    })

    applyResponse(response.data)
    chatSuccessMessage.value = '聊天配置已保存。'
  } catch (error: unknown) {
    chatErrorMessage.value = '聊天配置保存失败，请稍后重试。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      chatErrorMessage.value = response?.data?.detail || chatErrorMessage.value
    }
  } finally {
    chatSavePending.value = false
  }
}

const handleSaveAsrConfig = async () => {
  asrSavePending.value = true
  resetAsrFeedback()

  try {
    const response = await api.post<SettingsResponse>('/runtime/settings/', {
      asr_api_base: asrApiBase.value.trim(),
      asr_model_name: asrModelName.value.trim(),
      tts_model_name: ttsModelName.value.trim(),
      asr_api_key: asrApiKey.value.trim(),
    })

    applyResponse(response.data)
    asrSuccessMessage.value = '语音配置已保存。'
  } catch (error: unknown) {
    asrErrorMessage.value = '语音配置保存失败，请稍后重试。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      asrErrorMessage.value = response?.data?.detail || asrErrorMessage.value
    }
  } finally {
    asrSavePending.value = false
  }
}

const handleTestConnection = async () => {
  testPending.value = true
  testMessage.value = ''
  testErrorMessage.value = ''
  chatSuccessMessage.value = ''
  chatErrorMessage.value = ''

  try {
    const response = await api.post<{
      detail: string
      reply_preview?: string
      resolved?: {
        provider: string
        api_base: string
        model_name: string
      }
    }>('/runtime/settings/test/', {
      provider: provider.value,
      api_base: apiBase.value.trim(),
      model_name: modelName.value.trim(),
      api_key: apiKey.value.trim(),
    })

    const preview = response.data.reply_preview ? ` 返回示例：${response.data.reply_preview}` : ''
    testMessage.value = `${response.data.detail}${preview}`
  } catch (error: unknown) {
    testErrorMessage.value = '连接测试失败，请检查配置。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      testErrorMessage.value = response?.data?.detail || testErrorMessage.value
    }
  } finally {
    testPending.value = false
  }
}

const handleTestAsrConnection = async () => {
  testAsrPending.value = true
  testAsrMessage.value = ''
  testAsrErrorMessage.value = ''
  asrSuccessMessage.value = ''
  asrErrorMessage.value = ''

  try {
    const response = await api.post<{
      detail: string
      reply_preview?: string
      resolved?: {
        api_base: string
        model_name: string
      }
    }>('/runtime/settings/test_asr/', {
      asr_api_base: asrApiBase.value.trim(),
      asr_model_name: asrModelName.value.trim(),
      asr_api_key: asrApiKey.value.trim(),
    })

    const preview = response.data.reply_preview ? ` 返回示例：${response.data.reply_preview}` : ''
    testAsrMessage.value = `${response.data.detail}${preview}`
  } catch (error: unknown) {
    testAsrErrorMessage.value = 'ASR 测试失败，请检查配置。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      testAsrErrorMessage.value = response?.data?.detail || testAsrErrorMessage.value
    }
  } finally {
    testAsrPending.value = false
  }
}

onMounted(() => {
  void loadSettings()
})
</script>

<template>
  <section :class="props.embedded ? '' : 'mx-auto w-full max-w-[104rem] px-4 py-8 sm:px-6 lg:px-8'">
    <div
      :class="props.embedded
        ? 'rounded-[32px] border border-base-200 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(248,250,252,0.95))] p-5 shadow-sm sm:p-6'
        : 'rounded-[36px] border border-base-200 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(248,250,252,0.95))] p-6 shadow-[0_20px_80px_rgba(15,23,42,0.08)] sm:p-8'"
    >
      <div class="flex flex-col gap-5 border-b border-base-200/80 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div class="max-w-3xl">
          <div class="text-xs font-black uppercase tracking-[0.28em] text-sky-600">Runtime Config</div>
          <h1 class="mt-3 text-3xl font-black tracking-tight text-base-content sm:text-4xl">运行时配置</h1>
          <p class="mt-3 text-sm leading-7 text-base-content/65 sm:text-[15px]">
            这里统一管理聊天、ASR 和语音播报配置。页面直接编辑 `backend/.env` 里的 `AI_RUNTIME_CONFIG_JSON`；如果你维护多套聊天提供方，只需要切换 `active.chat_provider`。
          </p>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="rounded-[24px] border border-base-200 bg-white px-4 py-3 shadow-sm">
            <div class="text-xs font-bold uppercase tracking-[0.18em] text-base-content/45">聊天模式</div>
            <div class="mt-2 text-sm font-semibold text-base-content">
              {{ runtimeSummary?.chat_runtime?.enabled ? '已配置聊天运行时' : '等待补全配置' }}
            </div>
          </div>
          <div class="rounded-[24px] border border-base-200 bg-white px-4 py-3 shadow-sm">
            <div class="text-xs font-bold uppercase tracking-[0.18em] text-base-content/45">ASR 模式</div>
            <div class="mt-2 text-sm font-semibold text-base-content">
              {{ runtimeSummary?.asr_runtime?.enabled ? '已配置语音运行时' : '等待补全配置' }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="loading" class="flex min-h-[320px] items-center justify-center">
        <span class="loading loading-spinner loading-lg text-primary" />
      </div>

      <div v-else class="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1.42fr)_minmax(20rem,0.9fr)]">
        <form class="space-y-6" @submit.prevent>
          <div class="overflow-hidden rounded-[32px] border border-base-200 bg-white shadow-[0_14px_50px_rgba(15,23,42,0.06)]">
            <div class="flex flex-col gap-5 border-b border-base-200/80 px-6 py-6 sm:px-7 lg:flex-row lg:items-start lg:justify-between">
              <div class="max-w-2xl">
                <div class="inline-flex rounded-full bg-sky-50 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-sky-700">
                  Chat
                </div>
                <h2 class="mt-3 text-2xl font-black tracking-tight text-base-content">聊天模型配置</h2>
                <p class="mt-2 text-sm leading-7 text-base-content/60">
                  把提供方、模型、网关地址和聊天密钥收在一张卡片里。保存有效配置后，聊天运行时会自动生效。
                </p>
              </div>

              <div class="grid gap-3 sm:min-w-[14rem]">
                <div class="rounded-[24px] border border-base-200 bg-slate-50 px-4 py-3 text-sm shadow-sm">
                  <div class="text-xs font-bold uppercase tracking-[0.18em] text-base-content/45">聊天 Key</div>
                  <div class="mt-2 font-semibold text-base-content">
                    {{ hasExistingApiKey ? maskedApiKey : '未保存' }}
                  </div>
                </div>
                <div class="rounded-[24px] border border-base-200 bg-slate-50 px-4 py-3 text-sm shadow-sm">
                  <div class="text-xs font-bold uppercase tracking-[0.18em] text-base-content/45">当前配置</div>
                  <div class="mt-2 font-semibold text-base-content/75">
                    读取 `backend/.env` 当前编辑 provider
                  </div>
                </div>
              </div>
            </div>

            <div class="space-y-6 px-6 py-6 sm:px-7">
              <div class="grid gap-5 md:grid-cols-2">
                <label class="form-control">
                  <span class="mb-2 text-sm font-bold text-base-content/70">模型提供方</span>
                  <select v-model="provider" class="select select-bordered w-full bg-base-50" @change="handleProviderChange">
                    <option v-for="item in providerOptions" :key="item.value" :value="item.value">
                      {{ item.label }}
                    </option>
                  </select>
                  <span class="mt-2 text-xs leading-6 text-base-content/55">
                    {{ selectedProvider?.helper || '请选择一个兼容 OpenAI Chat Completions 的提供方。' }}
                  </span>
                </label>

                <label class="form-control">
                  <span class="mb-2 text-sm font-bold text-base-content/70">模型名</span>
                  <input
                    v-model="modelName"
                    type="text"
                    maxlength="128"
                    class="input input-bordered w-full bg-base-50"
                    :placeholder="selectedProvider?.default_model_name || '例如 qwen-plus / deepseek-chat / gpt-4o-mini'"
                  >
                  <span class="mt-2 text-xs leading-6 text-base-content/55">
                    留空时自动使用该提供方的默认建议模型。
                  </span>
                </label>

                <label class="form-control md:col-span-2">
                  <span class="mb-2 text-sm font-bold text-base-content/70">API Base</span>
                  <input
                    v-model="apiBase"
                    type="text"
                    maxlength="512"
                    class="input input-bordered w-full bg-base-50"
                    :placeholder="selectedProvider?.default_api_base || 'https://your-gateway.example.com/v1'"
                  >
                  <span class="mt-2 text-xs leading-6 text-base-content/55">
                    如果使用官方默认地址，可以留空；如果接代理网关，建议明确写全地址。
                  </span>
                </label>

                <label class="form-control md:col-span-2">
                  <span class="mb-2 text-sm font-bold text-base-content/70">API Key</span>
                  <input
                    v-model="apiKey"
                    type="password"
                    maxlength="512"
                    class="input input-bordered w-full bg-base-50"
                    placeholder="留空表示保持当前已保存的密钥不变"
                  >
                  <span class="mt-2 text-xs leading-6 text-base-content/55">
                    输入新 key 会覆盖旧值；留空则保持当前已保存的聊天 key。当前保存的是 {{ hasExistingApiKey ? maskedApiKey : '无' }}。
                  </span>
                </label>
              </div>

              <div v-if="testErrorMessage" class="alert alert-error text-sm shadow-sm">{{ testErrorMessage }}</div>
              <div v-if="testMessage" class="alert alert-info text-sm shadow-sm">{{ testMessage }}</div>
              <div v-if="chatErrorMessage" class="alert alert-error text-sm shadow-sm">{{ chatErrorMessage }}</div>
              <div v-if="chatSuccessMessage" class="alert alert-success text-sm shadow-sm">{{ chatSuccessMessage }}</div>
            </div>

            <div class="flex flex-col gap-3 border-t border-base-200/80 bg-slate-50/70 px-6 py-5 sm:px-7 md:flex-row md:items-center md:justify-between">
              <p class="text-sm leading-7 text-base-content/55">
                先测试聊天链路，再保存；这里更新的是 `.env` 当前 provider 的聊天配置和对应 API Key。
              </p>
              <div class="flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  class="btn btn-ghost border border-base-300 bg-white"
                  :disabled="busy"
                  @click="handleTestConnection"
                >
                  {{ testPending ? '测试中...' : '测试聊天配置' }}
                </button>
                <button
                  type="button"
                  class="btn btn-primary"
                  :disabled="busy"
                  @click="handleSaveChatConfig"
                >
                  {{ chatSavePending ? '保存中...' : '保存聊天配置' }}
                </button>
              </div>
            </div>
          </div>

          <div class="overflow-hidden rounded-[32px] border border-base-200 bg-white shadow-[0_14px_50px_rgba(15,23,42,0.06)]">
            <div class="flex flex-col gap-5 border-b border-base-200/80 px-6 py-6 sm:px-7 lg:flex-row lg:items-start lg:justify-between">
              <div class="max-w-2xl">
                <div class="inline-flex rounded-full bg-amber-50 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-amber-700">
                  Voice
                </div>
                <h2 class="mt-3 text-2xl font-black tracking-tight text-base-content">语音配置</h2>
                <p class="mt-2 text-sm leading-7 text-base-content/60">
                  这块统一管理语音输入和语音播报。ASR 与 TTS 共用同一套语音运行时，TTS 额外指定播报模型；保存后会自动生效。
                </p>
              </div>

              <div class="grid gap-3 sm:min-w-[14rem]">
                <div class="rounded-[24px] border border-base-200 bg-amber-50/60 px-4 py-3 text-sm shadow-sm">
                  <div class="text-xs font-bold uppercase tracking-[0.18em] text-base-content/45">语音 Key</div>
                  <div class="mt-2 font-semibold text-base-content">
                    {{ hasExistingAsrApiKey ? maskedAsrApiKey : '未保存' }}
                  </div>
                </div>
                <div class="rounded-[24px] border border-base-200 bg-amber-50/60 px-4 py-3 text-sm shadow-sm">
                  <div class="text-xs font-bold uppercase tracking-[0.18em] text-base-content/45">生效方式</div>
                  <div class="mt-2 font-semibold text-base-content/75">{{ runtimeSummary?.asr_runtime?.enabled ? '已配置语音运行时' : '等待补全配置' }}</div>
                </div>
              </div>
            </div>

            <div class="space-y-6 px-6 py-6 sm:px-7">
              <div class="grid gap-5 md:grid-cols-2">
                <label class="form-control">
                  <span class="mb-2 text-sm font-bold text-base-content/70">识别模型</span>
                  <input
                    v-model="asrModelName"
                    type="text"
                    maxlength="128"
                    class="input input-bordered w-full bg-base-50"
                    placeholder="qwen3-asr-flash"
                  >
                  <span class="mt-2 text-xs leading-6 text-base-content/55">
                    留空时默认使用 `qwen3-asr-flash`。
                  </span>
                </label>

                <label class="form-control">
                  <span class="mb-2 text-sm font-bold text-base-content/70">API Base</span>
                  <input
                    v-model="asrApiBase"
                    type="text"
                    maxlength="512"
                    class="input input-bordered w-full bg-base-50"
                    placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
                  >
                  <span class="mt-2 text-xs leading-6 text-base-content/55">
                    留空时默认使用阿里云百炼 DashScope 兼容地址。
                  </span>
                </label>

                <label class="form-control md:col-span-2">
                  <span class="mb-2 text-sm font-bold text-base-content/70">播报模型</span>
                  <input
                    v-model="ttsModelName"
                    type="text"
                    maxlength="128"
                    class="input input-bordered w-full bg-base-50"
                    placeholder="cosyvoice-v3.5-plus"
                  >
                  <span class="mt-2 text-xs leading-6 text-base-content/55">
                    角色语音播报使用这个模型。留空时默认使用 `cosyvoice-v3.5-plus`。
                  </span>
                </label>

                <label class="form-control md:col-span-2">
                  <span class="mb-2 text-sm font-bold text-base-content/70">API Key</span>
                  <input
                    v-model="asrApiKey"
                    type="password"
                    maxlength="512"
                    class="input input-bordered w-full bg-base-50"
                    placeholder="留空表示保持当前已保存的 ASR 密钥不变"
                  >
                  <span class="mt-2 text-xs leading-6 text-base-content/55">
                    输入新 key 会覆盖旧值；留空则保持当前已保存的 ASR key。当前保存的是 {{ hasExistingAsrApiKey ? maskedAsrApiKey : '无' }}。这里保存的是语音链路自己的 key，不再复用聊天配置。
                  </span>
                </label>
              </div>

              <div v-if="testAsrErrorMessage" class="alert alert-error text-sm shadow-sm">{{ testAsrErrorMessage }}</div>
              <div v-if="testAsrMessage" class="alert alert-info text-sm shadow-sm">{{ testAsrMessage }}</div>
              <div v-if="asrErrorMessage" class="alert alert-error text-sm shadow-sm">{{ asrErrorMessage }}</div>
              <div v-if="asrSuccessMessage" class="alert alert-success text-sm shadow-sm">{{ asrSuccessMessage }}</div>
            </div>

            <div class="flex flex-col gap-3 border-t border-base-200/80 bg-slate-50/70 px-6 py-5 sm:px-7 md:flex-row md:items-center md:justify-between">
              <p class="text-sm leading-7 text-base-content/55">
                这里的测试会发一段静音音频去探活，只验证 `.env` 当前激活 ASR 模型的请求链路是否可用。
              </p>
              <div class="flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  class="btn btn-ghost border border-base-300 bg-white"
                  :disabled="busy"
                  @click="handleTestAsrConnection"
                >
                  {{ testAsrPending ? '测试中...' : '测试语音识别' }}
                </button>
                <button
                  type="button"
                  class="btn btn-warning text-base-100"
                  :disabled="busy"
                  @click="handleSaveAsrConfig"
                >
                  {{ asrSavePending ? '保存中...' : '保存语音配置' }}
                </button>
              </div>
            </div>
          </div>
        </form>

        <aside class="space-y-6">
          <div class="rounded-[32px] border border-base-200 bg-white p-6 shadow-[0_14px_50px_rgba(15,23,42,0.06)]">
            <div class="text-xs font-black uppercase tracking-[0.24em] text-base-content/45">Live Preview</div>

            <div class="mt-5 space-y-4">
              <div class="rounded-[24px] border border-sky-100 bg-sky-50/60 p-4">
                <div class="flex items-center justify-between gap-3">
                  <div class="text-sm font-black text-base-content">聊天</div>
                  <div class="rounded-full bg-white px-3 py-1 text-xs font-bold text-sky-700 shadow-sm">
                    {{ runtimeSummary?.chat_runtime?.enabled ? '.env 当前激活 provider' : '等待补全配置' }}
                  </div>
                </div>
                <div class="mt-4 space-y-3 text-sm">
                  <div>
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">Provider</div>
                    <div class="mt-1 text-base-content/75">{{ selectedProvider?.label || provider }}</div>
                  </div>
                  <div>
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">API Base</div>
                    <div class="mt-1 break-all text-base-content/75">{{ resolvedApiBasePreview || '未设置' }}</div>
                  </div>
                  <div>
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">Model</div>
                    <div class="mt-1 break-all text-base-content/75">{{ resolvedModelPreview || '未设置' }}</div>
                  </div>
                </div>
              </div>

              <div class="rounded-[24px] border border-amber-100 bg-amber-50/60 p-4">
                <div class="flex items-center justify-between gap-3">
                  <div class="text-sm font-black text-base-content">语音运行时</div>
                  <div class="rounded-full bg-white px-3 py-1 text-xs font-bold text-amber-700 shadow-sm">
                    {{ runtimeSummary?.asr_runtime?.enabled ? '已配置' : '等待补全配置' }}
                  </div>
                </div>
                <div class="mt-4 space-y-3 text-sm">
                  <div>
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">API Base</div>
                    <div class="mt-1 break-all text-base-content/75">{{ resolvedAsrApiBasePreview }}</div>
                  </div>
                  <div>
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">识别模型</div>
                    <div class="mt-1 break-all text-base-content/75">{{ resolvedAsrModelPreview }}</div>
                  </div>
                  <div>
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">播报模型</div>
                    <div class="mt-1 break-all text-base-content/75">{{ resolvedTtsModelPreview }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="rounded-[32px] border border-base-200 bg-white p-6 shadow-[0_14px_50px_rgba(15,23,42,0.06)]">
            <div class="text-xs font-black uppercase tracking-[0.24em] text-base-content/45">Runtime Summary</div>
            <h2 class="mt-3 text-xl font-black text-base-content">实际生效摘要</h2>

            <div class="mt-5 space-y-4 text-sm">
              <div class="rounded-[24px] border border-base-200 bg-slate-50 p-4">
                <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">聊天 Runtime</div>
                <div class="mt-2 font-semibold text-base-content/80">
                  {{ runtimeSummary?.chat_runtime.label || '未启用' }}
                </div>
                <div class="mt-2 break-all text-base-content/65">
                  {{ runtimeSummary?.chat_runtime.model_name || '未设置模型' }}
                </div>
                <div
                  v-if="runtimeSummary?.chat_runtime_status === 'invalid'"
                  class="mt-2 text-xs leading-6 text-error"
                >
                  当前本地聊天配置不完整，系统不会再静默回退到本地假回复。
                </div>
                <div
                  v-else-if="runtimeSummary?.chat_runtime.reason"
                  class="mt-2 text-xs leading-6 text-base-content/55"
                >
                  {{ runtimeSummary.chat_runtime.reason }}
                </div>
              </div>

              <div class="rounded-[24px] border border-base-200 bg-slate-50 p-4">
                <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">ASR Runtime</div>
                <div class="mt-2 font-semibold text-base-content/80">
                  {{ runtimeSummary?.asr_runtime.label || '未启用' }}
                </div>
                <div class="mt-2 break-all text-base-content/65">
                  {{ runtimeSummary?.asr_runtime.model_name || '未设置模型' }}
                </div>
              </div>

              <div class="rounded-[24px] border border-base-200 bg-slate-50 p-4">
                <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">TTS Runtime</div>
                <div class="mt-2 font-semibold text-base-content/80">
                  {{ runtimeSummary?.tts_runtime.label || '未启用' }}
                </div>
                <div class="mt-2 break-all text-base-content/65">
                  {{ runtimeSummary?.tts_runtime.model_name || '未设置模型' }}
                </div>
              </div>

              <div class="rounded-[24px] border border-base-200 bg-slate-50 p-4">
                <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">最近编辑角色的 AI 摘要</div>
                <div v-if="runtimeSummary?.recent_character_summary" class="mt-2 space-y-1 text-base-content/75">
                  <div class="font-semibold text-base-content/85">{{ runtimeSummary.recent_character_summary.name }}</div>
                  <div>记忆模式：{{ runtimeSummary.recent_character_summary.memory_mode }}</div>
                  <div>回复风格：{{ runtimeSummary.recent_character_summary.reply_style }}</div>
                  <div>音色：{{ runtimeSummary.recent_character_summary.voice_name || '未配置' }}</div>
                </div>
                <div v-else class="mt-2 text-base-content/65">
                  还没有可展示的角色。
                </div>
              </div>

              <div class="rounded-[24px] border border-base-200 bg-slate-50 p-4">
                <div class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/45">Prompt Layers</div>
                <div class="mt-3 flex flex-wrap gap-2">
                  <span
                    v-for="layer in runtimeSummary?.prompt_layers || []"
                    :key="layer"
                    class="rounded-full border border-base-200 bg-white px-3 py-1 text-xs font-semibold text-base-content/65"
                  >
                    {{ layer }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="rounded-[32px] border border-base-200 bg-white p-6 shadow-[0_14px_50px_rgba(15,23,42,0.06)]">
            <div class="text-xs font-black uppercase tracking-[0.24em] text-base-content/45">Guidance</div>
            <h2 class="mt-3 text-xl font-black text-base-content">使用建议</h2>
            <ul class="mt-4 space-y-3 text-sm leading-7 text-base-content/60">
              <li>聊天支持阿里云百炼、DeepSeek、MiniMax、OpenAI，以及兼容 OpenAI 的自定义接口。</li>
              <li>语音识别当前只支持阿里云百炼兼容接口，建议单独保存一套稳定的 ASR 配置。</li>
              <li>如果模型名和 API Base 留空，系统会按对应模块自动补默认值。</li>
              <li>如果你维护多套聊天模型，请直接编辑 `backend/.env` 中 `AI_RUNTIME_CONFIG_JSON` 的 `active.chat_provider`。</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  </section>
</template>
