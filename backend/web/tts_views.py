from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

from web.ai_settings_service import get_dashscope_runtime_config, get_dashscope_websocket_api_url
from web.local_runtime import get_or_create_local_operator_user
from web.models import Character, Voice


def _build_tts_failure_detail(synthesizer, voice: Voice, fallback: str):
    last_response = getattr(synthesizer, 'last_response', None)
    request_id = getattr(synthesizer, 'last_request_id', '') or ''
    detail = fallback

    if isinstance(last_response, dict):
        header = last_response.get('header') or {}
        payload = last_response.get('payload') or {}
        error = payload.get('error') or {}
        event = header.get('event') or ''
        task_id = header.get('task_id') or request_id
        error_code = error.get('code') or payload.get('code') or ''
        error_message = error.get('message') or payload.get('message') or header.get('message') or ''

        parts = [fallback]
        if error_message:
            parts.append(f'服务端返回：{error_message}')
        if error_code:
            parts.append(f'错误码：{error_code}')
        if event:
            parts.append(f'事件：{event}')
        if task_id:
            parts.append(f'任务 ID：{task_id}')
        parts.append(f'音色：{voice.voice_code}')
        parts.append(f'模型：{voice.model_name}')
        return '；'.join(parts)

    parts = [fallback]
    if request_id:
        parts.append(f'任务 ID：{request_id}')
    parts.append(f'音色：{voice.voice_code}')
    parts.append(f'模型：{voice.model_name}')
    return '；'.join(parts)


def _resolve_public_character_voice(character: Character):
    if character.voice and character.voice.is_active:
        return character.voice
    return Voice.objects.filter(is_active=True, source='system').order_by('name', 'id').first()


def _build_preview_voice(payload):
    custom_voice_code = str(payload.get('custom_voice_code', '') or '').strip()
    if custom_voice_code:
        return Voice(
            owner=get_or_create_local_operator_user(),
            name=str(payload.get('custom_voice_name', '') or '').strip() or '自定义音色',
            provider='aliyun',
            source='custom',
            model_name=str(payload.get('custom_voice_model_name', '') or '').strip() or 'cosyvoice-v3.5-plus',
            voice_code=custom_voice_code,
            description=str(payload.get('custom_voice_description', '') or '').strip(),
            language='zh-CN',
            is_active=True,
        )

    try:
        voice_id = int(payload.get('voice_id', 0) or 0)
    except (TypeError, ValueError):
        return None

    if voice_id <= 0:
        return None

    return Voice.objects.filter(is_active=True).filter(pk=voice_id).filter(
        models.Q(source='system') | models.Q(owner=get_or_create_local_operator_user()),
    ).first()


def _synthesize_audio(text: str, voice: Voice, runtime_config):
    dashscope.api_key = runtime_config['api_key']
    dashscope.base_websocket_api_url = get_dashscope_websocket_api_url(runtime_config['api_base'])
    synthesizer = SpeechSynthesizer(model=voice.model_name, voice=voice.voice_code)
    audio = synthesizer.call(text[:1200])
    if hasattr(synthesizer, 'get_duplex_api'):
        try:
            synthesizer.get_duplex_api().close(1000, 'bye')
        except Exception:
            pass
    return synthesizer, audio


@api_view(['POST'])
@permission_classes([AllowAny])
def message_tts_view(request):
    try:
        character_id = int(request.data.get('character_id', 0) or 0)
    except (TypeError, ValueError):
        return Response({'detail': 'character_id 格式不正确。'}, status=status.HTTP_400_BAD_REQUEST)

    text = str(request.data.get('text', '') or '').strip()
    if character_id <= 0:
        return Response({'detail': '缺少有效的 character_id。'}, status=status.HTTP_400_BAD_REQUEST)
    if not text:
        return Response({'detail': '缺少有效的播报文本。'}, status=status.HTTP_400_BAD_REQUEST)

    character = get_object_or_404(Character.objects.select_related('voice'), pk=character_id)
    voice = _resolve_public_character_voice(character)
    if not voice:
        return Response({'detail': '当前没有可用音色。'}, status=status.HTTP_400_BAD_REQUEST)

    runtime_config = get_dashscope_runtime_config()
    if not runtime_config:
        return Response({
            'detail': '当前语音播报未启用，请先在 Studio 的运行时配置里补全语音运行时配置。',
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        synthesizer, audio = _synthesize_audio(text, voice, runtime_config)
        if not audio:
            return Response({
                'detail': _build_tts_failure_detail(synthesizer, voice, '语音合成没有返回有效音频。'),
            }, status=status.HTTP_502_BAD_GATEWAY)

        payload = bytes(audio) if not isinstance(audio, (bytes, bytearray)) else audio
        response = HttpResponse(payload, content_type='audio/mpeg')
        response['Cache-Control'] = 'no-store'
        response['X-Voice-Code'] = voice.voice_code
        return response
    except Exception as error:
        return Response({'detail': f'语音合成失败：{error}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def preview_tts_view(request):
    text = str(request.data.get('text', '') or '').strip()
    if not text:
        return Response({'detail': '缺少有效的试听文本。'}, status=status.HTTP_400_BAD_REQUEST)

    voice = _build_preview_voice(request.data)
    if not voice:
        return Response({'detail': '请先选择一个音色，或填入自定义音色 ID。'}, status=status.HTTP_400_BAD_REQUEST)

    runtime_config = get_dashscope_runtime_config()
    if not runtime_config:
        return Response({
            'detail': '当前语音播报未启用，请先在 Studio 的运行时配置里补全语音运行时配置。',
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        synthesizer, audio = _synthesize_audio(text, voice, runtime_config)
        if not audio:
            return Response({
                'detail': _build_tts_failure_detail(synthesizer, voice, '语音试听没有返回有效音频。'),
            }, status=status.HTTP_502_BAD_GATEWAY)

        payload = bytes(audio) if not isinstance(audio, (bytes, bytearray)) else audio
        response = HttpResponse(payload, content_type='audio/mpeg')
        response['Cache-Control'] = 'no-store'
        response['X-Voice-Code'] = voice.voice_code
        return response
    except Exception as error:
        return Response({'detail': f'语音试听失败：{error}'}, status=status.HTTP_400_BAD_REQUEST)
