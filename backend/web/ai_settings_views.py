import base64
import io
import wave

from openai import OpenAI
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from web.ai_settings_service import (
    PROVIDER_CONFIGS,
    get_local_runtime_settings,
    get_runtime_summary,
    resolve_user_asr_settings_payload,
    resolve_user_ai_settings_payload,
    serialize_provider_options,
    serialize_user_ai_settings,
)


def build_silence_wav_data_url(duration_ms=300, sample_rate=16000):
    frame_count = max(1, int(sample_rate * duration_ms / 1000))
    pcm_bytes = b'\x00\x00' * frame_count

    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)

    base64_audio = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f'data:audio/wav;base64,{base64_audio}'


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def user_ai_settings_view(request):
    settings = get_local_runtime_settings()

    if request.method == 'GET':
        return Response({
            'settings': serialize_user_ai_settings(settings),
            'providers': serialize_provider_options(),
            'runtime_summary': get_runtime_summary(),
        }, status=status.HTTP_200_OK)

    provider = str(request.data.get('provider', settings.provider)).strip() or settings.provider
    if provider not in PROVIDER_CONFIGS:
        return Response({'detail': '不支持的模型提供方。'}, status=status.HTTP_400_BAD_REQUEST)

    enabled = str(request.data.get('enabled', settings.enabled)).lower() in {'1', 'true', 'yes', 'on'}
    clear_api_key = str(request.data.get('clear_api_key', '')).lower() in {'1', 'true', 'yes', 'on'}
    api_key = str(request.data.get('api_key', '')).strip()
    api_base = str(request.data.get('api_base', '')).strip()
    model_name = str(request.data.get('model_name', '')).strip()
    chat_supports_dashscope_audio = str(
        request.data.get('chat_supports_dashscope_audio', settings.chat_supports_dashscope_audio),
    ).lower() in {'1', 'true', 'yes', 'on'}
    asr_enabled = str(request.data.get('asr_enabled', settings.asr_enabled)).lower() in {'1', 'true', 'yes', 'on'}
    clear_asr_api_key = str(request.data.get('clear_asr_api_key', '')).lower() in {'1', 'true', 'yes', 'on'}
    asr_api_key = str(request.data.get('asr_api_key', '')).strip()
    asr_api_base = str(request.data.get('asr_api_base', '')).strip()
    asr_model_name = str(request.data.get('asr_model_name', '')).strip()

    settings.enabled = enabled
    settings.provider = provider
    settings.api_base = api_base[:512]
    settings.model_name = model_name[:128]
    settings.chat_supports_dashscope_audio = chat_supports_dashscope_audio
    settings.asr_enabled = asr_enabled
    settings.asr_api_base = asr_api_base[:512]
    settings.asr_model_name = asr_model_name[:128]

    if clear_api_key:
        settings.api_key = ''
    elif api_key:
        settings.api_key = api_key[:512]

    if clear_asr_api_key:
        settings.asr_api_key = ''
    elif asr_api_key:
        settings.asr_api_key = asr_api_key[:512]

    settings.save()

    return Response({
        'settings': serialize_user_ai_settings(settings),
        'providers': serialize_provider_options(),
        'runtime_summary': get_runtime_summary(),
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def test_user_ai_settings_view(request):
    settings = get_local_runtime_settings()
    resolved = resolve_user_ai_settings_payload(settings, request.data)
    provider = resolved['provider']

    if provider not in PROVIDER_CONFIGS:
        return Response({'detail': '不支持的模型提供方。'}, status=status.HTTP_400_BAD_REQUEST)
    if not resolved['api_key']:
        return Response({'detail': '没有可用的 API Key。'}, status=status.HTTP_400_BAD_REQUEST)
    if not resolved['api_base']:
        return Response({'detail': '没有可用的 API Base。'}, status=status.HTTP_400_BAD_REQUEST)
    if not resolved['model_name']:
        return Response({'detail': '没有可用的模型名。'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        client = OpenAI(api_key=resolved['api_key'], base_url=resolved['api_base'])
        response = client.chat.completions.create(
            model=resolved['model_name'],
            messages=[{'role': 'user', 'content': '请只回复“OK”，不要输出其他内容。'}],
            temperature=0,
            max_tokens=16,
        )
        content = response.choices[0].message.content if response.choices else ''
        return Response({
            'detail': '连接测试成功。',
            'reply_preview': str(content or '').strip()[:120],
            'resolved': {
                'provider': provider,
                'api_base': resolved['api_base'],
                'model_name': resolved['model_name'],
            },
        }, status=status.HTTP_200_OK)
    except Exception as error:
        return Response({'detail': f'连接测试失败：{error}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def test_user_asr_settings_view(request):
    settings = get_local_runtime_settings()
    resolved = resolve_user_asr_settings_payload(settings, request.data)

    if not resolved['asr_api_key']:
        return Response({'detail': '没有可用的 ASR API Key。'}, status=status.HTTP_400_BAD_REQUEST)
    if not resolved['asr_api_base']:
        return Response({'detail': '没有可用的 ASR API Base。'}, status=status.HTTP_400_BAD_REQUEST)
    if not resolved['asr_model_name']:
        return Response({'detail': '没有可用的 ASR 模型名。'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        client = OpenAI(api_key=resolved['asr_api_key'], base_url=resolved['asr_api_base'])
        response = client.chat.completions.create(
            model=resolved['asr_model_name'],
            messages=[{
                'role': 'user',
                'content': [{
                    'type': 'input_audio',
                    'input_audio': {'data': build_silence_wav_data_url()},
                }],
            }],
            stream=False,
            extra_body={'asr_options': {'enable_itn': True}},
        )

        content = response.choices[0].message.content if response.choices else ''
        preview = str(content or '').strip()[:120]
        detail = 'ASR 连接测试成功。模型已接受音频请求。'
        if not preview:
            detail += ' 测试音频是静音，未识别到语音属于正常现象。'
        return Response({
            'detail': detail,
            'reply_preview': preview,
            'resolved': {
                'api_base': resolved['asr_api_base'],
                'model_name': resolved['asr_model_name'],
            },
        }, status=status.HTTP_200_OK)
    except Exception as error:
        return Response({'detail': f'ASR 连接测试失败：{error}'}, status=status.HTTP_400_BAD_REQUEST)
