from django.contrib.auth.models import User
from django.db import transaction

from web.models import Character, Friend, UserAISettings, Voice


LOCAL_OPERATOR_USERNAME = 'local_operator'
ELYSIA_DEMO_VOICE_CODE = 'cosyvoice-v3.5-flash-bailian-99058280e3994e48ad0c44453d58f8e0'


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
            'model_name': 'cosyvoice-v3.5-flash',
            'description': '内置示例音色。适合爱莉希雅风格角色草稿直接选用。',
            'language': 'zh-CN',
            'is_active': True,
        },
    )


def get_local_characters_queryset():
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
