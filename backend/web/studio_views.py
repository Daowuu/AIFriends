from typing import Optional

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from web.ai_settings_service import get_runtime_summary
from web.api_helpers import serialize_character_list, serialize_voice
from web.local_runtime import get_or_create_local_operator_user
from web.models import Character, Friend, Voice


def _serialize_recent_debug_summary(session: Optional[Friend]):
    if not session:
        return None

    latest_message = session.messages.order_by('-created_at').first()
    character = session.character
    snapshot = session.last_debug_snapshot or {}
    memory_injection = snapshot.get('memory_injection') or {}
    memory_update = snapshot.get('memory_update') or {}
    return {
        'session_id': session.id,
        'character_id': character.id,
        'character_name': character.name,
        'memory_mode': character.memory_mode,
        'voice_name': character.voice.name if character.voice else '',
        'last_message_at': latest_message.created_at.isoformat() if latest_message else '',
        'memory_updated_at': session.memory_updated_at.isoformat() if session.memory_updated_at else '',
        'last_debug_at': session.last_debug_at.isoformat() if session.last_debug_at else '',
        'has_summary': bool(session.conversation_summary.strip()),
        'has_preference_memory': bool(session.user_preference_memory.strip()),
        'prompt_layers': snapshot.get('prompt_layers', []),
        'runtime_source': snapshot.get('runtime_source', ''),
        'fallback_used': bool(snapshot.get('fallback_used', False)),
        'error_tag': snapshot.get('error_tag', ''),
        'memory_update_reason': memory_update.get('reason', ''),
        'memory_update_triggered': bool(memory_update.get('triggered', False)),
        'used_summary': bool(memory_injection.get('used_summary', False)),
        'used_relationship_memory': bool(memory_injection.get('used_relationship_memory', False)),
        'used_user_preference_memory': bool(memory_injection.get('used_user_preference_memory', False)),
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def studio_overview_view(request):
    local_user = get_or_create_local_operator_user()
    characters = Character.objects.filter(user=local_user).select_related('voice')
    voices = Voice.objects.filter(is_active=True).filter(
        Q(source='system') | Q(owner=local_user),
    ).order_by('source', 'name', 'id')
    recent_session = Friend.objects.filter(user=local_user).select_related(
        'character',
        'character__voice',
    ).order_by('-last_debug_at', '-memory_updated_at', '-created_at', '-id').first()

    return Response({
        'characters': serialize_character_list(characters),
        'voices': [serialize_voice(voice) for voice in voices],
        'runtime_summary': get_runtime_summary(),
        'recent_debug_summary': _serialize_recent_debug_summary(recent_session),
    }, status=status.HTTP_200_OK)
