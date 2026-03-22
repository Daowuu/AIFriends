import type { AIRuntimeSummary } from '@/types/ai-settings'
import type { Character, VoiceOption } from '@/types/character'

export type StudioSessionMemorySummary = {
  character_id: number
  has_messages: boolean
  last_message_at: string
  memory_updated_at: string
  conversation_summary: string
  relationship_memory: string
  user_preference_memory: string
}

export type StudioOverview = {
  characters: Character[]
  voices: VoiceOption[]
  runtime_summary: AIRuntimeSummary
  session_memory_summaries: StudioSessionMemorySummary[]
}
