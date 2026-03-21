<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import Croppie from 'croppie'
import 'croppie/croppie.css'

import { base64ToFile } from '@/utils/base64ToFile'

const props = withDefaults(defineProps<{
  title: string
  modelValue?: string
  helper?: string
  accept?: string
  viewportWidth?: number
  aspectRatio?: number
  outputWidth?: number
  outputFormat?: 'png' | 'jpeg' | 'webp'
  outputQuality?: number
  maxFileSizeMB?: number
  viewportType?: 'square' | 'circle'
}>(), {
  modelValue: '',
  helper: '',
  accept: 'image/*',
  viewportWidth: 220,
  aspectRatio: 1,
  outputWidth: 720,
  outputFormat: 'webp',
  outputQuality: 0.92,
  maxFileSizeMB: 10,
  viewportType: 'square',
})

const emit = defineEmits<{
  change: [{ file: File | null, preview: string }]
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const dialogRef = ref<HTMLDialogElement | null>(null)
const croppieRef = ref<HTMLDivElement | null>(null)
const preview = ref(props.modelValue)
const isReady = ref(false)
const errorMessage = ref('')

let croppie: Croppie | null = null
let pendingSource = ''
let pendingFilename = 'image.webp'

watch(() => props.modelValue, (value) => {
  preview.value = value
})

const viewportHeight = () => props.viewportWidth / props.aspectRatio
const boundaryWidth = () => Math.max(props.viewportWidth + 160, 360)
const boundaryHeight = () => Math.max(viewportHeight() + 120, 420)

const closeDialog = () => {
  dialogRef.value?.close()
}

const normalizeExtension = () => {
  if (props.outputFormat === 'jpeg') return 'jpg'
  return props.outputFormat
}

const ensureCroppie = async () => {
  await nextTick()

  if (!croppieRef.value) return

  if (!croppie) {
    const height = viewportHeight()
    croppie = new Croppie(croppieRef.value, {
      viewport: {
        width: props.viewportWidth,
        height,
        type: props.viewportType,
      },
      boundary: {
        width: boundaryWidth(),
        height: boundaryHeight(),
      },
      enableOrientation: true,
      enforceBoundary: true,
      showZoomer: true,
    })
  }

  await croppie.bind({ url: pendingSource })
  isReady.value = true
}

const openCropper = async (file: File) => {
  pendingFilename = file.name || `image.${normalizeExtension()}`

  const reader = new FileReader()
  reader.onload = async () => {
    pendingSource = String(reader.result || '')
    dialogRef.value?.showModal()
    isReady.value = false
    await ensureCroppie()
  }
  reader.readAsDataURL(file)
}

const handleInputChange = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  errorMessage.value = ''

  if (!file.type.startsWith('image/')) {
    errorMessage.value = '只支持上传图片文件。'
    if (inputRef.value) inputRef.value.value = ''
    return
  }

  const maxBytes = props.maxFileSizeMB * 1024 * 1024
  if (file.size > maxBytes) {
    errorMessage.value = `原图不能超过 ${props.maxFileSizeMB} MB，请压缩后再上传。`
    if (inputRef.value) inputRef.value.value = ''
    return
  }

  await openCropper(file)
}

const handleCrop = async () => {
  if (!croppie) return

  const result = await croppie.result({
    type: 'base64',
    size: { width: props.outputWidth },
    format: props.outputFormat,
    quality: props.outputQuality,
  })

  preview.value = result
  const extension = normalizeExtension()
  emit('change', {
    file: base64ToFile(result, pendingFilename.replace(/\.[^.]+$/, '') + `.${extension}`),
    preview: result,
  })
  closeDialog()
}

const clearImage = () => {
  preview.value = ''
  if (inputRef.value) inputRef.value.value = ''
  emit('change', { file: null, preview: '' })
}

onBeforeUnmount(() => {
  croppie?.destroy()
})
</script>

<template>
  <div class="rounded-3xl border border-base-200 bg-base-100 p-5 shadow-sm">
    <div class="mb-3 flex items-center justify-between gap-3">
      <div>
        <h3 class="text-base font-bold text-base-content">{{ title }}</h3>
        <p v-if="helper" class="mt-1 text-sm text-base-content/60">{{ helper }}</p>
      </div>
      <button
        v-if="preview"
        type="button"
        class="btn btn-ghost btn-sm text-error"
        @click="clearImage"
      >
        清除
      </button>
    </div>

    <div class="flex flex-col gap-4 md:flex-row md:items-center">
      <div
        class="grid aspect-square w-28 shrink-0 place-items-center overflow-hidden rounded-3xl border border-dashed border-base-300 bg-base-200/50"
      >
        <img
          v-if="preview"
          :src="preview"
          :alt="title"
          class="h-full w-full object-cover"
        >
        <span v-else class="text-sm text-base-content/40">暂无图片</span>
      </div>

      <div class="space-y-3">
        <input
          ref="inputRef"
          :accept="accept"
          type="file"
          class="file-input file-input-bordered w-full max-w-xs"
          @change="handleInputChange"
        >
        <p class="text-xs leading-6 text-base-content/50">
          选择图片后会进入裁剪弹窗。支持常见图片格式，原图不超过 {{ props.maxFileSizeMB }} MB，导出为 {{ props.outputFormat.toUpperCase() }}。
        </p>
        <div v-if="errorMessage" class="alert alert-error py-2 text-sm">
          {{ errorMessage }}
        </div>
      </div>
    </div>

    <dialog ref="dialogRef" class="modal">
      <div class="modal-box max-w-2xl rounded-[28px] transition-none">
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost absolute right-4 top-4">✕</button>
        </form>
        <h3 class="text-lg font-black">裁剪{{ title }}</h3>
        <p class="mt-2 text-sm text-base-content/55">
          现在支持左右和上下拖动，缩放条放在裁剪区下方。
        </p>
        <div
          ref="croppieRef"
          class="crop-shell my-5 min-h-[420px] overflow-hidden rounded-[24px] bg-base-50"
        />
        <div class="flex justify-end gap-3">
          <button type="button" class="btn btn-ghost" @click="closeDialog">取消</button>
          <button type="button" class="btn btn-primary" :disabled="!isReady" @click="handleCrop">
            保存裁剪
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.crop-shell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.crop-shell:deep(.croppie-container) {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.crop-shell :deep(.cr-boundary) {
  margin: 0 auto;
  order: 1;
}

.crop-shell :deep(.cr-slider-wrap) {
  order: 2;
  width: min(420px, calc(100% - 32px));
  margin: 18px auto 0;
  padding: 0 8px;
}

.crop-shell :deep(.cr-slider) {
  width: 100%;
}
</style>
