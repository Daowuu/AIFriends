export type CharacterAuthor = {
  id: number
  username: string
  display_name: string
  bio: string
  avatar: string
}

export type VoiceOption = {
  id: number
  name: string
  provider: string
  source: 'system' | 'custom'
  model_name: string
  voice_code: string
  description: string
  language: string
  sample_audio: string
  is_active: boolean
  is_owner: boolean
  character_count: number
}

export type CharacterAIConfig = {
  reply_style: 'natural' | 'warm' | 'restrained' | 'playful'
  reply_length: 'short' | 'balanced' | 'detailed'
  initiative_level: 'passive' | 'balanced' | 'proactive'
  memory_mode: 'off' | 'standard' | 'enhanced'
  persona_boundary: 'grounded' | 'companion' | 'dramatic'
  tools_enabled: boolean
  tools_require_confirmation: boolean
  tools_read_only: boolean
}

export type Character = {
  id: number
  name: string
  profile: string
  custom_prompt: string
  voice_id: number | null
  voice: VoiceOption | null
  photo: string
  background_image: string
  created_at: string
  updated_at: string
  author: CharacterAuthor
  ai_config: CharacterAIConfig
  is_owner: boolean
  friend_id: number | null
}

export type CharacterFormPayload = {
  name: string
  profile: string
  customPrompt: string
  voiceId: number | null
  customVoiceName: string
  customVoiceCode: string
  customVoiceModelName: string
  customVoiceDescription: string
  aiConfig: CharacterAIConfig
  photoFile: File | null
  backgroundImageFile: File | null
  removePhoto: boolean
  removeBackgroundImage: boolean
}
