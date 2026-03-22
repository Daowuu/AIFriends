from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from web.models import WerewolfGame
from web.werewolf_services import (
    advance_werewolf_game,
    build_werewolf_game_detail,
    create_werewolf_game,
    list_werewolf_games,
    reset_werewolf_game,
)


def _parse_create_payload(data):
    title = str(data.get('title', '') or '').strip()
    character_ids = data.get('character_ids', []) or []
    custom_seats = data.get('custom_seats', []) or []

    if not isinstance(character_ids, list):
        raise ValueError('character_ids 必须是数组。')
    if not isinstance(custom_seats, list):
        raise ValueError('custom_seats 必须是数组。')

    normalized_character_ids = []
    for raw_value in character_ids:
        try:
            normalized_character_ids.append(int(raw_value))
        except (TypeError, ValueError):
            raise ValueError('character_ids 中存在无效角色。')

    normalized_custom_seats = []
    for item in custom_seats:
        if not isinstance(item, dict):
            raise ValueError('custom_seats 中存在无效席位。')

        normalized_custom_seats.append({
            'display_name': str(item.get('display_name', '') or '').strip(),
            'profile': str(item.get('profile', '') or '').strip(),
            'custom_prompt': str(item.get('custom_prompt', '') or '').strip(),
            'voice_id': item.get('voice_id') or None,
            'reply_style': str(item.get('reply_style', '') or '').strip(),
            'reply_length': str(item.get('reply_length', '') or '').strip(),
            'initiative_level': str(item.get('initiative_level', '') or '').strip(),
            'memory_mode': str(item.get('memory_mode', '') or '').strip(),
            'persona_boundary': str(item.get('persona_boundary', '') or '').strip(),
        })

    return title, normalized_character_ids, normalized_custom_seats


@api_view(['GET'])
@permission_classes([AllowAny])
def list_werewolf_games_view(request):
    return Response({'games': list_werewolf_games()}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_werewolf_game_view(request):
    try:
        title, character_ids, custom_seats = _parse_create_payload(request.data)
        game = create_werewolf_game(
            title=title,
            character_ids=character_ids,
            custom_seats=custom_seats,
        )
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(build_werewolf_game_detail(game), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_werewolf_game_view(request, game_id):
    game = get_object_or_404(WerewolfGame, pk=game_id)
    return Response(build_werewolf_game_detail(game), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def advance_werewolf_game_view(request, game_id):
    game = get_object_or_404(WerewolfGame, pk=game_id)
    observer_note = str(request.data.get('observer_note', '') or '').strip()
    try:
        game = advance_werewolf_game(game, observer_note=observer_note)
    except ValueError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(build_werewolf_game_detail(game), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_werewolf_game_view(request, game_id):
    game = get_object_or_404(WerewolfGame, pk=game_id)
    game = reset_werewolf_game(game)
    return Response(build_werewolf_game_detail(game), status=status.HTTP_200_OK)
