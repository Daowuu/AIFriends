import type { Character } from '@/types/character'

export type DiscussionGroupStatus = 'waiting' | 'active' | 'finished'
export type DiscussionGroupPhase = 'setup' | 'day_speeches' | 'finished'

export type DiscussionParticipant = {
  id: number
  character_id: number | null
  seat_order: number
  display_name: string
  is_moderator: boolean
  profile: string
  custom_prompt: string
  voice_name: string
  voice_model_name: string
  photo: string
  background_image: string
  reply_style: Character['ai_config']['reply_style']
  reply_length: Character['ai_config']['reply_length']
  initiative_level: Character['ai_config']['initiative_level']
  persona_boundary: Character['ai_config']['persona_boundary']
}

export type DiscussionGroup = {
  id: number
  title: string
  status: DiscussionGroupStatus
  phase: DiscussionGroupPhase
  phase_label: string
  round_number: number
  max_rounds: number
  topic: string
  observer_note: string
  participant_count: number
  moderator_participant_id: number | null
  moderator_participant_name: string
  current_stage: string
  current_stage_label: string
  runtime_status: 'ready' | 'blocked'
  failed_node: {
    id?: string
    kind?: string
    stage?: string
  }
  last_failure: {
    node_id: string
    node_kind: string
    stage: string
    failure_code: string
    failure_reason: string
    retryable: boolean
    failed_at: string
  }
  created_at: string
  updated_at: string
}

export type DiscussionEvent = {
  id: number
  event_type: string
  phase: DiscussionGroupPhase
  phase_label: string
  round_number: number
  title: string
  content: string
  payload: Record<string, unknown>
  created_at: string
}

export type DiscussionSpeech = {
  id: number
  participant_id: number
  participant_name: string
  phase: DiscussionGroupPhase
  phase_label: string
  round_number: number
  audience: 'public' | 'wolves' | 'private'
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

export type DiscussionGroupDetail = {
  group: DiscussionGroup
  participants: DiscussionParticipant[]
  events: DiscussionEvent[]
  speeches: DiscussionSpeech[]
  discussion_plan: {
    current_stage: string
    current_stage_label: string
    current_round: number
    agenda_items: string[]
    round_goal: string
    focus_points: string[]
    moderator_question: string
  }
  stance_map: Record<string, {
    participant_id: number
    participant_name: string
    stance_label: string
    confidence: string
    summary: string
    last_round: number
  }>
  consensus_state: {
    resolved_points: string[]
    open_questions: string[]
    consensus_draft: string
    final_summary: string
  }
  runtime_status: 'ready' | 'blocked'
  failed_node: {
    id?: string
    kind?: string
    stage?: string
  }
  last_failure: {
    node_id: string
    node_kind: string
    stage: string
    failure_code: string
    failure_reason: string
    retryable: boolean
    failed_at: string
  }
}
