from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from web.api_helpers import get_user_profile, serialize_user


REFRESH_COOKIE_NAME = 'refresh_token'
REFRESH_COOKIE_MAX_AGE = int(timedelta(days=7).total_seconds())


def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        samesite='Lax',
        secure=False,
        path='/',
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response({'detail': '用户名和密码不能为空。'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'detail': '用户名或密码错误。'}, status=status.HTTP_400_BAD_REQUEST)

    refresh = RefreshToken.for_user(user)
    response = Response(
        {
            'access': str(refresh.access_token),
            'user': serialize_user(user),
        },
        status=status.HTTP_200_OK,
    )
    _set_refresh_cookie(response, str(refresh))
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    password_confirm = request.data.get('password_confirm', '')

    if not username or not password or not password_confirm:
        return Response({'detail': '请完整填写注册信息。'}, status=status.HTTP_400_BAD_REQUEST)

    if password != password_confirm:
        return Response({'detail': '两次输入的密码不一致。'}, status=status.HTTP_400_BAD_REQUEST)

    if len(username) < 3:
        return Response({'detail': '用户名长度至少为 3。'}, status=status.HTTP_400_BAD_REQUEST)

    if len(password) < 6:
        return Response({'detail': '密码长度至少为 6。'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({'detail': '用户名已存在。'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password)
    get_user_profile(user)

    refresh = RefreshToken.for_user(user)
    response = Response(
        {
            'access': str(refresh.access_token),
            'user': serialize_user(user),
        },
        status=status.HTTP_201_CREATED,
    )
    _set_refresh_cookie(response, str(refresh))
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    response = Response({'detail': '退出成功。'}, status=status.HTTP_200_OK)
    response.delete_cookie(REFRESH_COOKIE_NAME, path='/')
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        return Response({'detail': '缺少 refresh token。'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        refresh = RefreshToken(refresh_token)
        access = str(refresh.access_token)
    except TokenError:
        return Response({'detail': 'refresh token 已失效。'}, status=status.HTTP_401_UNAUTHORIZED)

    return Response({'access': access}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info_view(request):
    return Response({'user': serialize_user(request.user)}, status=status.HTTP_200_OK)
