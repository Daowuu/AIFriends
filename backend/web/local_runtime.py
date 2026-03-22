from django.contrib.auth.models import User
from django.db import transaction

from web.models import Character, Friend, UserAISettings, Voice


LOCAL_OPERATOR_USERNAME = 'local_operator'


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


def get_local_characters_queryset():
    return Character.objects.filter(user=get_or_create_local_operator_user())


def get_local_voices_queryset():
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
