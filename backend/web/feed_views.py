from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from web.api_helpers import serialize_character, serialize_character_list, serialize_user
from web.models import Character, Friend


def _parse_int(raw_value, default):
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


def _get_offset_limit(request):
    offset = max(0, _parse_int(request.query_params.get('offset'), 0))
    limit = _parse_int(request.query_params.get('limit'), 12)
    limit = min(max(limit, 1), 24)
    return offset, limit


def _apply_query(queryset, query):
    if not query:
        return queryset

    return queryset.filter(
        Q(name__icontains=query)
        | Q(profile__icontains=query)
        | Q(user__username__icontains=query)
        | Q(user__profile__display_name__icontains=query)
    )


def _build_paginated_response(queryset, request, extra_payload=None):
    query = request.query_params.get('q', '').strip()
    queryset = _apply_query(queryset, query)
    offset, limit = _get_offset_limit(request)
    window = list(queryset[offset:offset + limit + 1])
    has_more = len(window) > limit
    characters = window[:limit]

    payload = {
        'characters': serialize_character_list(characters, viewer=request.user),
        'offset': offset,
        'next_offset': offset + len(characters),
        'has_more': has_more,
        'q': query,
    }

    if extra_payload:
        payload.update(extra_payload)

    return Response(payload, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def homepage_index_view(request):
    queryset = Character.objects.select_related('user').all()
    return _build_paginated_response(queryset, request)


@api_view(['GET'])
@permission_classes([AllowAny])
def user_space_view(request, user_id):
    author = get_object_or_404(User.objects.select_related('profile'), pk=user_id)
    queryset = Character.objects.select_related('user').filter(user=author)
    return _build_paginated_response(
        queryset,
        request,
        extra_payload={'author': serialize_user(author)},
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def public_character_detail_view(request, character_id):
    character = get_object_or_404(
        Character.objects.select_related('user', 'user__profile', 'voice'),
        pk=character_id,
    )

    friend_id = None
    if getattr(request.user, 'is_authenticated', False):
        friend_id = Friend.objects.filter(
            user=request.user,
            character=character,
        ).values_list('id', flat=True).first()

    return Response(
        {'character': serialize_character(character, viewer=request.user, friend_id=friend_id)},
        status=status.HTTP_200_OK,
    )
