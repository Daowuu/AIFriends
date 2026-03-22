from web.models import Character, Friend, UserProfile, Voice


def get_user_profile(user):
    return UserProfile.objects.get_or_create(user=user)[0]


def file_url(file_field):
    if not file_field:
        return ''

    try:
        return file_field.url
    except ValueError:
        return ''


def serialize_user(user):
    profile = getattr(user, 'profile', None) or get_user_profile(user)
    return {
        'id': user.id,
        'username': user.username,
        'display_name': profile.display_name or user.username,
        'bio': profile.bio,
        'avatar': file_url(profile.avatar),
    }


def serialize_voice(voice: Voice, *, viewer=None):
    viewer_id = viewer.id if getattr(viewer, 'is_authenticated', False) else None
    return {
        'id': voice.id,
        'name': voice.name,
        'provider': voice.provider,
        'source': voice.source,
        'model_name': voice.model_name,
        'voice_code': voice.voice_code,
        'description': voice.description,
        'language': voice.language,
        'sample_audio': file_url(voice.sample_audio),
        'is_active': voice.is_active,
        'is_owner': viewer_id == voice.owner_id if viewer_id and voice.owner_id else False,
        'character_count': voice.characters.count() if getattr(voice, 'id', None) else 0,
    }


def serialize_character_ai_config(character: Character):
    return {
        'reply_style': character.reply_style,
        'reply_length': character.reply_length,
        'initiative_level': character.initiative_level,
        'memory_mode': character.memory_mode,
        'persona_boundary': character.persona_boundary,
        'tools_enabled': character.tools_enabled,
        'tools_require_confirmation': character.tools_require_confirmation,
        'tools_read_only': character.tools_read_only,
    }


def serialize_character(character: Character, *, viewer=None, friend_id=None):
    viewer_id = viewer.id if getattr(viewer, 'is_authenticated', False) else None

    return {
        'id': character.id,
        'name': character.name,
        'profile': character.profile,
        'custom_prompt': character.custom_prompt,
        'voice_id': character.voice_id,
        'voice': serialize_voice(character.voice, viewer=viewer) if character.voice else None,
        'photo': file_url(character.photo),
        'background_image': file_url(character.background_image),
        'created_at': character.created_at.isoformat(),
        'updated_at': character.updated_at.isoformat(),
        'author': serialize_user(character.user),
        'ai_config': serialize_character_ai_config(character),
        'is_owner': viewer_id == character.user_id if viewer_id else False,
        'friend_id': friend_id,
    }


def serialize_character_list(characters, *, viewer=None):
    character_list = list(characters)
    friend_map = {}

    if getattr(viewer, 'is_authenticated', False):
        friend_map = {
            friend.character_id: friend.id
            for friend in Friend.objects.filter(
                user=viewer,
                character_id__in=[character.id for character in character_list],
            )
        }

    return [
        serialize_character(character, viewer=viewer, friend_id=friend_map.get(character.id))
        for character in character_list
    ]


def serialize_friend(friend: Friend):
    return {
        'id': friend.id,
        'created_at': friend.created_at.isoformat(),
        'memory': {
            'conversation_summary': friend.conversation_summary,
            'relationship_memory': friend.relationship_memory,
            'user_preference_memory': friend.user_preference_memory,
            'memory_updated_at': friend.memory_updated_at.isoformat() if friend.memory_updated_at else '',
        },
        'character': serialize_character(friend.character, viewer=friend.user, friend_id=friend.id),
    }
