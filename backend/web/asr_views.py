from openai import OpenAI
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from web.ai_settings_service import get_dashscope_runtime_config
from web.system_api_quota_service import build_quota_exceeded_response, consume_system_api_quota


def _transcribe_audio(audio_data: str, runtime_config):
    client = OpenAI(api_key=runtime_config['api_key'], base_url=runtime_config['api_base'])
    completion = client.chat.completions.create(
        model=runtime_config.get('model_name', 'qwen3-asr-flash'),
        messages=[{
            'role': 'user',
            'content': [{
                'type': 'input_audio',
                'input_audio': {'data': audio_data},
            }],
        }],
        stream=False,
        extra_body={'asr_options': {'enable_itn': True}},
    )
    transcript = ''
    if completion.choices:
        transcript = (completion.choices[0].message.content or '').strip()
    return transcript


@api_view(['POST'])
@permission_classes([AllowAny])
def speech_to_text_view(request):
    audio_data = str(request.data.get('audio_data', '')).strip()

    if not audio_data.startswith('data:audio/'):
        return Response({'detail': '缺少有效的音频数据。'}, status=status.HTTP_400_BAD_REQUEST)

    runtime_config = get_dashscope_runtime_config()
    if not runtime_config:
        return Response({
            'detail': '当前语音识别未启用，请先在 Studio 的运行时配置里补全可用的 ASR 或兼容 DashScope 的聊天配置。',
        }, status=status.HTTP_400_BAD_REQUEST)

    if runtime_config.get('source') == 'env':
        if not consume_system_api_quota(request, quota_type='voice'):
            return build_quota_exceeded_response(quota_type='voice')

    try:
        transcript = _transcribe_audio(audio_data, runtime_config)
        if not transcript:
            return Response({'detail': '没有识别到清晰的语音内容。'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'text': transcript}, status=status.HTTP_200_OK)
    except Exception as error:
        return Response({'detail': f'语音识别失败：{error}'}, status=status.HTTP_400_BAD_REQUEST)
