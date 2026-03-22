from web.models import Character, Voice


def file_url(file_field):
    if not file_field:
        return ''

    try:
        return file_field.url
    except ValueError:
        return ''


def serialize_voice(voice: Voice):
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


def serialize_character(character: Character):
    return {
        'id': character.id,
        'name': character.name,
        'profile': character.profile,
        'custom_prompt': character.custom_prompt,
        'voice_id': character.voice_id,
        'voice': serialize_voice(character.voice) if character.voice else None,
        'photo': file_url(character.photo),
        'background_image': file_url(character.background_image),
        'created_at': character.created_at.isoformat(),
        'updated_at': character.updated_at.isoformat(),
        'ai_config': serialize_character_ai_config(character),
    }


def serialize_character_list(characters):
    return [serialize_character(character) for character in list(characters)]
