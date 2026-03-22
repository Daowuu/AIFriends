from __future__ import annotations

import json
import re
import secrets
from difflib import SequenceMatcher

from django.db import transaction
from django.utils import timezone
from openai import OpenAI

from web.ai_settings_service import get_runtime_ai_resolution
from web.chat_services import strip_reasoning_content
from web.dag_runtime import (
    mark_node_completed,
    mark_node_failed,
    pop_ready_node,
    retry_failed_node,
    sanitize_dag_runtime,
)
from web.discussion_dag import (
    NodeKind,
    append_consensus_draft,
    append_discussion_finish,
    append_final_response_round,
    append_focused_round,
    build_initial_discussion_dag_runtime,
)
from web.models import Character, WerewolfEvent, WerewolfGame, WerewolfSeat, WerewolfSpeech
from web.openai_compat import create_chat_completion


MIN_PARTICIPANTS = 2
MAX_PARTICIPANTS = 8
DEFAULT_MAX_ROUNDS = 2
MAX_TOPIC_LENGTH = 600
MAX_PUBLIC_EVENTS = 160
MAX_PUBLIC_SPEECHES = 240
MAX_VISIBLE_SPEECHES = 6
MIN_CONTENT_LENGTH = 16
MIN_NEW_INFORMATION_LENGTH = 8
SIMILARITY_FAILURE_THRESHOLD = 0.84
SELF_SIMILARITY_FAILURE_THRESHOLD = 0.78
DISCUSSION_MODE = 'discussion'
STRUCTURED_OUTPUT_MAX_TOKENS = 1600
PARTICIPANT_REPLY_MAX_TOKENS = 900

RUNTIME_STATUS_READY = 'ready'
RUNTIME_STATUS_BLOCKED = 'blocked'

FAILURE_CODE_INVALID_PLAN = 'invalid_plan'
FAILURE_CODE_INVALID_MODERATOR_PLAN = 'invalid_moderator_plan'
FAILURE_CODE_DUPLICATE_CONTENT = 'duplicate_content'
FAILURE_CODE_DUPLICATE_SELF = 'duplicate_self'
FAILURE_CODE_NO_NEW_INFORMATION = 'no_new_information'
FAILURE_CODE_TOO_SHORT = 'too_short'
FAILURE_CODE_LEAKAGE = 'leakage_or_off_topic'
FAILURE_CODE_UNSPOKEN_REFERENCE = 'unspoken_reference'
FAILURE_CODE_GENERATION_EMPTY = 'generation_empty'

STAGE_LABELS = {
    'setup': '准备阶段',
    'topic_opening': '开场',
    'agenda_setup': '议题拆解',
    'opening_turn': '角色立场',
    'round_summary': '主持总结',
    'focused_turn': '聚焦讨论',
    'consensus_draft': '共识结论',
    'final_response_turn': '异议补充',
    'discussion_finish': '讨论完成',
    'finished': '已结束',
}

STANCE_PATTERNS = (
    ('支持推进', ('支持', '赞同', '同意', '应该', '值得', '可行', '建议推进')),
    ('谨慎保留', ('保留', '谨慎', '需要确认', '先别急', '还要看', '先验证')),
    ('质疑反对', ('反对', '不建议', '不该', '不行', '问题更大', '风险更大', '质疑')),
)


def get_discussion_phase_label(phase: str):
    return {
        'setup': '准备阶段',
        'day_speeches': '讨论中',
        'finished': '已结束',
    }.get(phase, phase)


def get_discussion_stage_label(stage: str):
    return STAGE_LABELS.get(str(stage or '').strip(), str(stage or '').strip())


def _ensure_state_dict(group: WerewolfGame):
    if not isinstance(group.state, dict):
        group.state = {}
    return group.state


def _is_discussion_group(group: WerewolfGame):
    state = group.state if isinstance(group.state, dict) else {}
    return str(state.get('mode') or '') == DISCUSSION_MODE


def _assert_discussion_group(group: WerewolfGame, participants=None):
    state = _ensure_state_dict(group)
    if str(state.get('mode') or '') != DISCUSSION_MODE:
        raise ValueError('当前房间不是讨论组。')

    topic = str(state.get('topic') or '').strip()
    if not topic:
        raise ValueError('当前讨论组缺少有效主题。')

    max_rounds = int(state.get('max_rounds') or 0)
    if max_rounds < 2:
        raise ValueError('当前讨论组缺少有效轮次配置。')

    ordered_participants = list(participants) if participants is not None else list(group.seats.select_related('character', 'voice').order_by('seat_order', 'id'))
    if not (MIN_PARTICIPANTS <= len(ordered_participants) <= MAX_PARTICIPANTS):
        raise ValueError(f'讨论组参与角色数必须在 {MIN_PARTICIPANTS} 到 {MAX_PARTICIPANTS} 人之间。')
    return ordered_participants


def _get_topic(group: WerewolfGame):
    return str(_ensure_state_dict(group).get('topic') or '').strip()


def _get_max_rounds(group: WerewolfGame):
    return max(2, int(_ensure_state_dict(group).get('max_rounds') or DEFAULT_MAX_ROUNDS))


def _empty_discussion_plan():
    return {
        'current_stage': 'setup',
        'current_stage_label': get_discussion_stage_label('setup'),
        'current_round': 0,
        'agenda_items': [],
        'round_goal': '',
        'focus_points': [],
        'moderator_question': '',
    }


def _empty_consensus_state():
    return {
        'resolved_points': [],
        'open_questions': [],
        'consensus_draft': '',
        'final_summary': '',
    }


def _build_initial_stance_map(participants):
    stance_map = {}
    for seat in participants:
        stance_map[str(seat.id)] = {
            'participant_id': seat.id,
            'participant_name': seat.display_name,
            'stance_label': '待表达',
            'confidence': 'low',
            'summary': '',
            'contribution': '',
            'last_round': 0,
        }
    return stance_map


def _empty_last_failure():
    return {
        'node_id': '',
        'node_kind': '',
        'stage': '',
        'failure_code': '',
        'failure_reason': '',
        'retryable': False,
        'failed_at': '',
    }


def _get_moderator_seat_id(group: WerewolfGame):
    state = _ensure_state_dict(group)
    try:
        moderator_seat_id = int(state.get('moderator_seat_id') or 0)
    except (TypeError, ValueError):
        moderator_seat_id = 0
    if moderator_seat_id > 0:
        return moderator_seat_id
    first_seat = group.seats.order_by('seat_order', 'id').first()
    return first_seat.id if first_seat else 0


def _get_moderator_seat(group: WerewolfGame):
    moderator_seat_id = _get_moderator_seat_id(group)
    if moderator_seat_id <= 0:
        return None
    return group.seats.select_related('voice').filter(id=moderator_seat_id).first()


def _get_discussion_plan(group: WerewolfGame):
    plan = _ensure_state_dict(group).get('discussion_plan')
    if not isinstance(plan, dict):
        plan = _empty_discussion_plan()
        _ensure_state_dict(group)['discussion_plan'] = plan
    return plan


def _get_consensus_state(group: WerewolfGame):
    consensus_state = _ensure_state_dict(group).get('consensus_state')
    if not isinstance(consensus_state, dict):
        consensus_state = _empty_consensus_state()
        _ensure_state_dict(group)['consensus_state'] = consensus_state
    return consensus_state


def _get_stance_map(group: WerewolfGame):
    stance_map = _ensure_state_dict(group).get('stance_map')
    if not isinstance(stance_map, dict):
        participants = list(group.seats.order_by('seat_order', 'id'))
        stance_map = _build_initial_stance_map(participants)
        _ensure_state_dict(group)['stance_map'] = stance_map
    return stance_map


def _get_runtime_status(group: WerewolfGame):
    return str(_ensure_state_dict(group).get('runtime_status') or RUNTIME_STATUS_READY)


def _get_failed_node(group: WerewolfGame):
    failed_node = _ensure_state_dict(group).get('failed_node')
    return failed_node if isinstance(failed_node, dict) else {}


def _get_last_failure(group: WerewolfGame):
    failure = _ensure_state_dict(group).get('last_failure')
    return failure if isinstance(failure, dict) else _empty_last_failure()


def _clear_failure_state(group: WerewolfGame):
    state = _ensure_state_dict(group)
    state['runtime_status'] = RUNTIME_STATUS_READY
    state['failed_node'] = {}
    state['last_failure'] = _empty_last_failure()


def _update_discussion_state(group: WerewolfGame, *, stage: str | None = None, round_number: int | None = None, agenda_items=None, round_goal: str | None = None, focus_points=None, moderator_question: str | None = None, resolved_points=None, open_questions=None, consensus_draft: str | None = None, final_summary: str | None = None):
    state = _ensure_state_dict(group)
    plan = _get_discussion_plan(group)
    consensus_state = _get_consensus_state(group)
    if stage is not None:
        plan['current_stage'] = stage
        plan['current_stage_label'] = get_discussion_stage_label(stage)
    if round_number is not None:
        plan['current_round'] = int(round_number)
    if agenda_items is not None:
        plan['agenda_items'] = _dedupe_text_items(agenda_items, limit=4)
    if round_goal is not None:
        plan['round_goal'] = str(round_goal or '').strip()
    if focus_points is not None:
        plan['focus_points'] = _dedupe_text_items(focus_points, limit=4)
    if moderator_question is not None:
        plan['moderator_question'] = str(moderator_question or '').strip()
    if resolved_points is not None:
        consensus_state['resolved_points'] = _dedupe_text_items(resolved_points, limit=4)
    if open_questions is not None:
        consensus_state['open_questions'] = _dedupe_text_items(open_questions, limit=4)
    if consensus_draft is not None:
        consensus_state['consensus_draft'] = str(consensus_draft or '').strip()
    if final_summary is not None:
        consensus_state['final_summary'] = str(final_summary or '').strip()
    state['discussion_plan'] = plan
    state['consensus_state'] = consensus_state


def _set_dag_runtime_state(group: WerewolfGame, dag_runtime):
    _ensure_state_dict(group)['dag_runtime'] = sanitize_dag_runtime(dag_runtime)


def _ensure_dag_runtime(group: WerewolfGame):
    _assert_discussion_group(group)
    dag_runtime = sanitize_dag_runtime(_ensure_state_dict(group).get('dag_runtime'))
    if not dag_runtime.get('nodes'):
        raise ValueError('当前讨论组缺少有效 dag_runtime，无法继续推进。')
    _set_dag_runtime_state(group, dag_runtime)
    return dag_runtime


def _mark_dag_node_completed(dag_runtime, node, payload=None):
    payload_dict = payload if isinstance(payload, dict) else {}
    payload_dict.setdefault('kind', node['kind'])
    payload_dict.setdefault('phase', node['phase'])
    payload_dict.setdefault('stage', node.get('data', {}).get('stage', ''))
    mark_node_completed(dag_runtime, node, payload_dict)


def _serialize_failure(failure):
    if not isinstance(failure, dict):
        return _empty_last_failure()
    return {
        'node_id': str(failure.get('node_id') or ''),
        'node_kind': str(failure.get('node_kind') or ''),
        'stage': str(failure.get('stage') or ''),
        'failure_code': str(failure.get('failure_code') or ''),
        'failure_reason': str(failure.get('failure_reason') or ''),
        'retryable': bool(failure.get('retryable')),
        'failed_at': str(failure.get('failed_at') or ''),
    }


def serialize_discussion_group(group: WerewolfGame):
    state = _ensure_state_dict(group)
    participant_count = group.seats.count()
    discussion_plan = _get_discussion_plan(group)
    failed_node = _get_failed_node(group)
    last_failure = _get_last_failure(group)
    moderator_seat = _get_moderator_seat(group)
    return {
        'id': group.id,
        'title': group.title,
        'status': group.status,
        'phase': group.phase,
        'phase_label': get_discussion_phase_label(group.phase),
        'round_number': group.day_number,
        'max_rounds': int(state.get('max_rounds') or DEFAULT_MAX_ROUNDS),
        'topic': str(state.get('topic') or ''),
        'observer_note': group.observer_note,
        'participant_count': participant_count,
        'moderator_participant_id': moderator_seat.id if moderator_seat else None,
        'moderator_participant_name': moderator_seat.display_name if moderator_seat else '',
        'current_stage': str(discussion_plan.get('current_stage') or 'setup'),
        'current_stage_label': str(discussion_plan.get('current_stage_label') or get_discussion_stage_label('setup')),
        'runtime_status': _get_runtime_status(group),
        'failed_node': failed_node if isinstance(failed_node, dict) else {},
        'last_failure': _serialize_failure(last_failure),
        'created_at': group.created_at.isoformat(),
        'updated_at': group.updated_at.isoformat(),
    }


def serialize_discussion_participant(seat: WerewolfSeat):
    moderator_seat_id = _get_moderator_seat_id(seat.game)
    return {
        'id': seat.id,
        'character_id': seat.character_id,
        'seat_order': seat.seat_order,
        'display_name': seat.display_name,
        'is_moderator': seat.id == moderator_seat_id,
        'profile': seat.profile,
        'custom_prompt': seat.custom_prompt,
        'photo': seat.photo.url if seat.photo else '',
        'background_image': seat.background_image.url if seat.background_image else '',
        'voice_name': seat.voice.name if seat.voice else '',
        'voice_model_name': seat.voice.model_name if seat.voice else '',
        'reply_style': seat.reply_style,
        'reply_length': seat.reply_length,
        'initiative_level': seat.initiative_level,
        'persona_boundary': seat.persona_boundary,
    }


def serialize_discussion_event(event: WerewolfEvent):
    return {
        'id': event.id,
        'event_type': event.event_type,
        'phase': event.phase,
        'phase_label': get_discussion_phase_label(event.phase) if event.phase else '',
        'round_number': event.day_number,
        'title': event.title,
        'content': event.content,
        'payload': event.payload,
        'created_at': event.created_at.isoformat(),
    }


def serialize_discussion_speech(speech: WerewolfSpeech):
    return {
        'id': speech.id,
        'participant_id': speech.seat_id,
        'participant_name': speech.seat.display_name,
        'phase': speech.phase,
        'phase_label': get_discussion_phase_label(speech.phase),
        'round_number': speech.day_number,
        'audience': speech.audience,
        'content': speech.content,
        'metadata': speech.metadata,
        'created_at': speech.created_at.isoformat(),
    }


def build_discussion_group_detail(group: WerewolfGame):
    participants = list(group.seats.select_related('voice').order_by('seat_order', 'id'))
    _assert_discussion_group(group, participants=participants)
    events = list(group.events.order_by('id')[:MAX_PUBLIC_EVENTS])
    speeches = list(group.speeches.select_related('seat').order_by('id')[:MAX_PUBLIC_SPEECHES])
    return {
        'group': serialize_discussion_group(group),
        'participants': [serialize_discussion_participant(seat) for seat in participants],
        'events': [serialize_discussion_event(event) for event in events],
        'speeches': [serialize_discussion_speech(speech) for speech in speeches],
        'discussion_plan': _get_discussion_plan(group),
        'stance_map': _get_stance_map(group),
        'consensus_state': _get_consensus_state(group),
        'runtime_status': _get_runtime_status(group),
        'failed_node': _get_failed_node(group),
        'last_failure': _serialize_failure(_get_last_failure(group)),
    }


def list_discussion_groups():
    groups = []
    for group in WerewolfGame.objects.order_by('-updated_at', '-id'):
        if _is_discussion_group(group):
            groups.append(serialize_discussion_group(group))
    return groups


def validate_discussion_roster(character_ids):
    normalized_ids = []
    for raw_value in character_ids or []:
        try:
            normalized_ids.append(int(raw_value))
        except (TypeError, ValueError) as error:
            raise ValueError('character_ids 中存在无效角色。') from error
    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError('讨论组里不能重复选择同一个角色。')
    if len(normalized_ids) < MIN_PARTICIPANTS:
        raise ValueError(f'讨论组至少需要 {MIN_PARTICIPANTS} 个角色。')
    if len(normalized_ids) > MAX_PARTICIPANTS:
        raise ValueError(f'讨论组最多支持 {MAX_PARTICIPANTS} 个角色。')
    return normalized_ids


def _add_event(group: WerewolfGame, *, event_type: str, title: str, content: str = '', payload=None):
    return WerewolfEvent.objects.create(
        game=group,
        event_type=event_type,
        phase=group.phase,
        day_number=group.day_number,
        night_number=0,
        title=title,
        content=content,
        payload=payload or {},
    )


def _is_moderator_speech_record(speech: WerewolfSpeech):
    return bool((speech.metadata or {}).get('is_moderator_speech'))


def _add_public_speech(
    group: WerewolfGame,
    *,
    seat: WerewolfSeat,
    round_number: int,
    content: str,
    metadata=None,
):
    return WerewolfSpeech.objects.create(
        game=group,
        seat=seat,
        phase='day_speeches',
        day_number=round_number,
        night_number=0,
        audience='public',
        content=content,
        metadata=metadata or {},
    )


def _compact_speech_text(content: str, limit: int = 140):
    return str(content or '').replace('\n', ' ').strip()[:limit]


def _compact_speech_text_no_name(content: str, *, topic: str, speaker_name: str):
    text = str(content or '').strip()
    for value in (topic, speaker_name):
        if value:
            text = text.replace(value, '')
    text = re.sub(r'[\s：:，,。！？!?\-—"“”‘’（）()]+', '', text)
    return text


def _public_speech_history_summary(speeches):
    if not speeches:
        return '当前可见公开发言：暂无。'
    lines = [f"{speech.seat.display_name}：{_compact_speech_text(speech.content)}" for speech in speeches]
    return '当前可见公开发言：' + '；'.join(lines)


def _contains_unspoken_speech_reference(content: str, unspoken_names):
    text = str(content or '')
    if not text:
        return False
    if unspoken_names and any(token in text for token in ('听了大家的发言', '大家刚才都说了', '前面所有人都说完了')):
        return True
    speech_cues = ('发言', '刚才', '方才', '提到', '表示', '说过', '说的', '聊到', '观点', '表态')
    for name in unspoken_names:
        if name not in text:
            continue
        for cue in speech_cues:
            if re.search(rf'{re.escape(name)}[^。！？\n]{{0,14}}{cue}', text):
                return True
            if re.search(rf'{cue}[^。！？\n]{{0,14}}{re.escape(name)}', text):
                return True
    return False


def _contains_off_topic_or_leakage(content: str):
    text = str(content or '')
    if not text.strip():
        return True
    leakage_patterns = (
        r'作为\s*(?:一个)?AI',
        r'作为\s*(?:一个)?模型',
        r'我是\s*(?:一个)?AI',
        r'我是\s*(?:一个)?模型',
        r'提示词',
        r'系统要求',
        r'系统提示',
        r'后台配置',
        r'后台指令',
        r'遵循.*指令',
        r'根据.*指令',
        r'按照.*提示',
    )
    return any(re.search(pattern, text, re.I) for pattern in leakage_patterns)


def _dedupe_text_items(items, *, limit=4):
    normalized = []
    seen = set()
    for raw_item in items or []:
        item = str(raw_item or '').strip().strip('•-')
        if not item:
            continue
        key = re.sub(r'\s+', '', item)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
        if len(normalized) >= limit:
            break
    return normalized


def _normalize_text_items_field(raw_value, *, limit=4):
    if isinstance(raw_value, str):
        return _dedupe_text_items([raw_value], limit=limit)
    if isinstance(raw_value, (list, tuple, set)):
        return _dedupe_text_items(list(raw_value), limit=limit)
    return []


def _extract_json_object(content: str):
    text = strip_reasoning_content(str(content or '')).strip()
    if not text:
        return None
    fenced_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.S)
    if fenced_match:
        text = fenced_match.group(1).strip()
    start_index = text.find('{')
    end_index = text.rfind('}')
    if start_index < 0 or end_index < start_index:
        return None
    try:
        return json.loads(text[start_index:end_index + 1])
    except Exception:
        return None


def _normalize_similarity_text(text: str):
    return re.sub(r'[\s：:，,。！？!?\-—"“”‘’（）()]+', '', str(text or '').strip())


def _similarity_score(left: str, right: str):
    normalized_left = _normalize_similarity_text(left)
    normalized_right = _normalize_similarity_text(right)
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _contains_meaningful_new_information(new_information: str, *, discussion_plan, consensus_state, recent_speeches):
    normalized = _normalize_similarity_text(new_information)
    if len(normalized) < MIN_NEW_INFORMATION_LENGTH:
        return False
    known_texts = []
    known_texts.extend(discussion_plan.get('agenda_items') or [])
    known_texts.extend(discussion_plan.get('focus_points') or [])
    known_texts.extend(consensus_state.get('resolved_points') or [])
    known_texts.extend(consensus_state.get('open_questions') or [])
    for speech in recent_speeches[-3:]:
        known_texts.append(_compact_speech_text(speech.content, limit=120))
    for text in known_texts:
        if normalized and _similarity_score(normalized, text) >= 0.84:
            return False
    return True


def _extract_stance_from_content(content: str):
    text = str(content or '')
    if not text.strip():
        return '待表达', 'low'
    for label, keywords in STANCE_PATTERNS:
        if any(keyword in text for keyword in keywords):
            confidence = 'high' if len(text) >= 40 else 'medium'
            return label, confidence
    if len(text) >= 36:
        return '中立分析', 'medium'
    return '待观察', 'low'


def _update_stance_from_speech(group: WerewolfGame, seat: WerewolfSeat, *, round_number: int, content: str, contribution: str):
    stance_label, confidence = _extract_stance_from_content(content)
    stance_map = _get_stance_map(group)
    stance_map[str(seat.id)] = {
        'participant_id': seat.id,
        'participant_name': seat.display_name,
        'stance_label': stance_label,
        'confidence': confidence,
        'summary': _compact_speech_text(content, limit=90),
        'contribution': str(contribution or '').strip(),
        'last_round': int(round_number),
    }
    _ensure_state_dict(group)['stance_map'] = stance_map


def _apply_stance_updates(group: WerewolfGame, stance_updates):
    if not isinstance(stance_updates, list):
        return
    stance_map = _get_stance_map(group)
    normalized_lookup = {
        str(payload.get('participant_name') or '').strip(): key
        for key, payload in stance_map.items()
        if isinstance(payload, dict)
    }
    for item in stance_updates:
        if not isinstance(item, dict):
            continue
        participant_name = str(item.get('participant_name') or '').strip()
        key = normalized_lookup.get(participant_name)
        if not key:
            continue
        current_payload = stance_map.get(key, {})
        stance_map[key] = {
            'participant_id': current_payload.get('participant_id'),
            'participant_name': current_payload.get('participant_name'),
            'stance_label': str(item.get('stance_label') or current_payload.get('stance_label') or '待表达').strip(),
            'confidence': str(item.get('confidence') or current_payload.get('confidence') or 'low').strip(),
            'summary': str(item.get('summary') or current_payload.get('summary') or '').strip(),
            'contribution': str(item.get('contribution') or current_payload.get('contribution') or '').strip(),
            'last_round': current_payload.get('last_round', 0),
        }
    _ensure_state_dict(group)['stance_map'] = stance_map


def _infer_addressed_agenda_items(text: str, *, agenda_items, focus_points):
    addressed = []
    for item in (focus_points or []) + (agenda_items or []):
        item_text = str(item or '').strip()
        if not item_text:
            continue
        keywords = [segment for segment in re.split(r'[，、：；\s]+', item_text) if len(segment) >= 2]
        if any(keyword in text for keyword in keywords):
            addressed.append(item_text)
    return _dedupe_text_items(addressed, limit=3)


def _discussion_public_state(group: WerewolfGame, *, topic: str, stage: str, round_number: int, prior_speeches, moderator_question: str, agenda_items, focus_points, previous_stance: str):
    return '\n'.join([
        f'讨论主题：{topic}',
        f'当前阶段：{get_discussion_stage_label(stage)}',
        f'当前是第 {round_number}/{_get_max_rounds(group)} 轮讨论。',
        f'主持人本轮问题：{moderator_question or "围绕当前最关键的分歧继续推进。"}',
        '当前子议题：' + (' / '.join(agenda_items) if agenda_items else '暂无'),
        '当前焦点：' + (' / '.join(focus_points) if focus_points else '暂无'),
        f'你上一轮立场摘要：{previous_stance or "暂无。"}',
        _public_speech_history_summary(prior_speeches[-MAX_VISIBLE_SPEECHES:]),
    ])


def _discussion_private_state(seat: WerewolfSeat):
    profile = seat.profile.strip() or '没有额外设定。'
    prompt = seat.custom_prompt.strip() or '无额外要求。'
    return '\n'.join([
        f'角色设定：{profile}',
        f'自定义 Prompt：{prompt}',
        f'发言风格：{seat.reply_style} / {seat.reply_length} / {seat.initiative_level} / {seat.persona_boundary}',
    ])


def _get_runtime_client():
    resolution = get_runtime_ai_resolution()
    if resolution['status'] == 'invalid':
        raise RuntimeError('当前聊天运行时配置不完整，无法生成讨论组发言。')
    runtime = resolution['config']
    if not runtime:
        return None, None
    client = OpenAI(api_key=runtime['api_key'], base_url=runtime['api_base'])
    return client, runtime


def _generate_structured_json(*, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int | None = None):
    client, runtime = _get_runtime_client()
    if not client or not runtime:
        return {}
    request_kwargs = {
        'model': runtime['model_name'],
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': temperature,
    }
    if max_tokens is not None:
        request_kwargs['max_tokens'] = max_tokens
    response = create_chat_completion(client, **request_kwargs)
    content = response.choices[0].message.content if response.choices else ''
    payload = _extract_json_object(content or '')
    return payload if isinstance(payload, dict) else {}


def _generate_text(*, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int | None = None):
    client, runtime = _get_runtime_client()
    if not client or not runtime:
        return ''
    request_kwargs = {
        'model': runtime['model_name'],
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': temperature,
    }
    if max_tokens is not None:
        request_kwargs['max_tokens'] = max_tokens
    response = create_chat_completion(client, **request_kwargs)
    content = response.choices[0].message.content if response.choices else ''
    return strip_reasoning_content(content or '').strip()


def _plan_participant_turn(*, seat: WerewolfSeat, topic: str, public_state: str, private_state: str, stage: str):
    system_prompt = (
        '你正在为一个多人讨论节点生成发言提纲。'
        '必须输出严格 JSON，不要输出任何其他内容。'
        '不要输出思考过程，不要输出<think>标签。'
    )
    user_prompt = '\n'.join([
        f'角色名：{seat.display_name}',
        private_state,
        public_state,
        f'当前阶段：{stage}',
        (
            '输出 JSON：'
            '{"response_target":"","new_information":"","agenda_item":"","stance_label":"","avoid_repeating":[]}'
        ),
        '要求：response_target 只能是已公开发言的角色名或空；new_information 必须是这次新增的信息点；avoid_repeating 写 1-2 条本次不要重复的话。',
    ])
    return _generate_structured_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=STRUCTURED_OUTPUT_MAX_TOKENS,
    )


def _generate_moderator_payload(*, seat: WerewolfSeat, topic: str, stage: str, round_number: int, max_rounds: int, participant_names, prior_speeches, discussion_plan, consensus_state, stance_map):
    speech_lines = []
    for speech in prior_speeches[-MAX_VISIBLE_SPEECHES:]:
        speech_lines.append(f"- {speech.seat.display_name}：{_compact_speech_text(speech.content, limit=160)}")
    stance_lines = []
    for item in stance_map.values():
        if not isinstance(item, dict):
            continue
        stance_lines.append(
            f"- {item.get('participant_name', '')}｜{item.get('stance_label', '待表达')}｜{item.get('summary', '')}｜{item.get('contribution', '')}"
        )
    system_prompt = (
        '你正在主持一个多人讨论组。'
        '你需要以当前角色的身份完成主持职责。'
        '必须输出严格 JSON，不要输出额外文本。'
        '不要输出思考过程，不要输出<think>标签。'
        '输出必须简洁，避免长篇铺陈。'
    )
    private_state = _discussion_private_state(seat)
    stage_requirements = {
        'topic_opening': '必须返回非空 content、非空 agenda_items（2-4 条）、非空 round_goal、非空 new_focus。',
        'agenda_setup': '必须返回非空 content、非空 agenda_items（2-4 条），用于明确本轮拆解出来的议题。',
        'round_summary': '必须返回非空 content、非空 new_focus，用来明确下一轮要追问的焦点。',
        'consensus_draft': '必须返回非空 content、非空 consensus_draft，用来输出可执行共识草案。',
    }
    stage_output_schema = {
        'topic_opening': '{"content":"","round_goal":"","new_focus":"","agenda_items":[],"route":""}',
        'agenda_setup': '{"content":"","agenda_items":[],"round_goal":"","new_focus":"","route":""}',
        'round_summary': '{"content":"","new_focus":"","resolved_points":[],"open_questions":[],"route":""}',
        'consensus_draft': '{"content":"","consensus_draft":"","resolved_points":[],"open_questions":[],"route":""}',
    }
    stage_brevity_rules = {
        'topic_opening': 'content 控制在 120 字以内，agenda_items 保持 2-4 条短句。',
        'agenda_setup': 'content 控制在 120 字以内，agenda_items 保持 2-4 条短句，不要重复开场段落。',
        'round_summary': 'content 控制在 120 字以内，只总结新增分歧和下一步焦点。',
        'consensus_draft': 'content 控制在 160 字以内，consensus_draft 控制在 120 字以内，只写最终共识，不要再复述整段讨论历史。',
    }
    user_prompt = '\n'.join([
        f'主持角色：{seat.display_name}',
        private_state,
        f'讨论主题：{topic}',
        f'当前主持阶段：{stage}',
        f'当前轮次：{round_number}/{max_rounds}',
        f'参与角色：{", ".join(participant_names)}',
        '当前 agenda_items：' + json.dumps(discussion_plan.get('agenda_items') or [], ensure_ascii=False),
        '当前 focus_points：' + json.dumps(discussion_plan.get('focus_points') or [], ensure_ascii=False),
        '当前 resolved_points：' + json.dumps(consensus_state.get('resolved_points') or [], ensure_ascii=False),
        '当前 open_questions：' + json.dumps(consensus_state.get('open_questions') or [], ensure_ascii=False),
        '当前 stance_map：\n' + ('\n'.join(stance_lines) if stance_lines else '- 暂无'),
        '最近公开发言：\n' + ('\n'.join(speech_lines) if speech_lines else '- 暂无'),
        '输出 JSON：' + stage_output_schema.get(stage, '{"content":"","route":""}'),
        '要求：你就是主持人本人。content 必须是你对外公开会说的话，不要再依赖额外隐藏步骤。',
        '阶段硬约束：' + stage_requirements.get(stage, '所有字段都要尽量完整。'),
        '简洁约束：' + stage_brevity_rules.get(stage, '表达要短，不要复述。'),
        '不要省略必填字段，不要返回空数组，不要用“同上”“略”等占位表达。',
    ])
    return _generate_structured_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=STRUCTURED_OUTPUT_MAX_TOKENS,
    )


def generate_discussion_reply(seat: WerewolfSeat, *, topic: str, public_state: str, private_state: str, stage_instruction: str, plan):
    system_prompt = (
        '你正在参加一个多人讨论组。'
        '请严格扮演当前角色，用自然中文表达观点。'
        '不要跳出角色，不要提自己是 AI，不要假装听到了未来还没发生的发言。'
        '必须围绕本轮发言提纲输出，不要复述空泛套话。'
        '不要输出思考过程，不要输出<think>标签。'
    )
    user_prompt = '\n'.join([
        f'角色名：{seat.display_name}',
        private_state,
        public_state,
        '本轮发言提纲：' + json.dumps(plan, ensure_ascii=False),
        f'当前任务：{stage_instruction}',
        '请只输出这名角色此刻会说的话，不要加标题，不要解释系统。',
    ])
    return _generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.75,
        max_tokens=PARTICIPANT_REPLY_MAX_TOKENS,
    )


def _pick_round_start_index(total_count: int):
    if total_count <= 1:
        return 0
    return secrets.randbelow(total_count)


def _ordered_participants(group: WerewolfGame):
    return list(group.seats.select_related('voice').order_by('seat_order', 'id'))


def _ordered_participant_ids(group: WerewolfGame):
    return [seat.id for seat in _ordered_participants(group)]


def _discussion_speaker_ids(group: WerewolfGame):
    moderator_seat_id = _get_moderator_seat_id(group)
    return [seat_id for seat_id in _ordered_participant_ids(group) if seat_id != moderator_seat_id]


def _build_opening_round_queue(group: WerewolfGame):
    participant_ids = _discussion_speaker_ids(group)
    if not participant_ids:
        return []
    start_index = _pick_round_start_index(len(participant_ids))
    return participant_ids[start_index:] + participant_ids[:start_index]


def _relevance_score(seat_id: int, stance_map, open_questions):
    payload = stance_map.get(str(seat_id), {}) if isinstance(stance_map, dict) else {}
    score = 0
    stance_label = str(payload.get('stance_label') or '')
    confidence = str(payload.get('confidence') or '')
    summary = str(payload.get('summary') or '')
    if stance_label == '质疑反对':
        score += 4
    elif stance_label == '谨慎保留':
        score += 3
    elif stance_label == '中立分析':
        score += 2
    if confidence == 'low':
        score += 1
    for question in open_questions or []:
        if question and any(token in summary for token in re.split(r'[，、：；\s]+', question) if len(token) >= 2):
            score += 2
            break
    return score


def _build_focused_round_queue(group: WerewolfGame):
    participant_ids = _discussion_speaker_ids(group)
    stance_map = _get_stance_map(group)
    open_questions = _get_consensus_state(group).get('open_questions') or _get_discussion_plan(group).get('focus_points') or []
    decorated = []
    for index, seat_id in enumerate(participant_ids):
        decorated.append((-_relevance_score(seat_id, stance_map, open_questions), index, seat_id))
    decorated.sort()
    return [seat_id for _, _, seat_id in decorated]


def _build_final_response_queue(group: WerewolfGame):
    return _build_focused_round_queue(group)[: min(3, group.seats.count())]


def _prior_public_speeches(group: WerewolfGame, round_number: int):
    return list(
        WerewolfSpeech.objects.filter(
            game=group,
            phase='day_speeches',
            day_number=round_number,
            audience='public',
        ).select_related('seat').order_by('id')
    )


def _participant_names(group: WerewolfGame):
    return [seat.display_name for seat in _ordered_participants(group)]


def _mark_group_node_failure(group: WerewolfGame, dag_runtime, node, *, failure_code: str, failure_reason: str):
    failure_payload = {
        'kind': node['kind'],
        'stage': str(node.get('data', {}).get('stage') or ''),
        'failure_code': failure_code,
        'failure_reason': failure_reason,
        'retryable': True,
    }
    mark_node_failed(dag_runtime, node, failure_payload)
    state = _ensure_state_dict(group)
    failure = {
        'node_id': str(node.get('id') or ''),
        'node_kind': str(node.get('kind') or ''),
        'stage': str(node.get('data', {}).get('stage') or ''),
        'failure_code': failure_code,
        'failure_reason': failure_reason,
        'retryable': True,
        'failed_at': timezone.now().isoformat(),
    }
    state['runtime_status'] = RUNTIME_STATUS_BLOCKED
    state['failed_node'] = {
        'id': failure['node_id'],
        'kind': failure['node_kind'],
        'stage': failure['stage'],
    }
    state['last_failure'] = failure
    _set_dag_runtime_state(group, dag_runtime)
    group.save(update_fields=['state', 'updated_at'])
    _add_event(
        group,
        event_type='node_failed',
        title='节点执行失败',
        content=failure_reason,
        payload={
            'failure_code': failure_code,
            'failure_reason': failure_reason,
            'failed_node_kind': failure['node_kind'],
            'failed_node_id': failure['node_id'],
            'stage': failure['stage'],
            'retryable': True,
        },
    )


def _build_focus_points_from_speeches(prior_speeches, *, agenda_items, stance_map):
    focus_points = []
    focus_points.extend(agenda_items or [])
    skeptical_names = []
    for stance in stance_map.values():
        if not isinstance(stance, dict):
            continue
        if stance.get('stance_label') in ('谨慎保留', '质疑反对'):
            skeptical_names.append(str(stance.get('participant_name') or '').strip())
    if skeptical_names:
        focus_points.append(f'优先回应{ "、".join(name for name in skeptical_names if name) }提出的保留意见。')
    return _dedupe_text_items(focus_points, limit=4)


def _validate_participant_plan(plan, *, discussion_plan, consensus_state, visible_speeches):
    if not isinstance(plan, dict):
        return FAILURE_CODE_INVALID_PLAN, '发言提纲未返回有效 JSON。'
    required_fields = ('new_information', 'agenda_item', 'stance_label')
    for field in required_fields:
        if not str(plan.get(field) or '').strip():
            return FAILURE_CODE_INVALID_PLAN, f'发言提纲缺少必要字段：{field}。'
    new_information = str(plan.get('new_information') or '').strip()
    if not _contains_meaningful_new_information(
        new_information,
        discussion_plan=discussion_plan,
        consensus_state=consensus_state,
        recent_speeches=visible_speeches,
    ):
        return FAILURE_CODE_NO_NEW_INFORMATION, '发言提纲没有提供有效的新信息点。'
    return '', ''


def _validate_moderator_plan(plan, *, stage: str):
    if not isinstance(plan, dict):
        return FAILURE_CODE_INVALID_MODERATOR_PLAN, '主持发言未返回有效 JSON。'
    if not str(plan.get('content') or '').strip():
        return FAILURE_CODE_INVALID_MODERATOR_PLAN, '主持发言缺少 content。'
    if stage in ('topic_opening', 'agenda_setup'):
        if not _normalize_text_items_field(plan.get('agenda_items'), limit=4):
            return FAILURE_CODE_INVALID_MODERATOR_PLAN, '主持发言缺少 agenda_items。'
    if stage == 'round_summary' and not str(plan.get('new_focus') or '').strip():
        return FAILURE_CODE_INVALID_MODERATOR_PLAN, '主持发言没有抽出新的焦点。'
    if stage == 'consensus_draft' and not str(plan.get('consensus_draft') or '').strip():
        return FAILURE_CODE_INVALID_MODERATOR_PLAN, '主持发言没有形成共识草案。'
    return '', ''


def _validate_moderator_content(content: str, *, topic: str, stage: str, recent_events):
    text = str(content or '').strip()
    if len(_normalize_similarity_text(text)) < MIN_CONTENT_LENGTH:
        return FAILURE_CODE_TOO_SHORT, '主持输出过短或没有实质内容。', 0.0
    if _contains_off_topic_or_leakage(text):
        return FAILURE_CODE_LEAKAGE, '主持输出越界或泄漏系统信息。', 0.0
    comparable_events = [
        event for event in recent_events
        if getattr(event, 'event_type', '') in ('moderator_opening', 'agenda_setup', 'moderator_summary', 'consensus_draft')
    ]
    if comparable_events:
        similarity = max(_similarity_score(text, event.content) for event in comparable_events if getattr(event, 'content', ''))
        if similarity >= 0.97:
            return FAILURE_CODE_DUPLICATE_CONTENT, '主持输出与最近事件高度重复。', similarity
    normalized_text = _normalize_similarity_text(text)
    normalized_topic = _normalize_similarity_text(topic)
    if normalized_text == normalized_topic:
        return FAILURE_CODE_NO_NEW_INFORMATION, '主持输出只是在重复主题。', 1.0
    return '', '', 0.0


def _coerce_moderator_payload(payload):
    normalized_payload = payload if isinstance(payload, dict) else {}
    agenda_items = _normalize_text_items_field(normalized_payload.get('agenda_items'), limit=4)
    focus_points = _normalize_text_items_field(normalized_payload.get('focus_points'), limit=4)
    resolved_points = _normalize_text_items_field(normalized_payload.get('resolved_points'), limit=4)
    open_questions = _normalize_text_items_field(normalized_payload.get('open_questions'), limit=4)
    round_goal = str(normalized_payload.get('round_goal') or '').strip()
    new_focus = str(normalized_payload.get('new_focus') or '').strip()
    consensus_draft = str(normalized_payload.get('consensus_draft') or '').strip()
    content = str(normalized_payload.get('content') or '').strip()

    return {
        **normalized_payload,
        'content': content,
        'round_goal': round_goal,
        'new_focus': new_focus,
        'consensus_draft': consensus_draft,
        'agenda_items': agenda_items,
        'focus_points': focus_points,
        'resolved_points': resolved_points,
        'open_questions': open_questions,
    }


def _validate_participant_content(content: str, *, seat: WerewolfSeat, topic: str, visible_speeches, previous_summary: str, plan, discussion_plan, consensus_state, unspoken_names):
    text = str(content or '').strip()
    if len(_normalize_similarity_text(text)) < MIN_CONTENT_LENGTH:
        return FAILURE_CODE_TOO_SHORT, '发言过短或没有实质内容。', 0.0
    if _contains_off_topic_or_leakage(text):
        return FAILURE_CODE_LEAKAGE, '发言越界或暴露系统信息。', 0.0
    if _contains_unspoken_speech_reference(text, unspoken_names):
        return FAILURE_CODE_UNSPOKEN_REFERENCE, '发言引用了尚未公开的未来内容。', 0.0

    max_similarity = 0.0
    for speech in visible_speeches[-3:]:
        max_similarity = max(max_similarity, _similarity_score(text, speech.content))
    if max_similarity >= SIMILARITY_FAILURE_THRESHOLD:
        return FAILURE_CODE_DUPLICATE_CONTENT, '发言与最近公开内容高度重复。', max_similarity

    self_similarity = _similarity_score(text, previous_summary)
    if self_similarity >= SELF_SIMILARITY_FAILURE_THRESHOLD:
        return FAILURE_CODE_DUPLICATE_SELF, '发言与自己上一轮核心内容过于相似。', self_similarity

    new_information = str(plan.get('new_information') or '').strip()
    if not _contains_meaningful_new_information(
        new_information,
        discussion_plan=discussion_plan,
        consensus_state=consensus_state,
        recent_speeches=visible_speeches,
    ):
        return FAILURE_CODE_NO_NEW_INFORMATION, '发言提纲没有提供有效的新信息点。', 0.0

    return '', '', max_similarity


def _execute_dag_node(group: WerewolfGame, dag_runtime, node):
    handler_map = {
        NodeKind.MODERATOR_OPENING: _execute_moderator_opening_node,
        NodeKind.AGENDA_SETUP: _execute_agenda_setup_node,
        NodeKind.OPENING_TURN: _execute_turn_node,
        NodeKind.ROUND_SUMMARY: _execute_round_summary_node,
        NodeKind.FOCUSED_TURN: _execute_turn_node,
        NodeKind.CONSENSUS_DRAFT: _execute_consensus_draft_node,
        NodeKind.FINAL_RESPONSE_TURN: _execute_turn_node,
        NodeKind.FINISH: _execute_finish_node,
    }
    handler = handler_map.get(node['kind'])
    if not handler:
        raise ValueError(f"未知讨论 DAG 节点：{node['kind']}")
    try:
        payload = handler(group, dag_runtime, node) or {}
    except RuntimeError as error:
        message = str(error)
        parts = message.split('|', 1)
        failure_code = parts[0].strip() if parts else FAILURE_CODE_GENERATION_EMPTY
        failure_reason = parts[1].strip() if len(parts) > 1 else message
        _mark_group_node_failure(
            group,
            dag_runtime,
            node,
            failure_code=failure_code or FAILURE_CODE_GENERATION_EMPTY,
            failure_reason=failure_reason or '生成失败。',
        )
        return {
            'failed': True,
            'failure_code': failure_code or FAILURE_CODE_GENERATION_EMPTY,
            'failure_reason': failure_reason or '生成失败。',
            'stage': str(node.get('data', {}).get('stage') or ''),
        }
    _mark_dag_node_completed(dag_runtime, node, payload)
    _clear_failure_state(group)
    _set_dag_runtime_state(group, dag_runtime)
    group.save(update_fields=['state', 'updated_at'])
    return payload


def _execute_moderator_node(group: WerewolfGame, *, node, stage: str, event_type: str, title: str):
    round_number = int(node['data'].get('round_number', 1) or 1)
    topic = _get_topic(group)
    max_rounds = _get_max_rounds(group)
    prior_speeches = _prior_public_speeches(group, round_number)
    discussion_plan = _get_discussion_plan(group)
    consensus_state = _get_consensus_state(group)
    stance_map = _get_stance_map(group)
    participant_names = _participant_names(group)
    moderator_seat = _get_moderator_seat(group)
    if moderator_seat is None:
        raise RuntimeError(f'{FAILURE_CODE_INVALID_MODERATOR_PLAN}|当前讨论组缺少主持人。')

    payload = _generate_moderator_payload(
        seat=moderator_seat,
        topic=topic,
        stage=stage,
        round_number=round_number,
        max_rounds=max_rounds,
        participant_names=participant_names,
        prior_speeches=prior_speeches,
        discussion_plan=discussion_plan,
        consensus_state=consensus_state,
        stance_map=stance_map,
    )
    payload = _coerce_moderator_payload(payload)
    failure_code, failure_reason = _validate_moderator_plan(payload, stage=stage)
    if failure_code:
        raise RuntimeError(f'{failure_code}|{failure_reason}')

    agenda_items = _normalize_text_items_field(payload.get('agenda_items'), limit=4)
    focus_points = _dedupe_text_items([payload.get('new_focus')] + _normalize_text_items_field(payload.get('focus_points'), limit=4), limit=4)
    resolved_points = _normalize_text_items_field(payload.get('resolved_points'), limit=4)
    open_questions = _normalize_text_items_field(payload.get('open_questions'), limit=4)
    route = str(payload.get('route') or '').strip()
    round_goal = str(payload.get('round_goal') or '').strip()
    moderator_question = str(payload.get('new_focus') or '').strip()
    consensus_draft = str(payload.get('consensus_draft') or '').strip()
    content = str(payload.get('content') or '').strip()
    failure_code, failure_reason, similarity_score = _validate_moderator_content(
        content,
        topic=topic,
        stage=stage,
        recent_events=list(group.events.order_by('-id')[:3]),
    )
    if failure_code:
        raise RuntimeError(f'{failure_code}|{failure_reason}')

    if stage == 'topic_opening':
        group.day_number = round_number
        group.night_number = 0
        group.status = 'active'
        group.phase = 'day_speeches'
        group.save(update_fields=['day_number', 'night_number', 'status', 'phase', 'updated_at'])

    _update_discussion_state(
        group,
        stage=stage,
        round_number=round_number,
        agenda_items=agenda_items if agenda_items else discussion_plan.get('agenda_items'),
        round_goal=round_goal or discussion_plan.get('round_goal'),
        focus_points=focus_points if focus_points else discussion_plan.get('focus_points'),
        moderator_question=moderator_question or discussion_plan.get('moderator_question'),
        resolved_points=resolved_points if resolved_points else consensus_state.get('resolved_points'),
        open_questions=open_questions if open_questions else consensus_state.get('open_questions'),
        consensus_draft=consensus_draft or consensus_state.get('consensus_draft'),
    )
    _apply_stance_updates(group, payload.get('stance_updates'))

    event_payload = {
        'stage': stage,
        'stage_label': get_discussion_stage_label(stage),
        'topic': topic,
        'round_number': round_number,
        'moderator_participant_id': moderator_seat.id,
        'moderator_participant_name': moderator_seat.display_name,
        'agenda_items': _get_discussion_plan(group).get('agenda_items', []),
        'round_goal': _get_discussion_plan(group).get('round_goal', ''),
        'focus_points': _get_discussion_plan(group).get('focus_points', []),
        'moderator_question': _get_discussion_plan(group).get('moderator_question', ''),
        'resolved_points': _get_consensus_state(group).get('resolved_points', []),
        'open_questions': _get_consensus_state(group).get('open_questions', []),
        'consensus_draft': _get_consensus_state(group).get('consensus_draft', ''),
        'route': route,
        'validation_passed': True,
        'similarity_score': round(similarity_score, 4),
    }

    _add_public_speech(
        group,
        seat=moderator_seat,
        round_number=round_number,
        content=content,
        metadata={
            'topic': topic,
            'phase': stage,
            'phase_label': get_discussion_stage_label(stage),
            'stage': stage,
            'stage_label': get_discussion_stage_label(stage),
            'round_number': round_number,
            'is_moderator_speech': True,
            'moderator_question': event_payload['moderator_question'],
            'agenda_items': event_payload['agenda_items'],
            'focus_points': event_payload['focus_points'],
            'resolved_points': event_payload['resolved_points'],
            'open_questions': event_payload['open_questions'],
            'consensus_draft': event_payload['consensus_draft'],
            'validation_passed': True,
            'similarity_score': round(similarity_score, 4),
        },
    )

    _add_event(
        group,
        event_type=event_type,
        title=title,
        content=content,
        payload=event_payload,
    )
    return {
        'kind': node['kind'],
        'round_number': round_number,
        'stage': stage,
        'route': route,
    }


def _execute_moderator_opening_node(group: WerewolfGame, dag_runtime, node):
    return _execute_moderator_node(
        group,
        node=node,
        stage='topic_opening',
        event_type='moderator_opening',
        title='主持人开场',
    )


def _execute_agenda_setup_node(group: WerewolfGame, dag_runtime, node):
    return _execute_moderator_node(
        group,
        node=node,
        stage='agenda_setup',
        event_type='agenda_setup',
        title='主持人拆解议题',
    )


def _execute_turn_node(group: WerewolfGame, dag_runtime, node):
    topic = _get_topic(group)
    round_number = int(node['data'].get('round_number', group.day_number or 1) or 1)
    participant_ids = [int(seat_id) for seat_id in node['data'].get('participant_ids', [])]
    seat_id = int(node['data'].get('seat_id', 0) or 0)
    turn_index = int(node['data'].get('turn_index', 1) or 1)
    stage = str(node['data'].get('stage') or '')
    participant_map = {seat.id: seat for seat in _ordered_participants(group)}
    seat = participant_map.get(seat_id)
    if seat is None:
        return {
            'kind': node['kind'],
            'round_number': round_number,
            'seat_id': seat_id,
            'skipped': True,
            'stage': stage,
        }

    prior_public_speeches = _prior_public_speeches(group, round_number)
    all_prior_public_speeches = list(
        WerewolfSpeech.objects.filter(
            game=group,
            phase='day_speeches',
            audience='public',
        ).select_related('seat').order_by('id')
    )
    participant_prior_public_speeches = [
        speech for speech in prior_public_speeches
        if not _is_moderator_speech_record(speech)
    ]
    if any(speech.seat_id == seat.id for speech in participant_prior_public_speeches):
        return {
            'kind': node['kind'],
            'round_number': round_number,
            'seat_id': seat.id,
            'skipped': True,
            'stage': stage,
        }

    spoken_seat_ids = {
        speech.seat_id for speech in all_prior_public_speeches
        if not _is_moderator_speech_record(speech)
    }
    unspoken_names = [
        participant_map[current_id].display_name
        for current_id in participant_ids
        if current_id != seat.id and current_id in participant_map and current_id not in spoken_seat_ids
    ]
    visible_speeches = prior_public_speeches[-MAX_VISIBLE_SPEECHES:]
    current_turn = len(participant_prior_public_speeches) + 1
    total_turn = len(participant_ids)
    visible_speech_ids = [speech.id for speech in visible_speeches]
    discussion_plan = _get_discussion_plan(group)
    consensus_state = _get_consensus_state(group)
    stance_map = _get_stance_map(group)
    previous_stance_summary = str(stance_map.get(str(seat.id), {}).get('summary') or '').strip()
    public_state = _discussion_public_state(
        group,
        topic=topic,
        stage=stage,
        round_number=round_number,
        prior_speeches=visible_speeches,
        moderator_question=str(discussion_plan.get('moderator_question') or ''),
        agenda_items=discussion_plan.get('agenda_items') or [],
        focus_points=discussion_plan.get('focus_points') or [],
        previous_stance=previous_stance_summary,
    )
    private_state = _discussion_private_state(seat)
    plan = _plan_participant_turn(
        seat=seat,
        topic=topic,
        public_state=public_state,
        private_state=private_state,
        stage=stage,
    )
    failure_code, failure_reason = _validate_participant_plan(
        plan,
        discussion_plan=discussion_plan,
        consensus_state=consensus_state,
        visible_speeches=visible_speeches,
    )
    if failure_code:
        raise RuntimeError(f'{failure_code}|{failure_reason}')

    if stage == 'opening_turn':
        stage_instruction = (
            f'现在是开场立场轮。你是本轮第 {current_turn}/{total_turn} 位。'
            '必须围绕发言提纲表达一个明确立场和新增判断，不要空泛地讲“先界定边界”。'
        )
    elif stage == 'focused_turn':
        stage_instruction = (
            f'现在是聚焦讨论轮。你是本轮第 {current_turn}/{total_turn} 位。'
            '必须回应发言提纲里的目标对象或焦点，并提出新的风险、代价、标准或替代方案。'
        )
    else:
        stage_instruction = (
            f'现在是最后补充环节。你是本轮第 {current_turn}/{total_turn} 位。'
            '只补最关键的异议或确认，不能重复前面已经说过的核心句。'
        )
    content = generate_discussion_reply(
        seat,
        topic=topic,
        public_state=public_state,
        private_state=private_state,
        stage_instruction=stage_instruction,
        plan=plan,
    )
    if not content:
        raise RuntimeError(f'{FAILURE_CODE_GENERATION_EMPTY}|模型没有返回有效发言。')

    failure_code, failure_reason, similarity_score = _validate_participant_content(
        content,
        seat=seat,
        topic=topic,
        visible_speeches=visible_speeches,
        previous_summary=previous_stance_summary,
        plan=plan,
        discussion_plan=discussion_plan,
        consensus_state=consensus_state,
        unspoken_names=unspoken_names,
    )
    if failure_code:
        raise RuntimeError(f'{failure_code}|{failure_reason}')

    response_target = str(plan.get('response_target') or '').strip()
    reply_to_speech_ids = []
    if response_target:
        for speech in visible_speeches:
            if speech.seat.display_name == response_target:
                reply_to_speech_ids.append(speech.id)
    if not reply_to_speech_ids and visible_speeches:
        reply_to_speech_ids.append(visible_speeches[-1].id)

    new_information = str(plan.get('new_information') or '').strip()
    agenda_item = str(plan.get('agenda_item') or '').strip()
    addressed_agenda_items = _infer_addressed_agenda_items(
        content,
        agenda_items=discussion_plan.get('agenda_items') or [],
        focus_points=discussion_plan.get('focus_points') or [],
    )
    if agenda_item and agenda_item not in addressed_agenda_items:
        addressed_agenda_items = _dedupe_text_items([agenda_item] + addressed_agenda_items, limit=3)

    _update_stance_from_speech(
        group,
        seat,
        round_number=round_number,
        content=content,
        contribution=new_information,
    )
    stance_label = _get_stance_map(group).get(str(seat.id), {}).get('stance_label', str(plan.get('stance_label') or '待表达'))

    _add_public_speech(
        group,
        seat=seat,
        round_number=round_number,
        content=content,
        metadata={
            'topic': topic,
            'phase': stage,
            'phase_label': get_discussion_stage_label(stage),
            'visible_speech_ids': visible_speech_ids,
            'visible_speech_count': len(visible_speech_ids),
            'current_turn': current_turn,
            'total_turn': total_turn,
            'reply_to_speech_ids': reply_to_speech_ids,
            'stance_label': stance_label,
            'addresses_agenda_items': addressed_agenda_items,
            'plan': plan,
            'new_information': new_information,
            'response_target': response_target,
            'validation_passed': True,
            'similarity_score': round(similarity_score, 4),
        },
    )
    _update_discussion_state(group, stage=stage, round_number=round_number)
    return {
        'kind': node['kind'],
        'round_number': round_number,
        'seat_id': seat.id,
        'turn_index': turn_index,
        'stage': stage,
        'response_target': response_target,
    }


def _execute_round_summary_node(group: WerewolfGame, dag_runtime, node):
    payload = _execute_moderator_node(
        group,
        node=node,
        stage='round_summary',
        event_type='moderator_summary',
        title=f'主持人总结 · 第 {int(node["data"].get("round_number", group.day_number or 1) or 1)} 轮',
    )
    round_number = int(node['data'].get('round_number', group.day_number or 1) or 1)
    route = str(payload.get('route') or '').strip()
    if round_number < _get_max_rounds(group) and route not in ('consensus', 'finish', 'final_response'):
        append_focused_round(
            dag_runtime,
            round_number=round_number + 1,
            participant_ids=_build_focused_round_queue(group),
            depends_on=node['id'],
        )
        route = 'continue'
    else:
        append_consensus_draft(
            dag_runtime,
            round_number=round_number,
            depends_on=node['id'],
        )
        route = 'consensus'
    payload['route'] = route
    return payload


def _execute_consensus_draft_node(group: WerewolfGame, dag_runtime, node):
    payload = _execute_moderator_node(
        group,
        node=node,
        stage='consensus_draft',
        event_type='consensus_draft',
        title='主持人给出共识草案',
    )
    round_number = int(node['data'].get('round_number', group.day_number or 1) or 1)
    route = str(payload.get('route') or '').strip()
    if route == 'final_response':
        final_round = append_final_response_round(
            dag_runtime,
            round_number=round_number + 1,
            participant_ids=_build_final_response_queue(group),
            depends_on=node['id'],
        )
        append_discussion_finish(
            dag_runtime,
            round_number=round_number + 1,
            depends_on=final_round['last_node_id'],
        )
    else:
        append_discussion_finish(
            dag_runtime,
            round_number=round_number,
            depends_on=node['id'],
        )
    return payload


def _execute_finish_node(group: WerewolfGame, dag_runtime, node):
    topic = _get_topic(group)
    total_speeches = group.speeches.filter(audience='public').count()
    completed_rounds = max(group.day_number, int(node['data'].get('round_number', group.day_number or 1) or 1))
    consensus_state = _get_consensus_state(group)
    _update_discussion_state(
        group,
        stage='discussion_finish',
        round_number=completed_rounds,
        final_summary=consensus_state.get('consensus_draft') or consensus_state.get('final_summary'),
    )
    _clear_failure_state(group)
    group.status = 'finished'
    group.phase = 'finished'
    group.winner = ''
    group.save(update_fields=['status', 'phase', 'winner', 'state', 'updated_at'])
    _add_event(
        group,
        event_type='game_finished',
        title='讨论已完成',
        content=f'围绕“{topic}”的讨论已结束，共完成 {completed_rounds} 轮，累计 {total_speeches} 段发言。',
        payload={
            'stage': 'discussion_finish',
            'stage_label': get_discussion_stage_label('discussion_finish'),
            'topic': topic,
            'completed_rounds': completed_rounds,
            'speech_count': total_speeches,
            'resolved_points': consensus_state.get('resolved_points', []),
            'open_questions': consensus_state.get('open_questions', []),
            'consensus_draft': consensus_state.get('consensus_draft', ''),
            'final_summary': consensus_state.get('final_summary', ''),
        },
    )
    return {
        'kind': node['kind'],
        'round_number': completed_rounds,
        'speech_count': total_speeches,
        'stage': 'discussion_finish',
    }


@transaction.atomic
def create_discussion_group(*, title: str, topic: str, character_ids, max_rounds: int = DEFAULT_MAX_ROUNDS):
    normalized_ids = validate_discussion_roster(character_ids)
    topic_text = str(topic or '').strip()[:MAX_TOPIC_LENGTH]
    if not topic_text:
        raise ValueError('讨论主题不能为空。')
    max_rounds = max(2, min(6, int(max_rounds or DEFAULT_MAX_ROUNDS)))
    characters = list(Character.objects.select_related('voice').filter(id__in=normalized_ids))
    character_map = {character.id: character for character in characters}
    if len(character_map) != len(normalized_ids):
        raise ValueError('有角色不存在，无法创建讨论组。')

    group = WerewolfGame.objects.create(
        title=str(title or '').strip() or '讨论组',
        status='waiting',
        phase='setup',
        day_number=0,
        night_number=0,
        state={
            'mode': DISCUSSION_MODE,
            'topic': topic_text,
            'max_rounds': max_rounds,
            'discussion_plan': _empty_discussion_plan(),
            'stance_map': {},
            'consensus_state': _empty_consensus_state(),
            'runtime_status': RUNTIME_STATUS_READY,
            'failed_node': {},
            'last_failure': _empty_last_failure(),
        },
    )
    for index, character_id in enumerate(normalized_ids, start=1):
        character = character_map[character_id]
        WerewolfSeat.objects.create(
            game=group,
            character=character,
            source_type='character',
            seat_order=index,
            display_name=character.name,
            profile=character.profile,
            custom_prompt=character.custom_prompt,
            voice=character.voice,
            photo=character.photo,
            background_image=character.background_image,
            reply_style=character.reply_style,
            reply_length=character.reply_length,
            initiative_level=character.initiative_level,
            memory_mode='off',
            persona_boundary=character.persona_boundary,
            identity='',
            is_alive=True,
            is_revealed=False,
        )
    participants = _ordered_participants(group)
    moderator_seat_id = participants[0].id if participants else 0
    _ensure_state_dict(group)['stance_map'] = _build_initial_stance_map(participants)
    _ensure_state_dict(group)['moderator_seat_id'] = moderator_seat_id
    _add_event(
        group,
        event_type='game_created',
        title='讨论组已创建',
        content=f'讨论主题：{topic_text}。已选 {len(normalized_ids)} 个角色，由{participants[0].display_name if participants else "首位角色"}担任主持。',
        payload={
            'topic': topic_text,
            'participant_count': len(normalized_ids),
            'max_rounds': max_rounds,
            'moderator_participant_id': moderator_seat_id,
            'moderator_participant_name': participants[0].display_name if participants else '',
            'stage': 'setup',
            'stage_label': get_discussion_stage_label('setup'),
        },
    )
    dag_runtime = build_initial_discussion_dag_runtime(
        participant_ids=_build_opening_round_queue(group),
        moderator_seat_id=moderator_seat_id,
        max_rounds=max_rounds,
    )
    _set_dag_runtime_state(group, dag_runtime)
    group.save(update_fields=['state', 'updated_at'])
    return group


def advance_discussion_group(group: WerewolfGame, observer_note: str = '', retry_failed_node_requested: bool = False):
    if group.status == 'finished' or group.phase == 'finished':
        raise ValueError('当前讨论组已结束，不能继续推进。')
    _assert_discussion_group(group)

    if observer_note.strip():
        group.observer_note = observer_note.strip()[:1000]
        group.save(update_fields=['observer_note', 'updated_at'])
        _add_event(group, event_type='note', title='观察者备注', content=group.observer_note, payload={})

    dag_runtime = _ensure_dag_runtime(group)
    runtime_status = _get_runtime_status(group)
    if runtime_status == RUNTIME_STATUS_BLOCKED:
        failed_node = _get_failed_node(group)
        if not retry_failed_node_requested:
            failure = _get_last_failure(group)
            raise ValueError(f"当前讨论组已暂停：{failure.get('failure_reason') or '存在失败节点。'}")
        failed_node_id = str(failed_node.get('id') or '')
        if not failed_node_id:
            raise ValueError('当前失败节点缺失，无法重试。')
        retry_failed_node(dag_runtime, failed_node_id)
        _clear_failure_state(group)
        _set_dag_runtime_state(group, dag_runtime)
        group.save(update_fields=['state', 'updated_at'])

    node = pop_ready_node(dag_runtime)
    if not node:
        raise ValueError('当前没有可执行的流程节点。')
    payload = _execute_dag_node(group, dag_runtime, node)
    group.refresh_from_db()
    if isinstance(payload, dict) and payload.get('failed'):
        return group
    return group


@transaction.atomic
def reset_discussion_group(group: WerewolfGame):
    participants = list(group.seats.order_by('seat_order', 'id'))
    _assert_discussion_group(group, participants=participants)
    group.events.all().delete()
    group.speeches.all().delete()
    topic = _get_topic(group)
    max_rounds = _get_max_rounds(group)
    group.status = 'waiting'
    group.phase = 'setup'
    group.day_number = 0
    group.night_number = 0
    group.winner = ''
    group.observer_note = ''
    group.state = {
        'mode': DISCUSSION_MODE,
        'topic': topic,
        'max_rounds': max_rounds,
        'moderator_seat_id': participants[0].id if participants else 0,
        'discussion_plan': _empty_discussion_plan(),
        'stance_map': _build_initial_stance_map(participants),
        'consensus_state': _empty_consensus_state(),
        'runtime_status': RUNTIME_STATUS_READY,
        'failed_node': {},
        'last_failure': _empty_last_failure(),
    }
    dag_runtime = build_initial_discussion_dag_runtime(
        participant_ids=_build_opening_round_queue(group),
        moderator_seat_id=participants[0].id if participants else 0,
        max_rounds=max_rounds,
    )
    _set_dag_runtime_state(group, dag_runtime)
    group.save(update_fields=['status', 'phase', 'day_number', 'night_number', 'winner', 'observer_note', 'state', 'updated_at'])
    _add_event(
        group,
        event_type='game_reset',
        title='讨论组已重置',
        content=f'讨论主题仍为“{topic}”。你可以重新开始这一组讨论。',
        payload={
            'topic': topic,
            'participant_count': len(participants),
            'max_rounds': max_rounds,
            'moderator_participant_id': participants[0].id if participants else 0,
            'moderator_participant_name': participants[0].display_name if participants else '',
            'stage': 'setup',
            'stage_label': get_discussion_stage_label('setup'),
        },
    )
    return group
