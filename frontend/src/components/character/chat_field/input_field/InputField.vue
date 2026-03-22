<script setup lang="ts">
import { MicVAD } from '@ricky0123/vad-web'
import ortWasmModuleUrl from '@/assets/vad-runtime/ort-wasm-simd-threaded.mjs?url'
import ortWasmBinaryUrl from '@/assets/vad-runtime/ort-wasm-simd-threaded.wasm?url'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import api from '@/api/http'

const props = withDefaults(defineProps<{
  autofocus?: boolean
  pending?: boolean
  disabled?: boolean
  allowVoiceMode?: boolean
  asrEndpoint?: string
  disabledReason?: string
  placeholder?: string
  resetToken?: number
}>(), {
  autofocus: false,
  pending: false,
  disabled: false,
  allowVoiceMode: true,
  asrEndpoint: '/session/asr/',
  disabledReason: '',
  placeholder: '输入一句话，开始聊天。',
  resetToken: 0,
})

const emit = defineEmits<{
  send: [message: string]
  stop: []
}>()

const message = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const inputMode = ref<'text' | 'voice'>('text')
const isInitializingVad = ref(false)
const isListening = ref(false)
const isSpeaking = ref(false)
const isTranscribing = ref(false)
const isManualRecording = ref(false)
const isRefreshingDevices = ref(false)
const voiceError = ref('')
const voiceInfo = ref('')
const lastTranscript = ref('')
const audioInputDevices = ref<MediaDeviceInfo[]>([])
const selectedInputDeviceId = ref('')
const showVoiceSettings = ref(false)

const AUDIO_INPUT_LABEL_STORAGE_KEY = 'aifriends.preferred-audio-input-label'

let vadInstance: { start?: () => Promise<void> | void; destroy: () => void } | null = null
let manualRecorder: MediaRecorder | null = null
let manualRecorderChunks: Blob[] = []
let manualRecorderStream: MediaStream | null = null

const isVoiceBusy = computed(() => isInitializingVad.value || isTranscribing.value)
const voiceBasePath = computed(() => (
  import.meta.env.PROD ? '/static/frontend/vad/' : '/vad/'
))
const isIOS = computed(() => {
  if (typeof navigator === 'undefined') return false
  return /iP(hone|ad|od)/i.test(navigator.userAgent)
})
const voiceAvailabilityHint = computed(() => {
  if (props.disabledReason) return props.disabledReason
  if (typeof window !== 'undefined' && !window.isSecureContext) {
    return '当前页面不是 HTTPS，iPhone 和部分移动浏览器无法启用麦克风。'
  }
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    return '当前浏览器不支持麦克风接口。'
  }
  return ''
})
const selectedInputDeviceLabel = computed(() => (
  audioInputDevices.value.find((device) => device.deviceId === selectedInputDeviceId.value)?.label || ''
))
const isMicrophoneReady = computed(() => {
  if (props.disabled || Boolean(voiceAvailabilityHint.value) || isRefreshingDevices.value) {
    return false
  }

  return audioInputDevices.value.some((device) => device.deviceId === selectedInputDeviceId.value)
})
const voiceStatusTitle = computed(() => {
  if (voiceError.value) return '语音暂时不可用'
  if (voiceInfo.value) return '语音状态更新'
  if (lastTranscript.value) return '最近一次识别完成'
  if (isRefreshingDevices.value || !isMicrophoneReady.value) return '麦克风准备中'
  if (isInitializingVad.value) return '正在初始化麦克风...'
  if (isTranscribing.value) return '正在识别语音...'
  if (isManualRecording.value) return '手动录音进行中'
  if (isSpeaking.value) return '检测到你正在说话'
  if (isListening.value) return '自动监听已开启'
  return '语音模式已就绪'
})
const voiceStatusDescription = computed(() => {
  if (voiceError.value) return voiceError.value
  if (voiceInfo.value) return voiceInfo.value
  if (lastTranscript.value) return `最近识别：${lastTranscript.value}`
  if (voiceAvailabilityHint.value) return voiceAvailabilityHint.value
  if (isRefreshingDevices.value) return '正在检测可用麦克风，请稍等。'
  if (!isMicrophoneReady.value) return '麦克风还没准备好，准备完成后才能启动监听或手动录音。'
  if (isManualRecording.value) return '再次点击“停止并发送”即可提交识别。'
  if (isSpeaking.value) return '保持说话，停顿后会自动提交。'
  if (isListening.value) return '自动断句识别。也可以直接切手动录音。'
  return '启动监听后会自动识别，也支持手动录音。'
})
const shouldShowVoiceDrawer = computed(() => inputMode.value === 'voice' && showVoiceSettings.value)

const normalizeDeviceLabel = (label: string) => label.trim().toLowerCase()

const isContinuityAudioInput = (device: MediaDeviceInfo) => {
  const label = normalizeDeviceLabel(device.label)
  return /iphone|continuity|接力/.test(label)
}

const readStoredPreferredDeviceLabel = () => {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(AUDIO_INPUT_LABEL_STORAGE_KEY)?.trim() || ''
}

const writeStoredPreferredDeviceLabel = (label: string) => {
  if (typeof window === 'undefined') return
  const normalized = label.trim()
  if (!normalized) return
  window.localStorage.setItem(AUDIO_INPUT_LABEL_STORAGE_KEY, normalized)
}

const canProbeAudioInputs = () => (
  typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)
)

const focusTextarea = async () => {
  await nextTick()
  textareaRef.value?.focus()
}

const normalizeVoiceError = (error: unknown) => {
  if (typeof error === 'object' && error && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    const detail = response?.data?.detail?.trim()
    if (detail) return detail
  }

  if (error instanceof Error) {
    if (error.name === 'NotAllowedError') {
      return '麦克风权限被拒绝了，请在 Safari 设置里允许当前网站访问麦克风。'
    }
    if (error.name === 'NotFoundError') {
      return '没有检测到可用的麦克风设备。'
    }
    if (error.name === 'NotReadableError') {
      return '麦克风当前被其他应用占用，或者系统暂时无法读取。'
    }
    return error.message || '麦克风初始化失败。'
  }
  return '麦克风初始化失败。'
}

const blobToDataUrl = (blob: Blob) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(String(reader.result || ''))
  reader.onerror = () => reject(new Error('读取录音数据失败。'))
  reader.readAsDataURL(blob)
})

const buildAudioConstraints = () => {
  const baseConstraints = {
    channelCount: 1,
    echoCancellation: true,
    autoGainControl: true,
    noiseSuppression: true,
  }

  if (!selectedInputDeviceId.value) {
    return { audio: baseConstraints }
  }

  return {
    audio: {
      ...baseConstraints,
      deviceId: { exact: selectedInputDeviceId.value },
    },
  }
}

const pickPreferredAudioInput = (devices: MediaDeviceInfo[]) => {
  if (!devices.length) return ''

  const storedLabel = normalizeDeviceLabel(readStoredPreferredDeviceLabel())
  if (storedLabel) {
    const storedDevice = devices.find((device) => normalizeDeviceLabel(device.label) === storedLabel)
    if (storedDevice) return storedDevice.deviceId
  }

  const labeledDevices = devices.filter((device) => device.label.trim())
  if (!labeledDevices.length) {
    return ''
  }

  const builtInMic = labeledDevices.find((device) => /macbook|built-?in|内建|麦克风/i.test(device.label))
  if (builtInMic) return builtInMic.deviceId

  const nonIPhoneMic = labeledDevices.find((device) => !/iphone/i.test(device.label))
  if (nonIPhoneMic) return nonIPhoneMic.deviceId

  return labeledDevices[0]?.deviceId || ''
}

const probeUsableAudioInputs = async (devices: MediaDeviceInfo[]) => {
  if (!devices.length || !canProbeAudioInputs()) {
    return devices
  }

  const usableDevices: MediaDeviceInfo[] = []

  for (const device of devices) {
    if (
      device.deviceId === selectedInputDeviceId.value
      && (isListening.value || isManualRecording.value)
    ) {
      usableDevices.push(device)
      continue
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          deviceId: { exact: device.deviceId },
        },
      })
      stream.getTracks().forEach((track) => track.stop())
      usableDevices.push(device)
    } catch {
      continue
    }
  }

  return usableDevices
}

const refreshAudioDevices = async ({ ensurePermission = false } = {}) => {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.enumerateDevices) return

  isRefreshingDevices.value = true
  let temporaryStream: MediaStream | null = null

  try {
    if (ensurePermission && navigator.mediaDevices.getUserMedia) {
      temporaryStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    }

    const devices = await navigator.mediaDevices.enumerateDevices()
    const rawInputs = devices.filter((device) => device.kind === 'audioinput')
    const preferredInputs = rawInputs.filter((device) => !isContinuityAudioInput(device))
    const probeCandidates = preferredInputs.length ? preferredInputs : rawInputs
    const inputs = await probeUsableAudioInputs(probeCandidates)
    audioInputDevices.value = inputs

    if (!inputs.some((device) => device.deviceId === selectedInputDeviceId.value)) {
      const nextDeviceId = pickPreferredAudioInput(inputs)
      if (nextDeviceId) {
        selectedInputDeviceId.value = nextDeviceId
      } else {
        selectedInputDeviceId.value = ''
      }
    }

    if (!inputs.length && rawInputs.length) {
      voiceError.value = '当前检测到的麦克风都不可用，请检查系统输入设备或关闭占用麦克风的应用。'
    }
  } catch (error) {
    voiceError.value = normalizeVoiceError(error)
  } finally {
    temporaryStream?.getTracks().forEach((track) => track.stop())
    isRefreshingDevices.value = false
  }
}

const restartVad = async () => {
  destroyVad()
  await startVad()
}

const pauseLiveListening = () => {
  if (inputMode.value !== 'voice') return
  if (isManualRecording.value) return
  destroyVad()
  if (!isTranscribing.value) {
    voiceInfo.value = '正在播放角色语音，已暂停实时监听。'
  }
}

const toggleLiveListening = async () => {
  if (props.disabled || isVoiceBusy.value || !isMicrophoneReady.value) return

  if (isListening.value) {
    destroyVad()
    voiceInfo.value = '已停止实时监听。'
    return
  }

  await startVad()
}

const resumeLiveListening = async () => {
  if (inputMode.value !== 'voice' || props.disabled) return
  if (isManualRecording.value || isVoiceBusy.value || vadInstance) return
  voiceError.value = ''
  voiceInfo.value = '角色语音播放结束，正在恢复实时监听...'
  await startVad()
}

const float32ToWavDataUrl = (samples: Float32Array, sampleRate = 16000) => {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const writeString = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, samples.length * 2, true)

  let offset = 44
  for (let i = 0; i < samples.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, samples[i] ?? 0))
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
    offset += 2
  }

  let binary = ''
  const bytes = new Uint8Array(buffer)
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i] ?? 0)
  }
  return `data:audio/wav;base64,${btoa(binary)}`
}

const destroyVad = () => {
  if (vadInstance) {
    vadInstance.destroy()
    vadInstance = null
  }
  isListening.value = false
  isSpeaking.value = false
}

const cleanupManualRecorder = () => {
  if (manualRecorder) {
    manualRecorder.ondataavailable = null
    manualRecorder.onstop = null
    if (manualRecorder.state !== 'inactive') {
      manualRecorder.stop()
    }
  }
  manualRecorder = null
  manualRecorderChunks = []
  if (manualRecorderStream) {
    manualRecorderStream.getTracks().forEach((track) => track.stop())
    manualRecorderStream = null
  }
  isManualRecording.value = false
}

const resetToTextMode = async () => {
  destroyVad()
  cleanupManualRecorder()
  inputMode.value = 'text'
  showVoiceSettings.value = false
  voiceError.value = ''
  voiceInfo.value = ''
  isInitializingVad.value = false
  isTranscribing.value = false
  lastTranscript.value = ''
  if (props.autofocus) {
    await focusTextarea()
  }
}

const sendVoiceToBackend = async (audio: Float32Array) => {
  voiceInfo.value = '语音片段已捕获，正在提交识别...'
  const response = await api.post<{ text: string }>(props.asrEndpoint, {
    audio_data: float32ToWavDataUrl(audio),
  })

  const text = response.data.text.trim()
  if (!text) {
    voiceInfo.value = ''
    voiceError.value = '语音识别结果为空，请说得更清楚一些再试。'
    return
  }

  lastTranscript.value = text
  voiceInfo.value = `已识别并发送：${text}`
  if (props.pending) {
    emit('stop')
  }
  emit('send', text)
}

const sendVoiceDataUrlToBackend = async (audioDataUrl: string) => {
  voiceInfo.value = '录音已结束，正在提交识别...'
  const response = await api.post<{ text: string }>(props.asrEndpoint, {
    audio_data: audioDataUrl,
  })

  const text = response.data.text.trim()
  if (!text) {
    voiceInfo.value = ''
    voiceError.value = '语音识别结果为空，请说得更清楚一些再试。'
    return
  }

  lastTranscript.value = text
  voiceInfo.value = `已识别并发送：${text}`
  if (props.pending) {
    emit('stop')
  }
  emit('send', text)
}

const startVad = async () => {
  if (props.disabled || vadInstance || isInitializingVad.value) return

  isInitializingVad.value = true
  voiceError.value = ''

  if (typeof window !== 'undefined' && !window.isSecureContext) {
    voiceError.value = 'iPhone 上麦克风只能在 HTTPS 页面使用。请不要直接用局域网 http 地址打开当前页面。'
    isInitializingVad.value = false
    return
  }

  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    voiceError.value = '当前浏览器不支持麦克风接口，请使用 Safari 并确认系统版本较新。'
    isInitializingVad.value = false
    return
  }

  try {
    vadInstance = await MicVAD.new({
      baseAssetPath: voiceBasePath.value,
      getStream: async () => navigator.mediaDevices.getUserMedia(buildAudioConstraints()),
      resumeStream: async (stream) => {
        stream.getTracks().forEach((track) => track.stop())
        return navigator.mediaDevices.getUserMedia(buildAudioConstraints())
      },
      onSpeechStart: () => {
        isSpeaking.value = true
        voiceError.value = ''
        voiceInfo.value = '检测到你开始说话了，请在停顿后等它自动发送。'
      },
      onSpeechRealStart: () => {
        voiceInfo.value = '已确认是有效人声，继续说完即可自动发送。'
      },
      onVADMisfire: () => {
        isSpeaking.value = false
        voiceInfo.value = ''
        voiceError.value = '检测到了很短的声音，但没有形成完整语音片段，请再连续说久一点。'
      },
      onSpeechEnd: async (audio) => {
        isSpeaking.value = false
        if (!audio?.length) {
          voiceInfo.value = ''
          voiceError.value = '没有采集到有效语音片段，请靠近麦克风后再试。'
          return
        }

        isTranscribing.value = true
        voiceError.value = ''
        voiceInfo.value = '检测到说话结束，正在识别...'
        try {
          await sendVoiceToBackend(audio)
        } catch (error: unknown) {
          voiceInfo.value = ''
          voiceError.value = normalizeVoiceError(error)
        } finally {
          isTranscribing.value = false
        }
      },
      ortConfig: (ort) => {
        // Use Vite-managed asset URLs for ONNX Runtime so dev mode does not try
        // to import a module directly from /public.
        ort.env.wasm.wasmPaths = {
          mjs: ortWasmModuleUrl,
          wasm: ortWasmBinaryUrl,
        }
        ort.env.logLevel = 'error'
      },
      positiveSpeechThreshold: 0.45,
      negativeSpeechThreshold: 0.35,
      preSpeechPadMs: 800,
      minSpeechMs: 650,
      redemptionMs: 1000,
      processorType: isIOS.value ? 'ScriptProcessor' : 'auto',
    })

    await vadInstance.start?.()
    isListening.value = true
  } catch (error) {
    destroyVad()
    voiceError.value = normalizeVoiceError(error)
  } finally {
    isInitializingVad.value = false
  }
}

const startManualRecording = async () => {
  if (props.disabled || isManualRecording.value || isTranscribing.value || !isMicrophoneReady.value) return

  voiceError.value = ''
  voiceInfo.value = ''

  if (typeof window !== 'undefined' && !window.isSecureContext) {
    voiceError.value = '手动录音也需要 HTTPS 页面。'
    return
  }

  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    voiceError.value = '当前浏览器不支持手动录音。'
    return
  }

  try {
    manualRecorderStream = await navigator.mediaDevices.getUserMedia(buildAudioConstraints())
    manualRecorderChunks = []
    manualRecorder = new MediaRecorder(manualRecorderStream)
    manualRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        manualRecorderChunks.push(event.data)
      }
    }
    manualRecorder.onstop = async () => {
      try {
        const mimeType = manualRecorder?.mimeType || manualRecorderChunks[0]?.type || 'audio/webm'
        const audioBlob = new Blob(manualRecorderChunks, { type: mimeType })
        manualRecorderChunks = []

        if (!audioBlob.size) {
          voiceInfo.value = ''
          voiceError.value = '没有录到有效声音，请重试。'
          return
        }

        isTranscribing.value = true
        const audioDataUrl = await blobToDataUrl(audioBlob)
        await sendVoiceDataUrlToBackend(audioDataUrl)
      } catch (error) {
        voiceInfo.value = ''
        voiceError.value = normalizeVoiceError(error)
      } finally {
        isTranscribing.value = false
        if (manualRecorderStream) {
          manualRecorderStream.getTracks().forEach((track) => track.stop())
          manualRecorderStream = null
        }
        manualRecorder = null
        isManualRecording.value = false
      }
    }
    manualRecorder.start()
    isManualRecording.value = true
    voiceInfo.value = '手动录音中，再点一次“停止并发送”即可提交识别。'
  } catch (error) {
    cleanupManualRecorder()
    voiceError.value = normalizeVoiceError(error)
  }
}

const toggleManualRecording = async () => {
  if (isManualRecording.value) {
    if (manualRecorder && manualRecorder.state !== 'inactive') {
      manualRecorder.stop()
      voiceInfo.value = '录音结束，正在处理...'
    }
    return
  }

  await startManualRecording()
}

const setInputMode = async (mode: 'text' | 'voice') => {
  if (mode === inputMode.value) return

  if (mode === 'text') {
    await resetToTextMode()
    return
  }

  if (!props.allowVoiceMode) return

  inputMode.value = 'voice'
  message.value = ''
  showVoiceSettings.value = false
  await refreshAudioDevices({ ensurePermission: true })
  await startVad()
}

const handleSend = () => {
  if (props.disabled) return
  const value = message.value.trim()
  if (!value) return
  emit('send', value)
  message.value = ''
  void focusTextarea()
}

watch(() => props.autofocus, async (value) => {
  if (!value || inputMode.value !== 'text') return
  await focusTextarea()
}, { immediate: true })

watch(() => props.resetToken, () => {
  void resetToTextMode()
})

watch(() => props.allowVoiceMode, (allowed) => {
  if (!allowed && inputMode.value === 'voice') {
    void resetToTextMode()
  }
})

watch(selectedInputDeviceId, (current, previous) => {
  if (!current || current === previous || inputMode.value !== 'voice' || isVoiceBusy.value) {
    return
  }
  if (selectedInputDeviceLabel.value) {
    writeStoredPreferredDeviceLabel(selectedInputDeviceLabel.value)
  }
  voiceInfo.value = `已切换到麦克风：${selectedInputDeviceLabel.value || '当前设备'}，正在重新启动监听...`
  void restartVad()
})

onBeforeUnmount(() => {
  destroyVad()
  cleanupManualRecorder()
})

defineExpose({
  async focus() {
    if (inputMode.value === 'text') {
      await focusTextarea()
    }
  },
  isVoiceMode() {
    return inputMode.value === 'voice'
  },
  pauseLiveListening,
  resumeLiveListening,
  reset() {
    return resetToTextMode()
  },
})
</script>

<template>
  <div class="relative rounded-[26px] border border-base-200/80 bg-white/88 p-3 shadow-[0_18px_45px_-30px_rgba(15,23,42,0.35)] backdrop-blur sm:p-3.5">
    <div class="mb-3 flex items-center justify-between gap-3">
      <div class="flex gap-1.5 rounded-full border border-base-200 bg-base-100/90 p-1">
        <button
          type="button"
          class="btn btn-sm rounded-full"
          :class="inputMode === 'text' ? 'btn-primary' : 'btn-ghost text-base-content/70'"
          @click="setInputMode('text')"
        >
          文字
        </button>
        <button
          type="button"
          class="btn btn-sm rounded-full"
          :class="inputMode === 'voice' ? 'btn-primary' : 'btn-ghost text-base-content/70'"
          :disabled="disabled || !allowVoiceMode"
          @click="setInputMode('voice')"
        >
          语音
        </button>
      </div>

      <button
        v-if="pending"
        type="button"
        class="btn btn-sm rounded-full border-base-200 bg-base-100 text-base-content/75 hover:bg-base-200/70"
        @click="emit('stop')"
      >
        停止回复
      </button>
    </div>

    <div v-if="inputMode === 'text'" class="flex min-h-[84px] items-end gap-3">
      <textarea
        ref="textareaRef"
        v-model="message"
        class="textarea h-20 flex-1 resize-none border-0 bg-white/85 text-sm leading-7 text-base-content focus:outline-none"
        :disabled="disabled"
        :placeholder="placeholder"
        @keydown.enter.exact.prevent="handleSend"
      />
      <button type="button" class="btn btn-primary self-end" :disabled="disabled" @click="handleSend">
        {{ pending ? '继续发送' : '发送' }}
      </button>
    </div>

    <div v-else class="min-h-[84px]">
      <div class="flex min-h-[84px] items-center gap-3 rounded-[22px] border border-base-200 bg-base-50/95 px-4 py-3.5 text-base-content">
        <div class="min-w-0 flex-1">
          <div class="text-sm font-bold">
            {{ voiceStatusTitle }}
          </div>
          <div class="mt-1 line-clamp-2 text-xs leading-6 text-base-content/60">
            {{ voiceStatusDescription }}
          </div>
        </div>

        <div class="flex shrink-0 flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            class="btn btn-sm rounded-full border-base-200 bg-white text-base-content/80 hover:bg-base-200/70"
            :disabled="disabled || pending || isVoiceBusy || !isMicrophoneReady"
            @click="toggleLiveListening"
          >
            {{ isListening ? '停止监听' : '启动监听' }}
          </button>
          <button
            type="button"
            class="btn btn-sm rounded-full border-base-200 bg-base-100 text-base-content/80 hover:bg-base-200/70"
            :disabled="disabled || pending || isVoiceBusy || !isMicrophoneReady"
            @click="toggleManualRecording"
          >
            {{ isManualRecording ? '停止并发送' : '手动录音' }}
          </button>
          <button
            type="button"
            class="btn btn-sm rounded-full border-base-200 bg-transparent text-base-content/65 hover:border-base-300 hover:bg-base-100 hover:text-base-content"
            :disabled="disabled || isVoiceBusy"
            @click="showVoiceSettings = !showVoiceSettings"
          >
            {{ showVoiceSettings ? '收起' : '设置' }}
          </button>
        </div>
      </div>

      <div
        v-if="isSpeaking"
        class="pointer-events-none absolute inset-x-0 top-[calc(100%+8px)] z-30 flex justify-center"
      >
        <div class="pointer-events-auto flex h-9 items-center gap-1 rounded-full border border-sky-300/20 bg-[#101828]/82 px-4 shadow-[0_18px_40px_-24px_rgba(15,23,42,0.75)] backdrop-blur-2xl">
          <div
            v-for="i in 18"
            :key="i"
            class="animate-wave w-0.5 rounded-full bg-sky-300"
            :style="{ animationDelay: `${i * 0.04}s` }"
          />
        </div>
      </div>

      <div class="pointer-events-none fixed inset-x-4 bottom-4 z-[70]">
        <div
          v-if="shouldShowVoiceDrawer"
          class="pointer-events-auto mx-auto max-w-[760px] rounded-[24px] border border-base-200 bg-white/96 p-4 text-base-content shadow-[0_28px_80px_-30px_rgba(15,23,42,0.3)] backdrop-blur-2xl"
        >
          <div class="mb-3 flex items-center justify-between gap-3">
            <div class="text-sm font-bold text-base-content/90">语音面板</div>
            <button
              type="button"
              class="btn btn-xs rounded-full border-base-200 bg-base-100 text-base-content/80 hover:bg-base-200/70"
              @click="showVoiceSettings = false"
            >
              收起
            </button>
          </div>
          <div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
            <label class="form-control">
              <span class="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-base-content/45">输入设备</span>
              <select
                v-model="selectedInputDeviceId"
                class="select select-bordered w-full bg-white/90 text-base-content"
                :disabled="disabled || isVoiceBusy || isManualRecording"
              >
                <option v-if="!audioInputDevices.length" value="">
                  {{ isRefreshingDevices ? '正在读取麦克风列表...' : '未读取到麦克风设备' }}
                </option>
                <option v-for="device in audioInputDevices" :key="device.deviceId" :value="device.deviceId">
                  {{ device.label || `麦克风 ${device.deviceId.slice(0, 6)}` }}
                </option>
              </select>
              <span class="mt-2 text-xs leading-6 text-base-content/55">
                当前优先设备：{{ selectedInputDeviceLabel || '浏览器默认输入设备' }}
              </span>
            </label>

            <button
              type="button"
              class="btn btn-sm self-end rounded-full border-base-200 bg-base-100 text-base-content/80 hover:bg-base-200/70"
              :disabled="disabled || isVoiceBusy"
              @click="refreshAudioDevices({ ensurePermission: false })"
            >
              {{ isRefreshingDevices ? '刷新中...' : '刷新设备' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-wave {
  height: 4px;
  animation: wave-animation 0.55s ease-in-out infinite alternate;
}

@keyframes wave-animation {
  0% {
    height: 4px;
    opacity: 0.35;
  }

  100% {
    height: 20px;
    opacity: 1;
  }
}
</style>
