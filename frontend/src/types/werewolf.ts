import type { Character } from '@/types/character'

export type WerewolfIdentity = 'wolf' | 'seer' | 'villager'
export type WerewolfGameStatus = 'waiting' | 'active' | 'finished'
export type WerewolfGamePhase = 'setup' | 'night' | 'day_speeches' | 'vote' | 'finished'

export type WerewolfSeat = {
  id: number
  seat_order: number
  source_type: 'character' | 'custom'
  character_id: number | null
  display_name: string
  profile: string
  custom_prompt: string
  voice_name: string
  voice_model_name: string
  photo: string
  background_image: string
  identity: WerewolfIdentity
  identity_label: string
  is_alive: boolean
  is_revealed: boolean
  reply_style: Character['ai_config']['reply_style']
  reply_length: Character['ai_config']['reply_length']
  initiative_level: Character['ai_config']['initiative_level']
  persona_boundary: Character['ai_config']['persona_boundary']
}

export type WerewolfGame = {
  id: number
  title: string
  status: WerewolfGameStatus
  phase: WerewolfGamePhase
  phase_label: string
  day_number: number
  night_number: number
  winner: string
  winner_label: string
  observer_note: string
  created_at: string
  updated_at: string
}

export type WerewolfEvent = {
  id: number
  event_type: string
  phase: WerewolfGamePhase
  phase_label: string
  day_number: number
  night_number: number
  title: string
  content: string
  payload: Record<string, unknown>
  created_at: string
}

export type WerewolfSpeech = {
  id: number
  seat_id: number
  seat_name: string
  phase: WerewolfGamePhase
  phase_label: string
  day_number: number
  night_number: number
  audience: 'public' | 'wolves' | 'private'
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

export type WerewolfGameDetail = {
  game: WerewolfGame
  seats: WerewolfSeat[]
  events: WerewolfEvent[]
  speeches: WerewolfSpeech[]
}

export type WerewolfDraftSeat = {
  id: string
  source_type: 'character' | 'custom'
  character_id: number | null
  display_name: string
  profile: string
  custom_prompt: string
}
