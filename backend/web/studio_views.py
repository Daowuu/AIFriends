from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from web.ai_settings_service import get_runtime_summary
from web.api_helpers import serialize_character_list, serialize_voice
from web.local_runtime import ensure_demo_voice_configs, get_or_create_local_operator_user
from web.models import Character, Friend, Voice


def _serialize_session_memory_summary(session: Friend):
    latest_message = session.messages.order_by('-created_at').first()
    return {
        'character_id': session.character_id,
        'has_messages': session.messages.exists(),
        'last_message_at': latest_message.created_at.isoformat() if latest_message else '',
        'memory_updated_at': session.memory_updated_at.isoformat() if session.memory_updated_at else '',
        'conversation_summary': session.conversation_summary.strip(),
        'relationship_memory': session.relationship_memory.strip(),
        'user_preference_memory': session.user_preference_memory.strip(),
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def studio_overview_view(request):
    local_user = get_or_create_local_operator_user()
    ensure_demo_voice_configs()
    characters = Character.objects.filter(user=local_user).select_related('voice').order_by('sort_order', 'id')
    voices = Voice.objects.filter(is_active=True).filter(
        Q(source='system') | Q(owner=local_user),
    ).order_by('source', 'name', 'id')
    session_memory_summaries = [
        _serialize_session_memory_summary(session)
        for session in Friend.objects.filter(user=local_user).select_related('character').order_by('-memory_updated_at', '-created_at', '-id')
    ]

    return Response({
        'characters': serialize_character_list(characters),
        'voices': [serialize_voice(voice) for voice in voices],
        'runtime_summary': get_runtime_summary(),
        'session_memory_summaries': session_memory_summaries,
    }, status=status.HTTP_200_OK)
