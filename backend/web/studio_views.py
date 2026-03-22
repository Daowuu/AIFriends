from typing import Optional

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from web.ai_settings_service import get_runtime_summary
from web.api_helpers import serialize_character_list, serialize_voice
from web.models import Character, Friend, Voice


def _serialize_recent_debug_summary(friend: Optional[Friend]):
    if not friend:
        return None

    latest_message = friend.messages.order_by('-created_at').first()
    character = friend.character
    snapshot = friend.last_debug_snapshot or {}
    memory_injection = snapshot.get('memory_injection') or {}
    memory_update = snapshot.get('memory_update') or {}
    return {
        'friend_id': friend.id,
        'character_id': character.id,
        'character_name': character.name,
        'memory_mode': character.memory_mode,
        'voice_name': character.voice.name if character.voice else '',
        'last_message_at': latest_message.created_at.isoformat() if latest_message else '',
        'memory_updated_at': friend.memory_updated_at.isoformat() if friend.memory_updated_at else '',
        'last_debug_at': friend.last_debug_at.isoformat() if friend.last_debug_at else '',
        'has_summary': bool(friend.conversation_summary.strip()),
        'has_preference_memory': bool(friend.user_preference_memory.strip()),
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
@permission_classes([IsAuthenticated])
def studio_overview_view(request):
    characters = Character.objects.filter(user=request.user).select_related('voice', 'user', 'user__profile')
    voices = Voice.objects.filter(is_active=True).filter(
        Q(source='system') | Q(owner=request.user),
    ).select_related('owner').order_by('source', 'name', 'id')

    recent_friend = Friend.objects.filter(user=request.user).select_related(
        'character',
        'character__voice',
    ).order_by('-last_debug_at', '-memory_updated_at', '-created_at', '-id').first()

    return Response({
        'characters': serialize_character_list(characters, viewer=request.user),
        'voices': [serialize_voice(voice, viewer=request.user) for voice in voices],
        'runtime_summary': get_runtime_summary(request.user),
        'recent_debug_summary': _serialize_recent_debug_summary(recent_friend),
    }, status=status.HTTP_200_OK)
