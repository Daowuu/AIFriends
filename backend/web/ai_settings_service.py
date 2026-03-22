from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings as django_settings
from dotenv import dotenv_values, set_key

from web.models import Character

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


@dataclass
class RuntimeEnvSettings:
    enabled: bool
    provider: str
    api_key: str
    api_base: str
    model_name: str
    chat_supports_dashscope_audio: bool
    asr_enabled: bool
    asr_api_key: str
    asr_api_base: str
    asr_model_name: str
    updated_at: str
    env_path: Path


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


def _get_runtime_env_path():
    backend_env = Path(django_settings.BASE_DIR) / '.env'
    root_env = Path(django_settings.BASE_DIR).parent / '.env'
    if backend_env.exists():
        return backend_env
    if root_env.exists():
        return root_env
    return backend_env


def _load_runtime_env_values():
    env_path = _get_runtime_env_path()
    values = dotenv_values(env_path) if env_path.exists() else {}
    return env_path, values


def _env_str(values, key, default=''):
    value = values.get(key)
    if value is None:
        return default
    return str(value).strip()


def _env_bool(values, key, default=False):
    value = values.get(key)
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _format_file_updated_at(path: Path):
    if not path.exists():
        return ''
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()


def get_local_runtime_settings():
    env_path, values = _load_runtime_env_values()
    provider = _env_str(values, 'API_PROVIDER', 'aliyun') or 'aliyun'
    api_key = _env_str(values, 'API_KEY', '')
    api_base = _env_str(values, 'API_BASE', '')
    model_name = _env_str(values, 'CHAT_MODEL', '')
    asr_api_key = _env_str(values, 'ASR_API_KEY', '')
    asr_api_base = _env_str(values, 'ASR_API_BASE', '')
    asr_model_name = _env_str(values, 'ASR_MODEL', '')

    enabled = _env_bool(values, 'RUNTIME_ENABLED', bool(api_key or api_base))
    asr_enabled = _env_bool(values, 'ASR_ENABLED', bool(asr_api_key or asr_api_base))

    return RuntimeEnvSettings(
        enabled=enabled,
        provider=provider,
        api_key=api_key,
        api_base=api_base,
        model_name=model_name,
        chat_supports_dashscope_audio=_env_bool(values, 'CHAT_SUPPORTS_DASHSCOPE_AUDIO', False),
        asr_enabled=asr_enabled,
        asr_api_key=asr_api_key,
        asr_api_base=asr_api_base,
        asr_model_name=asr_model_name,
        updated_at=_format_file_updated_at(env_path),
        env_path=env_path,
    )


def serialize_user_ai_settings(settings: RuntimeEnvSettings):
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
        'updated_at': settings.updated_at,
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


def resolve_user_ai_settings_payload(settings: RuntimeEnvSettings, payload):
    provider = str(payload.get('provider', settings.provider)).strip() or settings.provider
    provider_config = get_provider_config(provider)
    clear_api_key = str(payload.get('clear_api_key', '')).lower() in {'1', 'true', 'yes', 'on'}
    raw_api_key = str(payload.get('api_key', '')).strip()
    api_key = '' if clear_api_key else (raw_api_key or settings.api_key.strip())
    api_base = str(payload.get('api_base', settings.api_base)).strip() or provider_config['default_api_base']
    model_name = str(payload.get('model_name', settings.model_name)).strip() or provider_config['default_model_name']

    return {
        'enabled': str(payload.get('enabled', settings.enabled)).lower() in {'1', 'true', 'yes', 'on'},
        'provider': provider,
        'api_key': api_key,
        'api_base': api_base,
        'model_name': model_name,
        'clear_api_key': clear_api_key,
        'chat_supports_dashscope_audio': str(
            payload.get('chat_supports_dashscope_audio', settings.chat_supports_dashscope_audio),
        ).lower() in {'1', 'true', 'yes', 'on'},
    }


def resolve_user_asr_settings_payload(settings: RuntimeEnvSettings, payload):
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


def save_runtime_env_settings(chat_payload=None, asr_payload=None):
    settings = get_local_runtime_settings()
    env_path = settings.env_path
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.touch()

    if chat_payload is not None:
        set_key(env_path, 'RUNTIME_ENABLED', 'true' if chat_payload['enabled'] else 'false', quote_mode='always')
        set_key(env_path, 'API_PROVIDER', chat_payload['provider'], quote_mode='always')
        set_key(env_path, 'API_KEY', chat_payload['api_key'], quote_mode='always')
        set_key(env_path, 'API_BASE', chat_payload['api_base'], quote_mode='always')
        set_key(env_path, 'CHAT_MODEL', chat_payload['model_name'], quote_mode='always')
        set_key(
            env_path,
            'CHAT_SUPPORTS_DASHSCOPE_AUDIO',
            'true' if chat_payload['chat_supports_dashscope_audio'] else 'false',
            quote_mode='always',
        )

    if asr_payload is not None:
        set_key(env_path, 'ASR_ENABLED', 'true' if asr_payload['asr_enabled'] else 'false', quote_mode='always')
        set_key(env_path, 'ASR_API_KEY', asr_payload['asr_api_key'], quote_mode='always')
        set_key(env_path, 'ASR_API_BASE', asr_payload['asr_api_base'], quote_mode='always')
        set_key(env_path, 'ASR_MODEL', asr_payload['asr_model_name'], quote_mode='always')

    return get_local_runtime_settings()


def get_server_ai_runtime_defaults():
    settings = get_local_runtime_settings()
    return {
        'chat': {
            'enabled': settings.enabled,
            'provider': settings.provider,
            'api_key': settings.api_key,
            'api_base': settings.api_base,
            'model_name': settings.model_name,
            'supports_dashscope_audio': settings.chat_supports_dashscope_audio,
        },
        'asr': {
            'enabled': settings.asr_enabled,
            'api_key': settings.asr_api_key,
            'api_base': settings.asr_api_base,
            'model_name': settings.asr_model_name,
        },
        'tts': {
            'model_name': str(getattr(django_settings, 'AI_RUNTIME', {}).get('tts', {}).get('model_name', '')).strip()
            or 'cosyvoice-v3.5-plus',
        },
        'demo_quota': getattr(django_settings, 'AI_RUNTIME', {}).get('demo_quota', {}),
    }


def get_runtime_ai_resolution():
    runtime = get_server_ai_runtime_defaults()
    chat = runtime.get('chat', {})
    provider = str(chat.get('provider', '')).strip() or 'aliyun'
    provider_config = get_provider_config(provider)

    if not chat.get('enabled', False):
        return {'status': 'missing', 'reason': 'runtime_disabled', 'config': None}

    api_key = str(chat.get('api_key', '')).strip()
    api_base = str(chat.get('api_base', '')).strip() or provider_config['default_api_base']
    model_name = str(chat.get('model_name', '')).strip() or provider_config['default_model_name']

    if not api_key:
        return {'status': 'invalid', 'reason': 'local_missing_api_key', 'config': None}
    if not api_base:
        return {'status': 'invalid', 'reason': 'local_missing_api_base', 'config': None}
    if not model_name:
        return {'status': 'invalid', 'reason': 'local_missing_model_name', 'config': None}

    dashscope_audio_reuse_source = resolve_dashscope_audio_reuse_source(
        explicit_enabled=bool(chat.get('supports_dashscope_audio', False)),
        provider=provider,
        api_base=api_base,
        source_prefix='runtime_env',
    )
    return {
        'status': 'ok',
        'reason': '',
        'config': {
            'source': 'runtime_env',
            'provider': provider,
            'api_key': api_key,
            'api_base': api_base,
            'model_name': model_name,
            'dashscope_audio_enabled': bool(dashscope_audio_reuse_source),
            'dashscope_audio_reuse_source': dashscope_audio_reuse_source,
            'label': 'Studio / .env 同步配置',
        },
    }


def get_public_runtime_ai_resolution():
    return get_runtime_ai_resolution()


def get_dashscope_runtime_config():
    runtime = get_server_ai_runtime_defaults()
    asr = runtime.get('asr', {})

    if asr.get('enabled', False):
        api_key = str(asr.get('api_key', '')).strip()
        if not api_key:
            return None
        return {
            'source': 'runtime_asr',
            'provider': 'aliyun',
            'api_key': api_key,
            'api_base': str(asr.get('api_base', '')).strip() or ASR_DEFAULT_API_BASE,
            'model_name': str(asr.get('model_name', '')).strip() or ASR_DEFAULT_MODEL_NAME,
            'label': 'Studio / .env 独立 ASR 配置',
        }

    runtime_resolution = get_runtime_ai_resolution()
    runtime_config = runtime_resolution.get('config') or {}
    if runtime_config.get('dashscope_audio_enabled'):
        return {
            'source': runtime_config['source'],
            'provider': 'aliyun',
            'api_key': runtime_config['api_key'],
            'api_base': runtime_config['api_base'],
            'model_name': str(asr.get('model_name', '')).strip() or ASR_DEFAULT_MODEL_NAME,
            'label': '复用聊天运行时配置',
            'dashscope_audio_reuse_source': runtime_config.get('dashscope_audio_reuse_source', ''),
        }

    return None


def get_public_dashscope_runtime_config():
    return get_dashscope_runtime_config()


def get_dashscope_websocket_api_url(api_base: str):
    api_base = str(api_base or '').strip().lower()
    if 'dashscope-intl' in api_base:
        return TTS_DEFAULT_INTL_WS_BASE
    return TTS_DEFAULT_WS_BASE


def get_runtime_tts_config():
    dashscope_runtime = get_dashscope_runtime_config()
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


def get_runtime_summary():
    latest_character = Character.objects.select_related('voice').order_by('-updated_at', '-id').first()
    chat_resolution = get_runtime_ai_resolution()
    chat_runtime_config = chat_resolution['config']
    asr_runtime_config = get_dashscope_runtime_config()
    tts_runtime_config = get_runtime_tts_config()

    if chat_resolution['status'] == 'invalid':
        chat_runtime_config = {
            'source': 'runtime_invalid',
            'provider': '',
            'api_base': '',
            'model_name': '',
            'label': '运行时配置不完整',
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
        'chat_runtime': serialize_runtime_config(chat_runtime_config, fallback_label='当前未启用聊天配置'),
        'asr_runtime': serialize_runtime_config(asr_runtime_config, fallback_label='当前未启用独立 ASR 或聊天语音复用'),
        'tts_runtime': serialize_runtime_config(tts_runtime_config, fallback_label='当前未启用语音播报'),
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
