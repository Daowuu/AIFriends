from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from web.discussion_services import (
    advance_discussion_group,
    build_discussion_group_detail,
    create_discussion_group,
    list_discussion_groups,
    reset_discussion_group,
)
from web.models import WerewolfGame


def _parse_create_payload(data):
    title = str(data.get('title', '') or '').strip()
    topic = str(data.get('topic', '') or '').strip()
    max_rounds = data.get('max_rounds', 2)
    character_ids = data.get('character_ids', []) or []

    if not isinstance(character_ids, list):
        raise ValueError('character_ids 必须是数组。')

    normalized_character_ids = []
    for raw_value in character_ids:
        try:
            normalized_character_ids.append(int(raw_value))
        except (TypeError, ValueError) as error:
            raise ValueError('character_ids 中存在无效角色。') from error

    try:
        normalized_max_rounds = int(max_rounds)
    except (TypeError, ValueError) as error:
        raise ValueError('max_rounds 必须是整数。') from error

    return title, topic, normalized_character_ids, normalized_max_rounds


@api_view(['GET'])
@permission_classes([AllowAny])
def list_discussion_groups_view(request):
    return Response({'groups': list_discussion_groups()}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_discussion_group_view(request):
    try:
        title, topic, character_ids, max_rounds = _parse_create_payload(request.data)
        group = create_discussion_group(
            title=title,
            topic=topic,
            character_ids=character_ids,
            max_rounds=max_rounds,
        )
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(build_discussion_group_detail(group), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_discussion_group_view(request, group_id):
    group = get_object_or_404(WerewolfGame, pk=group_id)
    try:
        payload = build_discussion_group_detail(group)
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(payload, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def advance_discussion_group_view(request, group_id):
    group = get_object_or_404(WerewolfGame, pk=group_id)
    observer_note = str(request.data.get('observer_note', '') or '').strip()
    retry_failed_node_requested = bool(request.data.get('retry_failed_node'))
    try:
        group = advance_discussion_group(
            group,
            observer_note=observer_note,
            retry_failed_node_requested=retry_failed_node_requested,
        )
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
    payload = build_discussion_group_detail(group)
    if payload.get('runtime_status') == 'blocked':
        detail = payload.get('last_failure', {}).get('failure_reason') or '当前节点失败。'
        return Response({'detail': detail, **payload}, status=status.HTTP_400_BAD_REQUEST)
    return Response(payload, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_discussion_group_view(request, group_id):
    group = get_object_or_404(WerewolfGame, pk=group_id)
    try:
        group = reset_discussion_group(group)
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(build_discussion_group_detail(group), status=status.HTTP_200_OK)


@api_view(['POST', 'DELETE'])
@permission_classes([AllowAny])
def remove_discussion_group_view(request, group_id):
    group = get_object_or_404(WerewolfGame, pk=group_id)
    try:
        build_discussion_group_detail(group)
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
    group.delete()
    return Response({'detail': '讨论组已删除。'}, status=status.HTTP_200_OK)
