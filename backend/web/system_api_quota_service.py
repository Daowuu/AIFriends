from django.conf import settings
from rest_framework import status
from rest_framework.response import Response


SYSTEM_API_QUOTA_SESSION_KEY = 'aifriends.system_api_quota.v1'


def get_text_chat_limit():
    return max(int(settings.AI_RUNTIME.get('demo_quota', {}).get('text_chat_limit', 20) or 0), 0)


def get_voice_chat_limit():
    return max(int(settings.AI_RUNTIME.get('demo_quota', {}).get('voice_chat_limit', 5) or 0), 0)


def _get_quota_bucket(session):
    bucket = session.get(SYSTEM_API_QUOTA_SESSION_KEY)
    if not isinstance(bucket, dict):
        bucket = {
            'text_chat_count': 0,
            'voice_chat_count': 0,
        }
        session[SYSTEM_API_QUOTA_SESSION_KEY] = bucket
    return bucket


def build_quota_exceeded_response(*, quota_type: str, authenticated: bool):
    if quota_type == 'voice':
        voice_limit = get_voice_chat_limit()
        detail = f'当前会话的语音试玩额度已用完（{voice_limit}/{voice_limit}）。'
    else:
        text_limit = get_text_chat_limit()
        detail = f'当前会话的文本试玩额度已用完（{text_limit}/{text_limit}）。'

    if authenticated:
        detail += ' 请在 AI Studio 配置个人 API 后继续使用。'
    else:
        detail += ' 请先登录，再在 AI Studio 配置个人 API 后继续使用。'

    return Response({
        'detail': detail,
        'quota_type': quota_type,
        'quota_exceeded': True,
    }, status=status.HTTP_429_TOO_MANY_REQUESTS)


def consume_system_api_quota(request, *, quota_type: str):
    bucket = _get_quota_bucket(request.session)

    if quota_type == 'voice':
        limit = get_voice_chat_limit()
        field = 'voice_chat_count'
    else:
        limit = get_text_chat_limit()
        field = 'text_chat_count'

    current = int(bucket.get(field, 0) or 0)
    if current >= limit:
        return False

    bucket[field] = current + 1
    request.session[SYSTEM_API_QUOTA_SESSION_KEY] = bucket
    request.session.modified = True
    return True
