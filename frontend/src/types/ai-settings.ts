export type AIProviderOption = {
  value: 'aliyun' | 'deepseek' | 'minimax' | 'openai' | 'custom'
  label: string
  helper: string
  default_api_base: string
  default_model_name: string
}

export type AISettings = {
  enabled: boolean
  provider: AIProviderOption['value']
  api_base: string
  model_name: string
  has_api_key: boolean
  resolved_api_base: string
  resolved_model_name: string
  chat_supports_dashscope_audio: boolean
  asr_enabled: boolean
  asr_api_base: string
  asr_model_name: string
  has_asr_api_key: boolean
  resolved_asr_api_base: string
  resolved_asr_model_name: string
  updated_at: string
}

export type AIRuntimeConfig = {
  enabled: boolean
  source: string
  provider: string
  api_base: string
  model_name: string
  label: string
  reason: string
}

export type AIRecentCharacterSummary = {
  id: number
  name: string
  memory_mode: string
  reply_style: string
  voice_name: string
  voice_model_name: string
}

export type AIRuntimeSummary = {
  chat_runtime: AIRuntimeConfig
  asr_runtime: AIRuntimeConfig
  tts_runtime: AIRuntimeConfig
  chat_runtime_status: 'ok' | 'invalid' | 'missing'
  chat_runtime_reason: string
  dashscope_audio_reuse_source: string
  recent_character_summary: AIRecentCharacterSummary | null
  prompt_layers: string[]
}
