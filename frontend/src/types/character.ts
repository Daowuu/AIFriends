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

export type Character = {
  id: number
  name: string
  profile: string
  voice_id: number | null
  voice: VoiceOption | null
  photo: string
  background_image: string
  created_at: string
  updated_at: string
  author: CharacterAuthor
  is_owner: boolean
  friend_id: number | null
}

export type CharacterFormPayload = {
  name: string
  profile: string
  voiceId: number | null
  customVoiceName: string
  customVoiceCode: string
  customVoiceModelName: string
  customVoiceDescription: string
  photoFile: File | null
  backgroundImageFile: File | null
  removePhoto: boolean
  removeBackgroundImage: boolean
}
