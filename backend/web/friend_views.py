from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from web.api_helpers import serialize_friend
from web.models import Character, Friend


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_or_create_friend_view(request):
    character_id = request.data.get('character_id')
    character = get_object_or_404(Character.objects.select_related('user'), pk=character_id)

    friend, created = Friend.objects.get_or_create(user=request.user, character=character)
    return Response(
        {'friend': serialize_friend(friend), 'created': created},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_friend_view(request):
    friend_id = request.data.get('friend_id')
    friend = get_object_or_404(
        Friend.objects.select_related('character', 'character__user'),
        pk=friend_id,
        user=request.user,
    )
    payload = serialize_friend(friend)
    friend.delete()
    return Response({'friend': payload, 'detail': '好友已删除。'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_friend_list_view(request):
    friends = Friend.objects.select_related('character', 'character__user').filter(user=request.user)
    return Response(
        {'friends': [serialize_friend(friend) for friend in friends]},
        status=status.HTTP_200_OK,
    )
