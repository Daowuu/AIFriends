from __future__ import annotations

import random
from collections import Counter

from django.db import transaction
from openai import OpenAI

from web.ai_settings_service import get_runtime_ai_resolution
from web.chat_services import strip_reasoning_content
from web.models import Character, WerewolfEvent, WerewolfGame, WerewolfSeat, WerewolfSpeech


BASE_WEREWOLF_TEMPLATE = ['wolf', 'wolf', 'seer', 'villager', 'villager']
MAX_PUBLIC_EVENTS = 160
MAX_PUBLIC_SPEECHES = 160


def get_game_phase_label(phase: str):
    return {
        'setup': '准备阶段',
        'night': '夜晚',
        'day_speeches': '白天发言',
        'vote': '投票阶段',
        'finished': '已结束',
    }.get(phase, phase)


def get_identity_label(identity: str):
    return {
        'wolf': '狼人',
        'seer': '预言家',
        'villager': '平民',
    }.get(identity, identity)


def serialize_werewolf_game(game: WerewolfGame):
    return {
        'id': game.id,
        'title': game.title,
        'status': game.status,
        'phase': game.phase,
        'phase_label': get_game_phase_label(game.phase),
        'day_number': game.day_number,
        'night_number': game.night_number,
        'winner': game.winner,
        'winner_label': '好人阵营' if game.winner == 'villagers' else ('狼人阵营' if game.winner == 'wolves' else ''),
        'observer_note': game.observer_note,
        'created_at': game.created_at.isoformat(),
        'updated_at': game.updated_at.isoformat(),
    }


def serialize_werewolf_seat(seat: WerewolfSeat):
    return {
        'id': seat.id,
        'character_id': seat.character_id,
        'source_type': seat.source_type,
        'seat_order': seat.seat_order,
        'display_name': seat.display_name,
        'profile': seat.profile,
        'custom_prompt': seat.custom_prompt,
        'photo': seat.photo.url if seat.photo else '',
        'background_image': seat.background_image.url if seat.background_image else '',
        'voice_name': seat.voice.name if seat.voice else '',
        'voice_model_name': seat.voice.model_name if seat.voice else '',
        'identity': seat.identity,
        'identity_label': get_identity_label(seat.identity),
        'is_alive': seat.is_alive,
        'is_revealed': seat.is_revealed,
        'reply_style': seat.reply_style,
        'reply_length': seat.reply_length,
        'initiative_level': seat.initiative_level,
        'persona_boundary': seat.persona_boundary,
    }


def serialize_werewolf_event(event: WerewolfEvent):
    return {
        'id': event.id,
        'event_type': event.event_type,
        'phase': event.phase,
        'phase_label': get_game_phase_label(event.phase) if event.phase else '',
        'day_number': event.day_number,
        'night_number': event.night_number,
        'title': event.title,
        'content': event.content,
        'payload': event.payload,
        'created_at': event.created_at.isoformat(),
    }


def serialize_werewolf_speech(speech: WerewolfSpeech):
    return {
        'id': speech.id,
        'seat_id': speech.seat_id,
        'seat_name': speech.seat.display_name,
        'phase': speech.phase,
        'phase_label': get_game_phase_label(speech.phase),
        'day_number': speech.day_number,
        'night_number': speech.night_number,
        'audience': speech.audience,
        'content': speech.content,
        'metadata': speech.metadata,
        'created_at': speech.created_at.isoformat(),
    }


def build_werewolf_game_detail(game: WerewolfGame):
    seats = list(game.seats.select_related('voice').order_by('seat_order', 'id'))
    events = list(game.events.order_by('id')[:MAX_PUBLIC_EVENTS])
    speeches = list(game.speeches.select_related('seat').order_by('id')[:MAX_PUBLIC_SPEECHES])
    return {
        'game': serialize_werewolf_game(game),
        'seats': [serialize_werewolf_seat(seat) for seat in seats],
        'events': [serialize_werewolf_event(event) for event in events],
        'speeches': [serialize_werewolf_speech(speech) for speech in speeches],
    }


def list_werewolf_games():
    return [
        serialize_werewolf_game(game)
        for game in WerewolfGame.objects.order_by('-updated_at', '-id')
    ]


def validate_werewolf_roster(character_ids, custom_seats):
    character_ids = [int(character_id) for character_id in character_ids if int(character_id)]
    custom_seats = [seat for seat in custom_seats if str(seat.get('display_name', '')).strip()]
    total = len(character_ids) + len(custom_seats)
    if total != len(BASE_WEREWOLF_TEMPLATE):
        raise ValueError(f'基础局需要正好 {len(BASE_WEREWOLF_TEMPLATE)} 个席位。当前收到 {total} 个。')
    return character_ids, custom_seats


def _normalize_custom_seat(payload):
    return {
        'display_name': str(payload.get('display_name', '')).strip()[:64],
        'profile': str(payload.get('profile', '')).strip()[:1600],
        'custom_prompt': str(payload.get('custom_prompt', '')).strip()[:2400],
        'reply_style': str(payload.get('reply_style', 'natural')).strip() or 'natural',
        'reply_length': str(payload.get('reply_length', 'balanced')).strip() or 'balanced',
        'initiative_level': str(payload.get('initiative_level', 'balanced')).strip() or 'balanced',
        'persona_boundary': str(payload.get('persona_boundary', 'grounded')).strip() or 'grounded',
    }


def _get_runtime_client():
    resolution = get_runtime_ai_resolution()
    if resolution['status'] == 'invalid':
        raise RuntimeError('当前聊天运行时配置不完整，无法生成狼人杀角色发言。')

    runtime = resolution['config']
    if not runtime:
        return None, None

    client = OpenAI(
        api_key=runtime['api_key'],
        base_url=runtime['api_base'],
    )
    return client, runtime


def _fallback_werewolf_text(seat: WerewolfSeat, *, stage_instruction: str):
    prefix = {
        'wolf': '我会先隐藏身份，尽量顺着公共信息推进怀疑。',
        'seer': '我会谨慎发言，只在关键时机释放真实查验带来的判断。',
        'villager': '我会根据公开发言和投票结果做出朴素判断。',
    }.get(seat.identity, '我会根据当前局势做出回应。')
    return f'我是{seat.display_name}。{prefix}{stage_instruction}'


def generate_werewolf_role_reply(seat: WerewolfSeat, *, public_state: str, private_state: str, stage_instruction: str):
    client, runtime = _get_runtime_client()
    if not client or not runtime:
        return _fallback_werewolf_text(seat, stage_instruction=stage_instruction)

    system_prompt = (
        '你正在参加一场狼人杀原型对局。'
        '请严格扮演当前席位，不要跳出角色，不要暴露系统规则，不要说自己是 AI。'
        '请使用自然中文发言，内容简短、明确、像桌游中的真实讨论。'
    )
    user_prompt = '\n'.join([
        f'席位名：{seat.display_name}',
        f'角色设定：{seat.profile or "普通玩家，没有额外公开人设。"}',
        f'自定义 Prompt：{seat.custom_prompt or "无"}',
        f'发言风格：{seat.reply_style} / {seat.reply_length} / {seat.initiative_level} / {seat.persona_boundary}',
        f'真实身份：{get_identity_label(seat.identity)}',
        f'公共局势：{public_state}',
        f'私有信息：{private_state}',
        f'当前任务：{stage_instruction}',
        '请只输出这名玩家此刻会说的话，不要加标题，不要解释规则，不要使用项目符号。',
    ])
    try:
        response = client.chat.completions.create(
            model=runtime['model_name'],
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            temperature=0.9,
            max_tokens=220,
        )
        content = response.choices[0].message.content if response.choices else ''
        return strip_reasoning_content(content or '').strip() or _fallback_werewolf_text(seat, stage_instruction=stage_instruction)
    except Exception:
        return _fallback_werewolf_text(seat, stage_instruction=stage_instruction)


def _alive_seats(game: WerewolfGame):
    return list(game.seats.select_related('voice').filter(is_alive=True).order_by('seat_order', 'id'))


def _alive_non_wolves(game: WerewolfGame):
    return [seat for seat in _alive_seats(game) if seat.identity != 'wolf']


def _seer_check_map(game: WerewolfGame):
    checks = game.state.get('seer_checks', {})
    return checks if isinstance(checks, dict) else {}


def _write_seer_check(game: WerewolfGame, seer_seat: WerewolfSeat | None, target: WerewolfSeat | None):
    if not seer_seat or not target:
        return
    checks = _seer_check_map(game)
    checks[str(target.id)] = {
        'target_id': target.id,
        'target_name': target.display_name,
        'identity': target.identity,
        'night_number': game.night_number,
    }
    game.state['seer_checks'] = checks


def _public_alive_summary(game: WerewolfGame):
    alive = _alive_seats(game)
    dead = list(game.seats.filter(is_alive=False).order_by('seat_order', 'id'))
    alive_names = '、'.join(seat.display_name for seat in alive) or '无人'
    dead_names = '、'.join(seat.display_name for seat in dead) or '暂无'
    return f'当前是第 {max(game.day_number, 1)} 天。存活玩家：{alive_names}。已出局玩家：{dead_names}。'


def _private_state_for_seat(game: WerewolfGame, seat: WerewolfSeat):
    if seat.identity == 'wolf':
        allies = [ally.display_name for ally in _alive_seats(game) if ally.identity == 'wolf' and ally.id != seat.id]
        ally_text = '、'.join(allies) if allies else '无存活狼同伴'
        return f'你是狼人。你的存活狼同伴：{ally_text}。'

    if seat.identity == 'seer':
        checks = _seer_check_map(game)
        if not checks:
            return '你是预言家。你暂时还没有查验结果。'
        parts = [f"{value['target_name']} 是 {get_identity_label(value['identity'])}" for value in checks.values()]
        return '你是预言家。你目前掌握的查验结果：' + '；'.join(parts)

    return '你是平民。你没有额外夜晚信息，只能根据公开信息推理。'


def _add_event(game: WerewolfGame, *, event_type: str, title: str, content: str = '', payload=None):
    return WerewolfEvent.objects.create(
        game=game,
        event_type=event_type,
        phase=game.phase,
        day_number=game.day_number,
        night_number=game.night_number,
        title=title,
        content=content,
        payload=payload or {},
    )


def _determine_winner(game: WerewolfGame):
    alive = _alive_seats(game)
    wolf_count = len([seat for seat in alive if seat.identity == 'wolf'])
    villager_count = len(alive) - wolf_count
    if wolf_count <= 0:
        return 'villagers'
    if wolf_count >= villager_count:
        return 'wolves'
    return ''


def _pick_wolf_target(game: WerewolfGame):
    candidates = _alive_non_wolves(game)
    if not candidates:
        return None
    seer = next((seat for seat in candidates if seat.identity == 'seer'), None)
    return seer or random.choice(candidates)


def _pick_seer_target(game: WerewolfGame):
    seer = next((seat for seat in _alive_seats(game) if seat.identity == 'seer'), None)
    if not seer:
        return None, None
    checks = _seer_check_map(game)
    candidates = [seat for seat in _alive_seats(game) if seat.id != seer.id and str(seat.id) not in checks]
    if not candidates:
        candidates = [seat for seat in _alive_seats(game) if seat.id != seer.id]
    if not candidates:
        return seer, None
    preferred = next((seat for seat in candidates if seat.identity == 'wolf'), None)
    return seer, preferred or random.choice(candidates)


@transaction.atomic
def create_werewolf_game(*, title: str, character_ids, custom_seats):
    character_ids, custom_seats = validate_werewolf_roster(character_ids, custom_seats)
    game = WerewolfGame.objects.create(title=title.strip() or '狼人杀房间')

    selected_characters = list(Character.objects.select_related('voice').filter(id__in=character_ids))
    selected_characters_map = {character.id: character for character in selected_characters}
    if len(selected_characters_map) != len(character_ids):
        raise ValueError('有角色不存在，无法建局。')

    identities = BASE_WEREWOLF_TEMPLATE[:]
    random.shuffle(identities)
    seat_order = 1
    identity_index = 0

    for character_id in character_ids:
        character = selected_characters_map[character_id]
        WerewolfSeat.objects.create(
            game=game,
            character=character,
            source_type='character',
            seat_order=seat_order,
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
            identity=identities[identity_index],
        )
        seat_order += 1
        identity_index += 1

    for raw_custom_seat in custom_seats:
        custom_seat = _normalize_custom_seat(raw_custom_seat)
        WerewolfSeat.objects.create(
            game=game,
            source_type='custom',
            seat_order=seat_order,
            display_name=custom_seat['display_name'],
            profile=custom_seat['profile'],
            custom_prompt=custom_seat['custom_prompt'],
            reply_style=custom_seat['reply_style'],
            reply_length='balanced',
            initiative_level=custom_seat['initiative_level'],
            memory_mode='off',
            persona_boundary=custom_seat['persona_boundary'],
            identity=identities[identity_index],
        )
        seat_order += 1
        identity_index += 1

    _add_event(
        game,
        event_type='game_created',
        title='房间已创建',
        content='基础局已准备完成。你可以开始对局，系统主持人会自动推进夜晚、白天发言与投票。',
        payload={'seat_count': len(BASE_WEREWOLF_TEMPLATE)},
    )
    return game


def _run_night(game: WerewolfGame):
    if game.phase == 'setup':
        game.day_number = 1
    game.night_number += 1
    game.status = 'active'
    game.phase = 'night'

    wolf_target = _pick_wolf_target(game)
    seer, seer_target = _pick_seer_target(game)
    if wolf_target:
        wolf_target.is_alive = False
        wolf_target.save(update_fields=['is_alive'])
    _write_seer_check(game, seer, seer_target)
    game.state['last_night'] = {
        'wolf_target_id': wolf_target.id if wolf_target else None,
        'wolf_target_name': wolf_target.display_name if wolf_target else '',
        'seer_target_id': seer_target.id if seer_target else None,
        'seer_target_name': seer_target.display_name if seer_target else '',
        'seer_target_identity': seer_target.identity if seer_target else '',
    }
    game.save(update_fields=['status', 'phase', 'day_number', 'night_number', 'state', 'updated_at'])

    killed_text = f'{wolf_target.display_name} 在昨夜出局。' if wolf_target else '昨夜无人出局。'
    seer_text = (
        f'预言家查验了 {seer_target.display_name}，结果是 {get_identity_label(seer_target.identity)}。'
        if seer_target else
        '预言家昨夜没有获得新的查验对象。'
    )
    _add_event(
        game,
        event_type='night_result',
        title=f'第 {game.night_number} 夜结束',
        content=f'{killed_text}{seer_text}',
        payload=game.state['last_night'],
    )
    game.phase = 'day_speeches'
    game.save(update_fields=['phase', 'updated_at'])
    _add_event(
        game,
        event_type='day_started',
        title=f'第 {game.day_number} 天开始',
        content='系统主持人宣布进入白天讨论阶段，所有存活席位将按顺序发言。',
        payload={'alive_seat_ids': [seat.id for seat in _alive_seats(game)]},
    )


def _run_day_speeches(game: WerewolfGame):
    alive = _alive_seats(game)
    public_state = _public_alive_summary(game)
    for seat in alive:
        private_state = _private_state_for_seat(game, seat)
        content = generate_werewolf_role_reply(
            seat,
            public_state=public_state,
            private_state=private_state,
            stage_instruction='现在是白天讨论阶段。请基于公开信息和自己的身份视角，发表 2 到 4 句怀疑、辩解或引导投票的发言。',
        )
        WerewolfSpeech.objects.create(
            game=game,
            seat=seat,
            phase='day_speeches',
            day_number=game.day_number,
            night_number=game.night_number,
            audience='public',
            content=content,
        )

    game.phase = 'vote'
    game.save(update_fields=['phase', 'updated_at'])
    _add_event(
        game,
        event_type='day_speeches_completed',
        title='白天发言完成',
        content='所有存活席位已经完成公开发言，系统将进入投票阶段。',
        payload={'speech_count': len(alive)},
    )


def _pick_vote_target(game: WerewolfGame, seat: WerewolfSeat):
    alive = [candidate for candidate in _alive_seats(game) if candidate.id != seat.id]
    if not alive:
        return None

    if seat.identity == 'wolf':
        non_wolves = [candidate for candidate in alive if candidate.identity != 'wolf']
        if non_wolves:
            return non_wolves[0]

    if seat.identity == 'seer':
        checks = _seer_check_map(game)
        checked_wolf = next(
            (
                candidate for candidate in alive
                if checks.get(str(candidate.id), {}).get('identity') == 'wolf'
            ),
            None,
        )
        if checked_wolf:
            return checked_wolf

    return alive[0]


def _run_vote(game: WerewolfGame):
    alive = _alive_seats(game)
    votes = {}
    for seat in alive:
        target = _pick_vote_target(game, seat)
        if target:
            votes[str(seat.id)] = target.id

    counter = Counter(votes.values())
    eliminated = None
    if counter:
        top_vote_count = max(counter.values())
        top_target_ids = sorted([seat_id for seat_id, count in counter.items() if count == top_vote_count])
        eliminated = next((seat for seat in alive if seat.id == top_target_ids[0]), None)

    if eliminated:
        eliminated.is_alive = False
        eliminated.is_revealed = True
        eliminated.save(update_fields=['is_alive', 'is_revealed'])

    game.state['last_vote'] = {
        'votes': votes,
        'eliminated_seat_id': eliminated.id if eliminated else None,
        'eliminated_name': eliminated.display_name if eliminated else '',
        'eliminated_identity': eliminated.identity if eliminated else '',
    }

    winner = _determine_winner(game)
    if winner:
        game.status = 'finished'
        game.phase = 'finished'
        game.winner = winner
    else:
        game.phase = 'night'
    game.save(update_fields=['state', 'status', 'phase', 'winner', 'updated_at'])

    vote_lines = []
    alive_map = {seat.id: seat.display_name for seat in alive}
    for source_id, target_id in votes.items():
        vote_lines.append(f"{alive_map.get(int(source_id), '未知席位')} 投给了 {alive_map.get(target_id, '未知席位')}")

    result_text = (
        f'本轮出局：{eliminated.display_name}（{get_identity_label(eliminated.identity)}）。'
        if eliminated else
        '本轮无人出局。'
    )
    _add_event(
        game,
        event_type='vote_result',
        title='投票结果',
        content='；'.join(vote_lines + [result_text]),
        payload=game.state['last_vote'],
    )

    if winner:
        _add_event(
            game,
            event_type='game_finished',
            title='游戏结束',
            content='好人阵营获胜。' if winner == 'villagers' else '狼人阵营获胜。',
            payload={'winner': winner},
        )
    else:
        game.day_number += 1
        game.save(update_fields=['day_number', 'updated_at'])


@transaction.atomic
def advance_werewolf_game(game: WerewolfGame, observer_note: str = ''):
    if game.status == 'finished' or game.phase == 'finished':
        raise ValueError('当前房间已结束，不能继续推进。')

    if observer_note.strip():
        game.observer_note = observer_note.strip()[:1000]
        game.save(update_fields=['observer_note', 'updated_at'])
        _add_event(
            game,
            event_type='note',
            title='观察者备注',
            content=game.observer_note,
            payload={},
        )

    if game.phase in {'setup', 'night'}:
        _run_night(game)
    elif game.phase == 'day_speeches':
        _run_day_speeches(game)
    elif game.phase == 'vote':
        _run_vote(game)
    else:
        raise ValueError('当前阶段不支持推进。')

    game.refresh_from_db()
    return game


@transaction.atomic
def reset_werewolf_game(game: WerewolfGame):
    game.events.all().delete()
    game.speeches.all().delete()
    game.seats.update(is_alive=True, is_revealed=False)

    identities = BASE_WEREWOLF_TEMPLATE[:]
    random.shuffle(identities)
    for seat, identity in zip(game.seats.order_by('seat_order', 'id'), identities):
        seat.identity = identity
        seat.save(update_fields=['identity'])

    game.status = 'waiting'
    game.phase = 'setup'
    game.day_number = 0
    game.night_number = 0
    game.winner = ''
    game.observer_note = ''
    game.state = {}
    game.save(update_fields=['status', 'phase', 'day_number', 'night_number', 'winner', 'observer_note', 'state', 'updated_at'])

    _add_event(
        game,
        event_type='game_reset',
        title='房间已重置',
        content='身份已经重新分配，你可以重新开始这局基础狼人杀。',
        payload={'seat_count': game.seats.count()},
    )
    return game
