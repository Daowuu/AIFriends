import json
from pathlib import Path

from django.contrib.auth.models import User
from django.db import transaction

from web.models import Character, Friend, UserAISettings, Voice


LOCAL_OPERATOR_USERNAME = 'local_operator'
ELYSIA_DEMO_VOICE_CODE = 'cosyvoice-v3.5-plus-bailian-871b21d0985945ad9282d136a6e1a08e'
DEFAULT_CHARACTERS_PATH = Path(__file__).resolve().parent / 'fixtures' / 'default_characters.json'
MEDIA_ROOT = Path(__file__).resolve().parents[1] / 'media'


def get_or_create_local_operator_user():
    user, created = User.objects.get_or_create(
        username=LOCAL_OPERATOR_USERNAME,
        defaults={
            'is_active': True,
            'is_staff': True,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])
    return user


def get_local_ai_settings():
    return UserAISettings.objects.get_or_create(user=get_or_create_local_operator_user())[0]


def ensure_demo_voice_configs():
    local_user = get_or_create_local_operator_user()
    Voice.objects.update_or_create(
        owner=local_user,
        voice_code=ELYSIA_DEMO_VOICE_CODE,
        defaults={
            'name': '爱莉希雅',
            'provider': 'aliyun',
            'source': 'custom',
            'model_name': 'cosyvoice-v3.5-plus',
            'description': '内置示例音色。适合爱莉希雅风格角色草稿直接选用。',
            'language': 'zh-CN',
            'is_active': True,
        },
    )


def _load_default_characters():
    if not DEFAULT_CHARACTERS_PATH.exists():
        return []
    payload = json.loads(DEFAULT_CHARACTERS_PATH.read_text())
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def ensure_default_characters():
    local_user = get_or_create_local_operator_user()
    if Character.objects.filter(user=local_user).exists():
        return

    ensure_demo_voice_configs()
    visible_voices = {
        voice.voice_code: voice
        for voice in Voice.objects.filter(is_active=True, owner=local_user)
    }

    for item in _load_default_characters():
        name = str(item.get('name', '') or '').strip()
        if not name:
            continue
        photo_name = str(item.get('photo', '') or '').strip()
        background_name = str(item.get('background_image', '') or '').strip()
        photo_value = photo_name if photo_name and (MEDIA_ROOT / photo_name).exists() else None
        background_value = background_name if background_name and (MEDIA_ROOT / background_name).exists() else None
        Character.objects.update_or_create(
            user=local_user,
            name=name,
            defaults={
                'profile': str(item.get('profile', '') or '').replace('\r\n', '\n').strip(),
                'custom_prompt': str(item.get('custom_prompt', '') or '').replace('\r\n', '\n').strip(),
                'sort_order': int(item.get('sort_order', 0) or 0),
                'reply_style': str(item.get('reply_style', '') or 'natural'),
                'reply_length': str(item.get('reply_length', '') or 'balanced'),
                'initiative_level': str(item.get('initiative_level', '') or 'balanced'),
                'memory_mode': str(item.get('memory_mode', '') or 'standard'),
                'persona_boundary': str(item.get('persona_boundary', '') or 'companion'),
                'voice': visible_voices.get(str(item.get('voice_code', '') or '').strip()),
                'photo': photo_value,
                'background_image': background_value,
            },
        )


def get_local_characters_queryset():
    ensure_default_characters()
    return Character.objects.filter(user=get_or_create_local_operator_user())


def get_local_voices_queryset():
    ensure_demo_voice_configs()
    local_user = get_or_create_local_operator_user()
    return Voice.objects.filter(is_active=True).filter(owner__isnull=True) | Voice.objects.filter(
        is_active=True,
        owner=local_user,
    )


@transaction.atomic
def get_or_create_local_session(character: Character):
    local_user = get_or_create_local_operator_user()
    session, _ = Friend.objects.get_or_create(
        user=local_user,
        character=character,
    )
    return session
