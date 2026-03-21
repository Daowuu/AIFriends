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
  asr_enabled: boolean
  asr_api_base: string
  asr_model_name: string
  has_asr_api_key: boolean
  resolved_asr_api_base: string
  resolved_asr_model_name: string
  updated_at: string
}
