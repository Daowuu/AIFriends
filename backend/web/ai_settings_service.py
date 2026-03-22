from django.conf import settings as django_settings

from web.models import Character, UserAISettings

ASR_DEFAULT_API_BASE = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
ASR_DEFAULT_MODEL_NAME = 'qwen3-asr-flash'
TTS_DEFAULT_WS_BASE = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
TTS_DEFAULT_INTL_WS_BASE = 'wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference'

PROVIDER_CONFIGS = {
    'aliyun': {
        'label': '阿里云百炼',
        'helper': '适合直接接入 DashScope 兼容 OpenAI 的聊天模型。',
        'default_api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'default_model_name': 'qwen-plus',
    },
    'deepseek': {
        'label': 'DeepSeek',
        'helper': '适合直接接入 DeepSeek 官方兼容接口。',
        'default_api_base': 'https://api.deepseek.com/v1',
        'default_model_name': 'deepseek-chat',
    },
    'minimax': {
        'label': 'MiniMax',
        'helper': '适合接入 MiniMax 官方兼容 OpenAI 的聊天接口。',
        'default_api_base': 'https://api.minimaxi.com/v1',
        'default_model_name': 'MiniMax-Text-01',
    },
    'openai': {
        'label': 'OpenAI',
        'helper': '适合接入 OpenAI 官方接口。',
        'default_api_base': 'https://api.openai.com/v1',
        'default_model_name': 'gpt-4o-mini',
    },
    'custom': {
        'label': '自定义兼容接口',
        'helper': '适合接入任何兼容 OpenAI Chat Completions 的网关。',
        'default_api_base': '',
        'default_model_name': '',
    },
}


def get_or_create_user_ai_settings(user):
    return UserAISettings.objects.get_or_create(user=user)[0]


def get_provider_config(provider):
    return PROVIDER_CONFIGS.get(provider) or PROVIDER_CONFIGS['aliyun']


def serialize_provider_options():
    return [
        {
            'value': key,
            'label': value['label'],
            'helper': value['helper'],
            'default_api_base': value['default_api_base'],
            'default_model_name': value['default_model_name'],
        }
        for key, value in PROVIDER_CONFIGS.items()
    ]


def serialize_user_ai_settings(settings):
    provider_config = get_provider_config(settings.provider)
    return {
        'enabled': settings.enabled,
        'provider': settings.provider,
        'api_base': settings.api_base,
        'model_name': settings.model_name,
        'has_api_key': bool(settings.api_key.strip()),
        'resolved_api_base': settings.api_base.strip() or provider_config['default_api_base'],
        'resolved_model_name': settings.model_name.strip() or provider_config['default_model_name'],
        'chat_supports_dashscope_audio': settings.chat_supports_dashscope_audio,
        'asr_enabled': settings.asr_enabled,
        'asr_api_base': settings.asr_api_base,
        'asr_model_name': settings.asr_model_name,
        'has_asr_api_key': bool(settings.asr_api_key.strip()),
        'resolved_asr_api_base': settings.asr_api_base.strip() or ASR_DEFAULT_API_BASE,
        'resolved_asr_model_name': settings.asr_model_name.strip() or ASR_DEFAULT_MODEL_NAME,
        'updated_at': settings.updated_at.isoformat(),
    }


def serialize_runtime_config(runtime_config, *, fallback_label='未启用'):
    if not runtime_config:
        return {
            'enabled': False,
            'source': 'disabled',
            'provider': '',
            'api_base': '',
            'model_name': '',
            'label': fallback_label,
            'reason': '',
        }

    return {
        'enabled': True,
        'source': runtime_config.get('source', ''),
        'provider': runtime_config.get('provider', ''),
        'api_base': runtime_config.get('api_base', ''),
        'model_name': runtime_config.get('model_name', ''),
        'label': runtime_config.get('label', runtime_config.get('source', '')),
        'reason': runtime_config.get('reason', ''),
    }


def is_truthy(value):
    return str(value).lower() in {'1', 'true', 'yes', 'on'}


def is_dashscope_compatible_api_base(api_base: str):
    normalized = str(api_base or '').strip().lower()
    return any(marker in normalized for marker in (
        'dashscope.aliyuncs.com',
        'dashscope-intl.aliyuncs.com',
    ))


def resolve_dashscope_audio_reuse_source(*, explicit_enabled: bool, provider: str, api_base: str, source_prefix: str):
    if explicit_enabled:
        return f'{source_prefix}_explicit_toggle'
    if provider == 'aliyun':
        return f'{source_prefix}_provider_default'
    if is_dashscope_compatible_api_base(api_base):
        return f'{source_prefix}_domain_fallback'
    return ''


def resolve_user_ai_settings_payload(settings, payload):
    provider = str(payload.get('provider', settings.provider)).strip() or settings.provider
    provider_config = get_provider_config(provider)
    clear_api_key = str(payload.get('clear_api_key', '')).lower() in {'1', 'true', 'yes', 'on'}
    raw_api_key = str(payload.get('api_key', '')).strip()
    api_key = '' if clear_api_key else (raw_api_key or settings.api_key.strip())
    api_base = str(payload.get('api_base', settings.api_base)).strip() or provider_config['default_api_base']
    model_name = str(payload.get('model_name', settings.model_name)).strip() or provider_config['default_model_name']

    return {
        'provider': provider,
        'api_key': api_key,
        'api_base': api_base,
        'model_name': model_name,
        'clear_api_key': clear_api_key,
    }


def resolve_user_asr_settings_payload(settings, payload):
    asr_enabled = str(payload.get('asr_enabled', settings.asr_enabled)).lower() in {'1', 'true', 'yes', 'on'}
    clear_asr_api_key = str(payload.get('clear_asr_api_key', '')).lower() in {'1', 'true', 'yes', 'on'}
    raw_api_key = str(payload.get('asr_api_key', '')).strip()
    asr_api_key = '' if clear_asr_api_key else (raw_api_key or settings.asr_api_key.strip())
    asr_api_base = str(payload.get('asr_api_base', settings.asr_api_base)).strip() or ASR_DEFAULT_API_BASE
    asr_model_name = str(payload.get('asr_model_name', settings.asr_model_name)).strip() or ASR_DEFAULT_MODEL_NAME

    return {
        'asr_enabled': asr_enabled,
        'asr_api_key': asr_api_key,
        'asr_api_base': asr_api_base,
        'asr_model_name': asr_model_name,
        'clear_asr_api_key': clear_asr_api_key,
    }


def get_server_ai_runtime_defaults():
    return getattr(django_settings, 'AI_RUNTIME', {
        'chat': {},
        'asr': {},
        'tts': {},
    })

def get_runtime_ai_resolution(user):
    settings = get_or_create_user_ai_settings(user)
    server_runtime = get_server_ai_runtime_defaults()
    server_chat = server_runtime.get('chat', {})

    if settings.enabled:
        provider_config = get_provider_config(settings.provider)
        api_key = settings.api_key.strip()
        api_base = settings.api_base.strip() or provider_config['default_api_base']
        model_name = settings.model_name.strip() or provider_config['default_model_name']

        if not api_key:
            return {
                'status': 'invalid',
                'reason': 'user_missing_api_key',
                'config': None,
            }
        if not api_base:
            return {
                'status': 'invalid',
                'reason': 'user_missing_api_base',
                'config': None,
            }
        if not model_name:
            return {
                'status': 'invalid',
                'reason': 'user_missing_model_name',
                'config': None,
            }

        dashscope_audio_reuse_source = resolve_dashscope_audio_reuse_source(
            explicit_enabled=settings.chat_supports_dashscope_audio,
            provider=settings.provider,
            api_base=api_base,
            source_prefix='user',
        )
        audio_reuse_enabled = bool(dashscope_audio_reuse_source)
        return {
            'status': 'ok',
            'reason': '',
            'config': {
                'source': 'user',
                'provider': settings.provider,
                'api_key': api_key,
                'api_base': api_base,
                'model_name': model_name,
                'dashscope_audio_enabled': audio_reuse_enabled,
                'dashscope_audio_reuse_source': dashscope_audio_reuse_source,
                'label': '个人聊天配置',
            },
        }

    api_key = str(server_chat.get('api_key', '')).strip()
    api_base = str(server_chat.get('api_base', '')).strip()
    model_name = str(server_chat.get('model_name', 'qwen-plus')).strip() or 'qwen-plus'

    if not api_key or not api_base:
        return {
            'status': 'missing',
            'reason': 'no_runtime_config',
            'config': None,
        }

    dashscope_audio_reuse_source = ''
    if bool(server_chat.get('supports_dashscope_audio', False)):
        dashscope_audio_reuse_source = 'env_explicit_toggle'
    elif is_dashscope_compatible_api_base(api_base):
        dashscope_audio_reuse_source = 'env_domain_fallback'

    return {
        'status': 'ok',
        'reason': '',
        'config': {
            'source': 'env',
            'provider': str(server_chat.get('provider', '')).strip() or 'env',
            'api_key': api_key,
            'api_base': api_base,
            'model_name': model_name,
            'dashscope_audio_enabled': bool(dashscope_audio_reuse_source),
            'dashscope_audio_reuse_source': dashscope_audio_reuse_source,
            'label': '服务端默认聊天配置',
        },
    }


def get_runtime_ai_config(user):
    return get_runtime_ai_resolution(user)['config']


def get_dashscope_runtime_config(user):
    settings = get_or_create_user_ai_settings(user)
    server_runtime = get_server_ai_runtime_defaults()
    server_chat = server_runtime.get('chat', {})
    server_asr = server_runtime.get('asr', {})
    if settings.asr_enabled:
        if not settings.asr_api_key.strip():
            return None

        return {
            'source': 'user_asr',
            'provider': 'aliyun',
            'api_key': settings.asr_api_key.strip(),
            'api_base': settings.asr_api_base.strip() or ASR_DEFAULT_API_BASE,
            'model_name': settings.asr_model_name.strip() or ASR_DEFAULT_MODEL_NAME,
            'label': '独立 ASR 配置',
        }

    user_runtime = get_runtime_ai_config(user)

    if user_runtime and user_runtime.get('dashscope_audio_enabled'):
        return {
            'source': 'user_chat',
            'provider': 'aliyun',
            'api_key': user_runtime['api_key'],
            'api_base': user_runtime['api_base'],
            'model_name': str(server_asr.get('model_name', ASR_DEFAULT_MODEL_NAME)).strip() or ASR_DEFAULT_MODEL_NAME,
            'label': '复用聊天配置',
            'dashscope_audio_reuse_source': user_runtime.get('dashscope_audio_reuse_source', ''),
        }

    api_key = str(server_asr.get('api_key', '')).strip() or str(server_chat.get('api_key', '')).strip()
    api_base = str(server_asr.get('api_base', '')).strip() or str(server_chat.get('api_base', '')).strip()
    model_name = str(server_asr.get('model_name', '')).strip() or ASR_DEFAULT_MODEL_NAME
    explicit_asr_base = bool(str(server_asr.get('api_base', '')).strip())

    if not api_key or not api_base:
        return None

    if not explicit_asr_base and not bool(server_chat.get('supports_dashscope_audio', False)) and not is_dashscope_compatible_api_base(api_base):
        return None

    return {
        'source': 'env',
        'provider': 'aliyun',
        'api_key': api_key,
        'api_base': api_base,
        'model_name': model_name,
        'label': '服务端语音配置',
        'dashscope_audio_reuse_source': 'env_explicit_asr_base' if explicit_asr_base else 'env_domain_fallback',
    }


def get_dashscope_websocket_api_url(api_base: str):
    api_base = str(api_base or '').strip().lower()
    if 'dashscope-intl' in api_base:
        return TTS_DEFAULT_INTL_WS_BASE
    return TTS_DEFAULT_WS_BASE


def get_runtime_tts_config(user):
    dashscope_runtime = get_dashscope_runtime_config(user)
    if not dashscope_runtime:
        return None

    server_tts = get_server_ai_runtime_defaults().get('tts', {})
    model_name = str(server_tts.get('model_name', '')).strip() or 'cosyvoice-v3.5-plus'
    return {
        'source': dashscope_runtime['source'],
        'provider': dashscope_runtime['provider'],
        'api_base': get_dashscope_websocket_api_url(dashscope_runtime['api_base']),
        'model_name': model_name,
        'label': dashscope_runtime.get('label', 'DashScope TTS'),
    }


def get_runtime_summary(user):
    latest_character = Character.objects.filter(user=user).select_related('voice').order_by('-updated_at', '-id').first()
    chat_resolution = get_runtime_ai_resolution(user)
    chat_runtime_config = chat_resolution['config']
    asr_runtime_config = get_dashscope_runtime_config(user)
    tts_runtime_config = get_runtime_tts_config(user)

    if chat_resolution['status'] == 'invalid':
        chat_runtime_config = {
            'source': 'user_invalid',
            'provider': '',
            'api_base': '',
            'model_name': '',
            'label': '个人聊天配置不完整',
            'reason': chat_resolution['reason'],
        }

    recent_character_summary = None
    if latest_character:
        recent_character_summary = {
            'id': latest_character.id,
            'name': latest_character.name,
            'memory_mode': latest_character.memory_mode,
            'reply_style': latest_character.reply_style,
            'voice_name': latest_character.voice.name if latest_character.voice else '',
            'voice_model_name': latest_character.voice.model_name if latest_character.voice else '',
        }

    return {
        'chat_runtime': serialize_runtime_config(
            chat_runtime_config,
            fallback_label='服务端默认或本地回退',
        ),
        'asr_runtime': serialize_runtime_config(asr_runtime_config, fallback_label='聊天配置或服务端环境'),
        'tts_runtime': serialize_runtime_config(tts_runtime_config, fallback_label='DashScope 语音播报未启用'),
        'chat_runtime_status': chat_resolution['status'],
        'chat_runtime_reason': chat_resolution['reason'],
        'dashscope_audio_reuse_source': (
            (asr_runtime_config or {}).get('dashscope_audio_reuse_source')
            or (chat_runtime_config or {}).get('dashscope_audio_reuse_source', '')
        ),
        'recent_character_summary': recent_character_summary,
        'prompt_layers': [
            'platform',
            'voice',
            'persona',
            'character_prompt',
            'creator_ai',
            'memory',
            'recent_dialogue',
        ],
    }
