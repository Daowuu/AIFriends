from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from web.api_helpers import get_user_profile, serialize_user
from web.media_utils import remove_stored_file, replace_stored_file


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    user = request.user
    profile = get_user_profile(user)

    username = request.data.get('username', user.username).strip()
    display_name = request.data.get('display_name', '').strip()
    bio = request.data.get('bio', '').strip()
    avatar = request.FILES.get('avatar')
    remove_avatar = request.data.get('remove_avatar') in {'1', 'true', 'True'}

    if len(username) < 3:
        return Response({'detail': '用户名长度至少为 3。'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.exclude(pk=user.pk).filter(username=username).exists():
        return Response({'detail': '用户名已存在。'}, status=status.HTTP_400_BAD_REQUEST)

    user.username = username
    user.save(update_fields=['username'])

    profile.display_name = display_name
    profile.bio = bio

    if avatar:
        replace_stored_file(profile, 'avatar', avatar)
    elif remove_avatar:
        remove_stored_file(profile.avatar)
        profile.avatar = None

    profile.save()

    return Response({'user': serialize_user(user)}, status=status.HTTP_200_OK)
