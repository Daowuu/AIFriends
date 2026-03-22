from django.db import migrations


LOCAL_OPERATOR_USERNAME = 'local_operator'


def _pick_text(*values):
    for value in values:
        if str(value or '').strip():
            return value
    return ''


def forwards(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Character = apps.get_model('web', 'Character')
    Friend = apps.get_model('web', 'Friend')
    Message = apps.get_model('web', 'Message')
    Voice = apps.get_model('web', 'Voice')
    UserAISettings = apps.get_model('web', 'UserAISettings')

    local_user, created = User.objects.get_or_create(
        username=LOCAL_OPERATOR_USERNAME,
        defaults={
            'is_active': True,
            'is_staff': True,
        },
    )
    if created:
        # Historical migration models do not include auth helper methods.
        local_user.password = '!'
        local_user.save(update_fields=['password'])

    Character.objects.exclude(user_id=local_user.id).update(user_id=local_user.id)
    Voice.objects.exclude(owner_id=local_user.id).filter(owner_id__isnull=False).update(owner_id=local_user.id)

    for character_id in Character.objects.values_list('id', flat=True):
        sessions = list(Friend.objects.filter(character_id=character_id).order_by('created_at', 'id'))
        if not sessions:
            continue

        primary = next((session for session in sessions if session.user_id == local_user.id), sessions[0])
        if primary.user_id != local_user.id:
            primary.user_id = local_user.id
            primary.save(update_fields=['user'])

        for session in sessions:
            if session.id == primary.id:
                continue

            Message.objects.filter(friend_id=session.id).update(friend_id=primary.id)
            primary.conversation_summary = _pick_text(primary.conversation_summary, session.conversation_summary)
            primary.relationship_memory = _pick_text(primary.relationship_memory, session.relationship_memory)
            primary.user_preference_memory = _pick_text(primary.user_preference_memory, session.user_preference_memory)
            primary.memory_updated_at = primary.memory_updated_at or session.memory_updated_at
            primary.memory_refresh_attempted_at = primary.memory_refresh_attempted_at or session.memory_refresh_attempted_at
            if not primary.last_debug_snapshot and session.last_debug_snapshot:
                primary.last_debug_snapshot = session.last_debug_snapshot
            primary.last_debug_at = primary.last_debug_at or session.last_debug_at
            session.delete()

        primary.save(update_fields=[
            'conversation_summary',
            'relationship_memory',
            'user_preference_memory',
            'memory_updated_at',
            'memory_refresh_attempted_at',
            'last_debug_snapshot',
            'last_debug_at',
        ])

    settings_list = list(UserAISettings.objects.all().order_by('-enabled', '-updated_at', 'id'))
    primary_settings = next((item for item in settings_list if item.user_id == local_user.id), None)
    if primary_settings is None and settings_list:
        source = settings_list[0]
        primary_settings = UserAISettings.objects.create(
            user_id=local_user.id,
            enabled=source.enabled,
            provider=source.provider,
            api_key=source.api_key,
            api_base=source.api_base,
            model_name=source.model_name,
            chat_supports_dashscope_audio=source.chat_supports_dashscope_audio,
            asr_enabled=source.asr_enabled,
            asr_api_key=source.asr_api_key,
            asr_api_base=source.asr_api_base,
            asr_model_name=source.asr_model_name,
        )
    elif primary_settings is None:
        primary_settings = UserAISettings.objects.create(user_id=local_user.id)

    for settings in settings_list:
        if settings.id == primary_settings.id:
            continue
        if not primary_settings.api_key and settings.api_key:
            primary_settings.api_key = settings.api_key
        if not primary_settings.api_base and settings.api_base:
            primary_settings.api_base = settings.api_base
        if not primary_settings.model_name and settings.model_name:
            primary_settings.model_name = settings.model_name
        if not primary_settings.asr_api_key and settings.asr_api_key:
            primary_settings.asr_api_key = settings.asr_api_key
        if not primary_settings.asr_api_base and settings.asr_api_base:
            primary_settings.asr_api_base = settings.asr_api_base
        if not primary_settings.asr_model_name and settings.asr_model_name:
            primary_settings.asr_model_name = settings.asr_model_name
        primary_settings.enabled = primary_settings.enabled or settings.enabled
        primary_settings.chat_supports_dashscope_audio = (
            primary_settings.chat_supports_dashscope_audio or settings.chat_supports_dashscope_audio
        )
        primary_settings.asr_enabled = primary_settings.asr_enabled or settings.asr_enabled
        settings.delete()

    primary_settings.user_id = local_user.id
    primary_settings.save()


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0012_friend_debug_fields'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
