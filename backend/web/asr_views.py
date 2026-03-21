from openai import OpenAI
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from web.ai_settings_service import get_dashscope_runtime_config


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def speech_to_text_view(request):
    audio_data = str(request.data.get('audio_data', '')).strip()

    if not audio_data.startswith('data:audio/'):
        return Response({'detail': '缺少有效的音频数据。'}, status=status.HTTP_400_BAD_REQUEST)

    runtime_config = get_dashscope_runtime_config(request.user)
    if not runtime_config:
        return Response({
            'detail': '语音识别当前需要阿里云百炼配置。请在 API 设置中切换到阿里云，或在服务端配置 ASR_API_KEY / ASR_API_BASE。',
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        client = OpenAI(
            api_key=runtime_config['api_key'],
            base_url=runtime_config['api_base'],
        )
        completion = client.chat.completions.create(
            model=runtime_config.get('model_name', 'qwen3-asr-flash'),
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'input_audio',
                            'input_audio': {
                                'data': audio_data,
                            },
                        },
                    ],
                },
            ],
            stream=False,
            extra_body={
                'asr_options': {
                    'enable_itn': True,
                },
            },
        )
        transcript = ''
        if completion.choices:
            transcript = (completion.choices[0].message.content or '').strip()

        if not transcript:
            return Response({'detail': '没有识别到清晰的语音内容。'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'text': transcript}, status=status.HTTP_200_OK)
    except Exception as error:
        return Response({'detail': f'语音识别失败：{error}'}, status=status.HTTP_400_BAD_REQUEST)
