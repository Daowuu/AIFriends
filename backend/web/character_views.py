from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from web.api_helpers import serialize_character, serialize_character_list, serialize_voice
from web.media_utils import remove_stored_file, replace_stored_file
from web.models import Character, Voice


def _get_owned_character(user, character_id):
    return get_object_or_404(Character.objects.select_related('voice', 'user', 'user__profile'), pk=character_id, user=user)


def _normalize_name(raw_name):
    return str(raw_name or '').strip()


def _get_available_voices(user):
    return Voice.objects.filter(
        is_active=True,
    ).filter(
        Q(source='system') | Q(owner=user),
    ).order_by('source', 'name', 'id')


def _get_owned_custom_voice(user, voice_id):
    return get_object_or_404(
        Voice.objects.filter(owner=user, source='custom'),
        pk=voice_id,
    )


def _resolve_voice(user, raw_voice_id):
    value = str(raw_voice_id or '').strip()
    if not value:
        return None

    try:
        voice_id = int(value)
    except (TypeError, ValueError):
        raise ValueError('音色参数格式不正确。')

    return get_object_or_404(_get_available_voices(user), pk=voice_id)


def _resolve_custom_voice(user, payload):
    custom_voice_code = str(payload.get('custom_voice_code', '') or '').strip()
    if not custom_voice_code:
        return None

    custom_voice_name = str(payload.get('custom_voice_name', '') or '').strip() or '自定义音色'
    custom_voice_model_name = str(payload.get('custom_voice_model_name', '') or '').strip() or 'cosyvoice-v3.5-plus'
    custom_voice_description = str(payload.get('custom_voice_description', '') or '').strip()

    voice, _ = Voice.objects.update_or_create(
        owner=user,
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_character_voices_view(request):
    voices = _get_available_voices(request.user)
    return Response({
        'voices': [serialize_voice(voice, viewer=request.user) for voice in voices],
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
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

        voice = _get_owned_custom_voice(request.user, voice_id)
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
            owner=request.user,
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
        'voice': serialize_voice(voice, viewer=request.user),
        'detail': '自定义音色已保存。',
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_character_voice_view(request, voice_id):
    voice = _get_owned_custom_voice(request.user, voice_id)
    Character.objects.filter(user=request.user, voice=voice).update(voice=None)
    voice.delete()
    return Response({'detail': '自定义音色已删除。'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_characters_view(request):
    characters = Character.objects.filter(user=request.user).select_related('voice', 'user', 'user__profile')
    return Response(
        {'characters': serialize_character_list(characters, viewer=request.user)},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_character_view(request):
    name = _normalize_name(request.data.get('name', ''))
    profile = str(request.data.get('profile', '') or '').strip()
    photo = request.FILES.get('photo')
    background_image = request.FILES.get('background_image')

    if not name:
        return Response({'detail': '角色名不能为空。'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        voice = _resolve_custom_voice(request.user, request.data) or _resolve_voice(request.user, request.data.get('voice_id', ''))
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    character = Character.objects.create(
        user=request.user,
        name=name,
        profile=profile,
        voice=voice,
        photo=photo,
        background_image=background_image,
    )

    return Response({'character': serialize_character(character, viewer=request.user)}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_single_character_view(request, character_id):
    character = _get_owned_character(request.user, character_id)
    return Response({'character': serialize_character(character, viewer=request.user)}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_character_view(request, character_id):
    character = _get_owned_character(request.user, character_id)

    name = _normalize_name(request.data.get('name', character.name))
    profile = str(request.data.get('profile', character.profile) or '').strip()
    photo = request.FILES.get('photo')
    background_image = request.FILES.get('background_image')
    remove_photo = request.data.get('remove_photo') in {'1', 'true', 'True'}
    remove_background_image = request.data.get('remove_background_image') in {'1', 'true', 'True'}

    if not name:
        return Response({'detail': '角色名不能为空。'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        voice = _resolve_custom_voice(request.user, request.data) or _resolve_voice(request.user, request.data.get('voice_id', character.voice_id or ''))
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    character.name = name
    character.profile = profile
    character.voice = voice

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

    return Response({'character': serialize_character(character, viewer=request.user)}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_character_view(request, character_id):
    character = _get_owned_character(request.user, character_id)
    remove_stored_file(character.photo)
    remove_stored_file(character.background_image)
    character.delete()
    return Response({'detail': '角色已删除。'}, status=status.HTTP_200_OK)
