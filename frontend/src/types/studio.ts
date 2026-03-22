import type { AIRuntimeSummary } from '@/types/ai-settings'
import type { Character, VoiceOption } from '@/types/character'

export type StudioRecentDebugSummary = {
  session_id: number
  character_id: number
  character_name: string
  memory_mode: string
  voice_name: string
  last_message_at: string
  memory_updated_at: string
  last_debug_at: string
  has_summary: boolean
  has_preference_memory: boolean
  prompt_layers: string[]
  runtime_source: string
  fallback_used: boolean
  error_tag: string
  memory_update_reason: string
  memory_update_triggered: boolean
  used_summary: boolean
  used_relationship_memory: boolean
  used_user_preference_memory: boolean
}

export type StudioOverview = {
  characters: Character[]
  voices: VoiceOption[]
  runtime_summary: AIRuntimeSummary
  recent_debug_summary: StudioRecentDebugSummary | null
}

export type StudioChatDebug = {
  prompt_layers: string[]
  memory_injection: {
    mode: string
    used_summary: boolean
    used_relationship_memory: boolean
    used_user_preference_memory: boolean
  }
  memory_update: {
    triggered: boolean
    updated: boolean
    reason: string
    cooldown_active?: boolean
  }
  runtime_source: string
  fallback_used: boolean
  error_tag?: string
}
