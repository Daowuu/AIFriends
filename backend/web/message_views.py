from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response

from web.chat_services import sse_event_stream, strip_reasoning_content
from web.models import Friend, Message


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@renderer_classes([JSONRenderer])
def get_history_view(request):
    try:
        friend_id = int(request.query_params.get('friend_id', 0) or 0)
        offset = max(int(request.query_params.get('offset', 0) or 0), 0)
        limit = min(max(int(request.query_params.get('limit', 20) or 20), 1), 50)
    except (TypeError, ValueError):
        return Response({'detail': '请求参数格式不正确。'}, status=status.HTTP_400_BAD_REQUEST)

    if friend_id <= 0:
        return Response({'detail': '缺少有效的 friend_id。'}, status=status.HTTP_400_BAD_REQUEST)

    friend = get_object_or_404(
        Friend.objects.select_related('character', 'character__user'),
        pk=friend_id,
        user=request.user,
    )

    window = list(Message.objects.filter(friend=friend).order_by('-id')[offset:offset + limit + 1])
    has_more = len(window) > limit
    messages = list(reversed(window[:limit]))

    return Response({
        'messages': [serialize_message(message) for message in messages],
        'offset': offset,
        'next_offset': offset + len(messages),
        'has_more': has_more,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@renderer_classes([SSERenderer])
def message_chat_view(request):
    try:
        friend_id = int(request.data.get('friend_id', 0) or 0)
    except (TypeError, ValueError):
        return Response({'detail': 'friend_id 格式不正确。'}, status=status.HTTP_400_BAD_REQUEST)

    user_message = str(request.data.get('message', '')).strip()

    if friend_id <= 0:
        return Response({'detail': '缺少有效的 friend_id。'}, status=status.HTTP_400_BAD_REQUEST)

    if not user_message:
        return Response({'detail': '消息内容不能为空。'}, status=status.HTTP_400_BAD_REQUEST)

    friend = get_object_or_404(
        Friend.objects.select_related(
            'character',
            'character__user',
            'character__user__profile',
        ),
        pk=friend_id,
        user=request.user,
    )

    response = StreamingHttpResponse(
        sse_event_stream(friend, user_message[:4000]),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    return response
