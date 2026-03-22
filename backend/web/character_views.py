from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from web.api_helpers import serialize_character, serialize_character_list, serialize_voice
from web.local_runtime import ensure_demo_voice_configs, get_or_create_local_operator_user
from web.media_utils import remove_stored_file, replace_stored_file
from web.models import Character, Voice


def _get_owned_character(character_id):
    return get_object_or_404(
        Character.objects.select_related('voice', 'user'),
        pk=character_id,
        user=get_or_create_local_operator_user(),
    )


def _normalize_name(raw_name):
    return str(raw_name or '').strip()


def _normalize_bool(value, *, default=False):
    if value is None or value == '':
        return default
    return str(value).lower() in {'1', 'true', 'yes', 'on'}


def _valid_choice(value, choices, default):
    normalized = str(value or '').strip()
    valid_values = {choice[0] for choice in choices}
    return normalized if normalized in valid_values else default


def _get_available_voices():
    ensure_demo_voice_configs()
    local_user = get_or_create_local_operator_user()
    return Voice.objects.filter(is_active=True).filter(
        Q(source='system') | Q(owner=local_user),
    ).order_by('source', 'name', 'id')


def _get_owned_custom_voice(voice_id):
    return get_object_or_404(
        Voice.objects.filter(owner=get_or_create_local_operator_user(), source='custom'),
        pk=voice_id,
    )


def _resolve_voice(raw_voice_id):
    value = str(raw_voice_id or '').strip()
    if not value:
        return None

    try:
        voice_id = int(value)
    except (TypeError, ValueError):
        raise ValueError('音色参数格式不正确。')

    return get_object_or_404(_get_available_voices(), pk=voice_id)


def _resolve_custom_voice(payload):
    custom_voice_code = str(payload.get('custom_voice_code', '') or '').strip()
    if not custom_voice_code:
        return None

    custom_voice_name = str(payload.get('custom_voice_name', '') or '').strip() or '自定义音色'
    custom_voice_model_name = str(payload.get('custom_voice_model_name', '') or '').strip() or 'cosyvoice-v3.5-plus'
    custom_voice_description = str(payload.get('custom_voice_description', '') or '').strip()

    voice, _ = Voice.objects.update_or_create(
        owner=get_or_create_local_operator_user(),
        voice_code=custom_voice_code,
        defaults={
            'name': custom_voice_name,
            'provider': 'aliyun',
            'source': 'custom',
            'model_name': custom_voice_model_name,
            'description': custom_voice_description,
            'language': 'zh-CN',
            'is_active': True,
        },
    )
    return voice


def _normalize_custom_voice_payload(payload):
    custom_voice_code = str(payload.get('custom_voice_code', '') or '').strip()
    if not custom_voice_code:
        raise ValueError('音色 ID 不能为空。')

    return {
        'name': str(payload.get('custom_voice_name', '') or '').strip() or '自定义音色',
        'voice_code': custom_voice_code,
        'model_name': str(payload.get('custom_voice_model_name', '') or '').strip() or 'cosyvoice-v3.5-plus',
        'description': str(payload.get('custom_voice_description', '') or '').strip(),
    }


def _resolve_character_ai_config(payload, *, character=None):
    reference = character or Character()
    return {
        'reply_style': _valid_choice(
            payload.get('reply_style', getattr(reference, 'reply_style', 'natural')),
            Character.REPLY_STYLE_CHOICES,
            'natural',
        ),
        'reply_length': _valid_choice(
            payload.get('reply_length', getattr(reference, 'reply_length', 'balanced')),
            Character.REPLY_LENGTH_CHOICES,
            'balanced',
        ),
        'initiative_level': _valid_choice(
            payload.get('initiative_level', getattr(reference, 'initiative_level', 'balanced')),
            Character.INITIATIVE_LEVEL_CHOICES,
            'balanced',
        ),
        'memory_mode': _valid_choice(
            payload.get('memory_mode', getattr(reference, 'memory_mode', 'standard')),
            Character.MEMORY_MODE_CHOICES,
            'standard',
        ),
        'persona_boundary': _valid_choice(
            payload.get('persona_boundary', getattr(reference, 'persona_boundary', 'companion')),
            Character.PERSONA_BOUNDARY_CHOICES,
            'companion',
        ),
        'tools_enabled': _normalize_bool(
            payload.get('tools_enabled'),
            default=getattr(reference, 'tools_enabled', False),
        ),
        'tools_require_confirmation': _normalize_bool(
            payload.get('tools_require_confirmation'),
            default=getattr(reference, 'tools_require_confirmation', True),
        ),
        'tools_read_only': _normalize_bool(
            payload.get('tools_read_only'),
            default=getattr(reference, 'tools_read_only', True),
        ),
    }


def _get_next_sort_order():
    latest = Character.objects.filter(user=get_or_create_local_operator_user()).order_by('-sort_order', '-id').first()
    return (latest.sort_order + 1) if latest else 0


@api_view(['GET'])
@permission_classes([AllowAny])
def list_character_voices_view(request):
    voices = _get_available_voices()
    return Response({
        'voices': [serialize_voice(voice) for voice in voices],
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def save_character_voice_view(request):
    raw_voice_id = str(request.data.get('voice_id', '') or '').strip()

    try:
        payload = _normalize_custom_voice_payload(request.data)
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    if raw_voice_id:
        try:
            voice_id = int(raw_voice_id)
        except (TypeError, ValueError):
            return Response({'detail': '音色参数格式不正确。'}, status=status.HTTP_400_BAD_REQUEST)

        voice = _get_owned_custom_voice(voice_id)
        conflict = Voice.objects.filter(voice_code=payload['voice_code']).exclude(pk=voice.pk).first()
        if conflict:
            return Response({'detail': '这个音色 ID 已存在，不能重复保存。'}, status=status.HTTP_400_BAD_REQUEST)

        voice.name = payload['name']
        voice.voice_code = payload['voice_code']
        voice.model_name = payload['model_name']
        voice.description = payload['description']
        voice.is_active = True
        voice.save()
    else:
        voice, _ = Voice.objects.update_or_create(
            owner=get_or_create_local_operator_user(),
            voice_code=payload['voice_code'],
            defaults={
                'name': payload['name'],
                'provider': 'aliyun',
                'source': 'custom',
                'model_name': payload['model_name'],
                'description': payload['description'],
                'language': 'zh-CN',
                'is_active': True,
            },
        )

    return Response({
        'voice': serialize_voice(voice),
        'detail': '自定义音色已保存。',
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def remove_character_voice_view(request, voice_id):
    voice = _get_owned_custom_voice(voice_id)
    Character.objects.filter(user=get_or_create_local_operator_user(), voice=voice).update(voice=None)
    voice.delete()
    return Response({'detail': '自定义音色已删除。'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_characters_view(request):
    characters = Character.objects.filter(user=get_or_create_local_operator_user()).select_related('voice').order_by('sort_order', 'id')
    return Response(
        {'characters': serialize_character_list(characters)},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_character_view(request):
    name = _normalize_name(request.data.get('name', ''))
    profile = str(request.data.get('profile', '') or '').strip()
    custom_prompt = str(request.data.get('custom_prompt', '') or '').strip()
    photo = request.FILES.get('photo')
    background_image = request.FILES.get('background_image')

    if not name:
        return Response({'detail': '角色名不能为空。'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        voice = _resolve_custom_voice(request.data) or _resolve_voice(request.data.get('voice_id', ''))
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    ai_config = _resolve_character_ai_config(request.data)

    character = Character.objects.create(
        user=get_or_create_local_operator_user(),
        name=name,
        profile=profile,
        custom_prompt=custom_prompt,
        voice=voice,
        photo=photo,
        background_image=background_image,
        sort_order=_get_next_sort_order(),
        **ai_config,
    )

    return Response({'character': serialize_character(character)}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_single_character_view(request, character_id):
    character = _get_owned_character(character_id)
    return Response({'character': serialize_character(character)}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_character_view(request, character_id):
    character = _get_owned_character(character_id)

    name = _normalize_name(request.data.get('name', character.name))
    profile = str(request.data.get('profile', character.profile) or '').strip()
    custom_prompt = str(request.data.get('custom_prompt', character.custom_prompt) or '').strip()
    photo = request.FILES.get('photo')
    background_image = request.FILES.get('background_image')
    remove_photo = request.data.get('remove_photo') in {'1', 'true', 'True'}
    remove_background_image = request.data.get('remove_background_image') in {'1', 'true', 'True'}

    if not name:
        return Response({'detail': '角色名不能为空。'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        voice = _resolve_custom_voice(request.data) or _resolve_voice(request.data.get('voice_id', character.voice_id or ''))
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    ai_config = _resolve_character_ai_config(request.data, character=character)

    character.name = name
    character.profile = profile
    character.custom_prompt = custom_prompt
    character.voice = voice
    character.reply_style = ai_config['reply_style']
    character.reply_length = ai_config['reply_length']
    character.initiative_level = ai_config['initiative_level']
    character.memory_mode = ai_config['memory_mode']
    character.persona_boundary = ai_config['persona_boundary']
    character.tools_enabled = ai_config['tools_enabled']
    character.tools_require_confirmation = ai_config['tools_require_confirmation']
    character.tools_read_only = ai_config['tools_read_only']

    if photo:
        replace_stored_file(character, 'photo', photo)
    elif remove_photo:
        remove_stored_file(character.photo)
        character.photo = None

    if background_image:
        replace_stored_file(character, 'background_image', background_image)
    elif remove_background_image:
        remove_stored_file(character.background_image)
        character.background_image = None

    character.save()

    return Response({'character': serialize_character(character)}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def remove_character_view(request, character_id):
    character = _get_owned_character(character_id)
    remove_stored_file(character.photo)
    remove_stored_file(character.background_image)
    character.delete()
    return Response({'detail': '角色已删除。'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def reorder_characters_view(request):
    raw_ids = request.data.get('character_ids')
    if not isinstance(raw_ids, list) or not raw_ids:
        return Response({'detail': '角色排序参数不能为空。'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        character_ids = [int(character_id) for character_id in raw_ids]
    except (TypeError, ValueError):
        return Response({'detail': '角色排序参数格式不正确。'}, status=status.HTTP_400_BAD_REQUEST)

    if len(character_ids) != len(set(character_ids)):
        return Response({'detail': '角色排序参数存在重复项。'}, status=status.HTTP_400_BAD_REQUEST)

    local_user = get_or_create_local_operator_user()
    characters = list(Character.objects.filter(user=local_user, id__in=character_ids).order_by('sort_order', 'id'))
    if len(characters) != len(character_ids):
        return Response({'detail': '角色排序参数不完整，无法保存顺序。'}, status=status.HTTP_400_BAD_REQUEST)

    character_map = {character.id: character for character in characters}
    for index, character_id in enumerate(character_ids):
        character = character_map[character_id]
        if character.sort_order != index:
            character.sort_order = index
            character.save(update_fields=['sort_order'])

    ordered_characters = Character.objects.filter(user=local_user).select_related('voice').order_by('sort_order', 'id')
    return Response({
        'characters': serialize_character_list(ordered_characters),
        'detail': '角色顺序已更新。',
    }, status=status.HTTP_200_OK)
