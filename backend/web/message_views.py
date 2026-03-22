from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response

from web.chat_services import sse_event_stream, strip_reasoning_content
from web.ai_settings_service import get_runtime_ai_resolution
from web.local_runtime import get_or_create_local_session
from web.models import Character, Message
from web.system_api_quota_service import build_quota_exceeded_response, consume_system_api_quota


class SSERenderer(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'txt'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


def serialize_message(message: Message):
    return {
        'id': message.id,
        'role': message.role,
        'content': strip_reasoning_content(message.content),
        'created_at': message.created_at.isoformat(),
    }


def _resolve_character(character_id: int):
    return get_object_or_404(Character.objects.select_related('voice'), pk=character_id)


@api_view(['GET'])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def get_history_view(request):
    try:
        character_id = int(request.query_params.get('character_id', 0) or 0)
        offset = max(int(request.query_params.get('offset', 0) or 0), 0)
        limit = min(max(int(request.query_params.get('limit', 20) or 20), 1), 50)
    except (TypeError, ValueError):
        return Response({'detail': '请求参数格式不正确。'}, status=status.HTTP_400_BAD_REQUEST)

    if character_id <= 0:
        return Response({'detail': '缺少有效的 character_id。'}, status=status.HTTP_400_BAD_REQUEST)

    session = get_or_create_local_session(_resolve_character(character_id))
    window = list(Message.objects.filter(friend=session).order_by('-id')[offset:offset + limit + 1])
    has_more = len(window) > limit
    messages = list(reversed(window[:limit]))

    return Response({
        'messages': [serialize_message(message) for message in messages],
        'offset': offset,
        'next_offset': offset + len(messages),
        'has_more': has_more,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
@renderer_classes([SSERenderer])
def message_chat_view(request):
    try:
        character_id = int(request.data.get('character_id', 0) or 0)
    except (TypeError, ValueError):
        return Response({'detail': 'character_id 格式不正确。'}, status=status.HTTP_400_BAD_REQUEST)

    user_message = str(request.data.get('message', '')).strip()
    if character_id <= 0:
        return Response({'detail': '缺少有效的 character_id。'}, status=status.HTTP_400_BAD_REQUEST)
    if not user_message:
        return Response({'detail': '消息内容不能为空。'}, status=status.HTTP_400_BAD_REQUEST)

    session = get_or_create_local_session(_resolve_character(character_id))

    runtime_resolution = get_runtime_ai_resolution()
    runtime_config = runtime_resolution.get('config') or {}
    if runtime_config.get('source') == 'env':
        if not consume_system_api_quota(request, quota_type='text'):
            return build_quota_exceeded_response(quota_type='text')

    response = StreamingHttpResponse(
        sse_event_stream(session, user_message[:4000]),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def reset_conversation_view(request):
    try:
        character_id = int(request.data.get('character_id', 0) or 0)
    except (TypeError, ValueError):
        return Response({'detail': 'character_id 格式不正确。'}, status=status.HTTP_400_BAD_REQUEST)

    mode = str(request.data.get('mode', 'history') or 'history').strip().lower()
    if mode not in {'history', 'full'}:
        return Response({'detail': 'mode 只能是 history 或 full。'}, status=status.HTTP_400_BAD_REQUEST)
    if character_id <= 0:
        return Response({'detail': '缺少有效的 character_id。'}, status=status.HTTP_400_BAD_REQUEST)

    session = get_or_create_local_session(_resolve_character(character_id))
    deleted_count, _ = Message.objects.filter(friend=session).delete()

    if mode == 'full':
        session.conversation_summary = ''
        session.relationship_memory = ''
        session.user_preference_memory = ''
        session.memory_updated_at = None
        session.memory_refresh_attempted_at = None
        session.last_debug_snapshot = {}
        session.last_debug_at = None
        session.save(update_fields=[
            'conversation_summary',
            'relationship_memory',
            'user_preference_memory',
            'memory_updated_at',
            'memory_refresh_attempted_at',
            'last_debug_snapshot',
            'last_debug_at',
        ])

    return Response({
        'detail': '已重置聊天窗口。' if mode == 'history' else '已清空这段会话的长期记忆。',
        'mode': mode,
        'deleted_message_count': deleted_count,
    }, status=status.HTTP_200_OK)
