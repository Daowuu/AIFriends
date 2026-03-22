import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from django.conf import settings as django_settings
from dotenv import dotenv_values, set_key

from web.models import Character

ASR_DEFAULT_API_BASE = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
ASR_DEFAULT_MODEL_NAME = 'qwen3-asr-flash'
TTS_DEFAULT_MODEL_NAME = 'cosyvoice-v3.5-plus'
TTS_DEFAULT_WS_BASE = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
TTS_DEFAULT_INTL_WS_BASE = 'wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference'
RUNTIME_STORE_VERSION = 4
RUNTIME_STORE_ENV_KEY = 'AI_RUNTIME_CONFIG_JSON'
VOICE_API_KEY_NAME = 'aliyun_voice'

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
        'default_model_name': 'MiniMax-M2.7-highspeed',
    },
    'openai': {
        'label': 'OpenAI',
        'helper': '适合接入 OpenAI 官方接口。',
        'default_api_base': 'https://api.openai.com/v1',
        'default_model_name': 'gpt-5.4',
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
    asr_enabled: bool
    asr_api_key: str
    asr_api_base: str
    asr_model_name: str
    tts_model_name: str
    updated_at: str
    env_path: Optional[Path]
    source: str = 'runtime_env'


def get_provider_config(provider):
    return PROVIDER_CONFIGS.get(provider) or PROVIDER_CONFIGS['custom']


def _mask_secret(secret: str):
    secret = str(secret or '').strip()
    if not secret:
        return ''
    if len(secret) <= 8:
        return f'{secret[:2]}...{secret[-2:]}'
    return f'{secret[:4]}...{secret[-4:]}'


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
    configured = getattr(django_settings, 'AI_RUNTIME_ENV_PATH', '')
    if configured:
        return Path(configured)

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


def _now_iso():
    return datetime.now().astimezone().isoformat()


def _build_empty_runtime_settings(*, env_path=None):
    return RuntimeEnvSettings(
        enabled=False,
        provider='openai',
        api_key='',
        api_base='',
        model_name='',
        asr_enabled=False,
        asr_api_key='',
        asr_api_base='',
        asr_model_name='',
        tts_model_name=TTS_DEFAULT_MODEL_NAME,
        updated_at='',
        env_path=env_path,
        source='runtime_env',
    )


def _normalize_key_map(raw):
    if not isinstance(raw, dict):
        return {}
    normalized = {}
    for key, value in raw.items():
        key_text = str(key or '').strip()
        if not key_text:
            continue
        normalized[key_text] = str(value or '').strip()
    return normalized


def _normalize_chat_entry(provider: str, payload: dict):
    provider_key = str(provider or '').strip()
    if provider_key not in PROVIDER_CONFIGS or not isinstance(payload, dict):
        return None
    provider_config = get_provider_config(provider_key)
    return {
        'api_base': str(payload.get('api_base', '')).strip() or provider_config['default_api_base'],
        'model_name': str(payload.get('model_name', '')).strip() or provider_config['default_model_name'],
        'updated_at': str(payload.get('updated_at', '')).strip(),
    }


def _normalize_voice_entry(payload):
    payload = payload if isinstance(payload, dict) else {}
    provider = str(payload.get('provider', '')).strip() or 'aliyun'
    return {
        'provider': provider,
        'api_base': str(payload.get('api_base', '')).strip() or ASR_DEFAULT_API_BASE,
        'asr_model_name': str(payload.get('asr_model_name', '')).strip() or ASR_DEFAULT_MODEL_NAME,
        'tts_model_name': str(payload.get('tts_model_name', '')).strip() or TTS_DEFAULT_MODEL_NAME,
        'updated_at': str(payload.get('updated_at', '')).strip(),
    }


def _empty_runtime_store():
    return {
        'version': RUNTIME_STORE_VERSION,
        'active': {
            'chat_provider': None,
        },
        'api_keys': {},
        'chat': {},
        'voice': _normalize_voice_entry({}),
    }


def _normalize_runtime_store(store):
    if not isinstance(store, dict):
        return _empty_runtime_store()

    normalized = _empty_runtime_store()
    normalized['api_keys'] = _normalize_key_map(store.get('api_keys'))

    chat_raw = store.get('chat') if isinstance(store.get('chat'), dict) else {}
    chat = {}
    for provider in PROVIDER_CONFIGS:
        entry = _normalize_chat_entry(provider, chat_raw.get(provider))
        if entry:
            chat[provider] = entry
    normalized['chat'] = chat

    active = store.get('active') if isinstance(store.get('active'), dict) else {}
    active_provider = str(active.get('chat_provider', '')).strip() or None
    if active_provider not in chat:
        active_provider = next(iter(chat.keys()), None)
    normalized['active']['chat_provider'] = active_provider
    normalized['voice'] = _normalize_voice_entry(store.get('voice'))
    return normalized


def _serialize_runtime_store_json(store: dict):
    return json.dumps(_normalize_runtime_store(store), ensure_ascii=False, indent=2)


def _save_runtime_store_to_env(env_path: Path, store: dict):
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.touch()
    set_key(env_path, RUNTIME_STORE_ENV_KEY, _serialize_runtime_store_json(store), quote_mode='always')


def _load_runtime_store():
    env_path, values = _load_runtime_env_values()
    raw_store = _env_str(values, RUNTIME_STORE_ENV_KEY, '')
    if raw_store:
        try:
            parsed = json.loads(raw_store)
        except json.JSONDecodeError as error:
            raise ValueError('AI_RUNTIME_CONFIG_JSON 不是合法 JSON。') from error
        return env_path, _normalize_runtime_store(parsed), True
    return env_path, _empty_runtime_store(), False


def _pick_updated_at(*timestamps):
    values = [str(value or '').strip() for value in timestamps if str(value or '').strip()]
    if not values:
        return ''
    return max(values)


def _get_active_chat_provider(store: dict):
    active_provider = str(store.get('active', {}).get('chat_provider', '')).strip() or None
    if active_provider in store.get('chat', {}):
        return active_provider
    return next(iter(store.get('chat', {}).keys()), None)


def _get_chat_config(store: dict, provider: Optional[str]):
    if not provider:
        return None
    return store.get('chat', {}).get(str(provider).strip())


def _get_chat_api_key(store: dict, provider: Optional[str]):
    if not provider:
        return ''
    return str(store.get('api_keys', {}).get(str(provider).strip(), '')).strip()


def _get_voice_api_key(store: dict):
    return str(store.get('api_keys', {}).get(VOICE_API_KEY_NAME, '')).strip()


def _serialize_runtime_settings_from_store(store: dict, *, env_path: Optional[Path]):
    provider = _get_active_chat_provider(store) or 'openai'
    chat_config = _get_chat_config(store, provider) or {}
    voice_config = store.get('voice', {})
    chat_api_key = _get_chat_api_key(store, provider)
    voice_api_key = _get_voice_api_key(store)
    return RuntimeEnvSettings(
        enabled=bool(chat_api_key),
        provider=provider,
        api_key=chat_api_key,
        api_base=str(chat_config.get('api_base', '')).strip(),
        model_name=str(chat_config.get('model_name', '')).strip(),
        asr_enabled=bool(voice_api_key),
        asr_api_key=voice_api_key,
        asr_api_base=str(voice_config.get('api_base', '')).strip(),
        asr_model_name=str(voice_config.get('asr_model_name', '')).strip(),
        tts_model_name=str(voice_config.get('tts_model_name', '')).strip() or TTS_DEFAULT_MODEL_NAME,
        updated_at=_pick_updated_at(
            chat_config.get('updated_at', ''),
            voice_config.get('updated_at', ''),
        ),
        env_path=env_path,
        source='runtime_env',
    )


def get_current_runtime_settings():
    env_path, store, present = _load_runtime_store()
    if present:
        return _serialize_runtime_settings_from_store(store, env_path=env_path)
    return _build_empty_runtime_settings(env_path=env_path)


def serialize_user_ai_settings(settings: RuntimeEnvSettings):
    provider_config = get_provider_config(settings.provider)
    return {
        'enabled': settings.enabled,
        'provider': settings.provider,
        'api_base': settings.api_base,
        'model_name': settings.model_name,
        'has_api_key': bool(settings.api_key.strip()),
        'masked_api_key': _mask_secret(settings.api_key),
        'resolved_api_base': settings.api_base.strip() or provider_config['default_api_base'],
        'resolved_model_name': settings.model_name.strip() or provider_config['default_model_name'],
        'asr_enabled': settings.asr_enabled,
        'asr_api_base': settings.asr_api_base,
        'asr_model_name': settings.asr_model_name,
        'has_asr_api_key': bool(settings.asr_api_key.strip()),
        'masked_asr_api_key': _mask_secret(settings.asr_api_key),
        'resolved_asr_api_base': settings.asr_api_base.strip() or ASR_DEFAULT_API_BASE,
        'resolved_asr_model_name': settings.asr_model_name.strip() or ASR_DEFAULT_MODEL_NAME,
        'tts_model_name': settings.tts_model_name,
        'updated_at': settings.updated_at,
        'source': settings.source,
    }


def serialize_chat_provider_summary(provider: str, payload: dict, *, active_provider: Optional[str], api_keys: dict):
    provider_config = get_provider_config(provider)
    api_key = str(api_keys.get(provider, '')).strip()
    return {
        'provider': provider,
        'provider_label': provider_config['label'],
        'api_base': str(payload.get('api_base', '')).strip() or provider_config['default_api_base'],
        'model_name': str(payload.get('model_name', '')).strip() or provider_config['default_model_name'],
        'has_api_key': bool(api_key),
        'masked_api_key': _mask_secret(api_key),
        'is_active': provider == str(active_provider or '').strip(),
        'updated_at': str(payload.get('updated_at', '')).strip(),
    }


def list_chat_provider_summaries():
    _, store, _ = _load_runtime_store()
    active_provider = _get_active_chat_provider(store)
    configured_providers = [
        provider for provider in PROVIDER_CONFIGS
        if provider in store.get('chat', {})
    ]
    configured_providers.sort(key=lambda provider: (provider != active_provider, provider))
    return [
        serialize_chat_provider_summary(
            provider,
            store['chat'][provider],
            active_provider=active_provider,
            api_keys=store.get('api_keys', {}),
        )
        for provider in configured_providers
    ]


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


def resolve_user_ai_settings_payload(settings: RuntimeEnvSettings, payload):
    previous_provider = settings.provider or 'openai'
    previous_provider_config = get_provider_config(previous_provider)
    provider = str(payload.get('provider', previous_provider)).strip() or previous_provider
    provider_config = get_provider_config(provider)

    _, store, _ = _load_runtime_store()
    existing_target_config = _get_chat_config(store, provider) or {}
    existing_target_api_key = _get_chat_api_key(store, provider)

    raw_api_key = str(payload.get('api_key', '')).strip()
    if raw_api_key:
        api_key = raw_api_key
    elif provider == previous_provider:
        api_key = settings.api_key.strip()
    else:
        api_key = existing_target_api_key

    submitted_api_base = str(payload.get('api_base', '')).strip()
    if submitted_api_base:
        api_base = submitted_api_base
    elif provider == previous_provider and settings.api_base.strip():
        api_base = settings.api_base.strip()
    elif existing_target_config.get('api_base'):
        api_base = str(existing_target_config.get('api_base', '')).strip()
    else:
        api_base = provider_config['default_api_base']

    submitted_model_name = str(payload.get('model_name', '')).strip()
    if submitted_model_name:
        model_name = submitted_model_name
    elif provider == previous_provider and settings.model_name.strip():
        model_name = settings.model_name.strip()
    elif existing_target_config.get('model_name'):
        model_name = str(existing_target_config.get('model_name', '')).strip()
    else:
        model_name = provider_config['default_model_name']

    if provider != previous_provider:
        if api_base == (settings.api_base.strip() or previous_provider_config['default_api_base']) and not existing_target_config.get('api_base'):
            api_base = provider_config['default_api_base']
        if model_name == (settings.model_name.strip() or previous_provider_config['default_model_name']) and not existing_target_config.get('model_name'):
            model_name = provider_config['default_model_name']

    return {
        'enabled': bool(api_key),
        'provider': provider,
        'api_key': api_key,
        'api_base': api_base,
        'model_name': model_name,
    }


def resolve_user_asr_settings_payload(settings: RuntimeEnvSettings, payload):
    raw_api_key = str(payload.get('asr_api_key', '')).strip()
    asr_api_key = raw_api_key or settings.asr_api_key.strip()
    asr_api_base = str(payload.get('asr_api_base', settings.asr_api_base)).strip() or ASR_DEFAULT_API_BASE
    asr_model_name = str(payload.get('asr_model_name', settings.asr_model_name)).strip() or ASR_DEFAULT_MODEL_NAME
    tts_model_name = str(payload.get('tts_model_name', settings.tts_model_name)).strip() or TTS_DEFAULT_MODEL_NAME
    voice_provider = str(payload.get('voice_provider', 'aliyun')).strip() or 'aliyun'
    return {
        'provider': voice_provider,
        'asr_enabled': bool(asr_api_key),
        'asr_api_key': asr_api_key,
        'asr_api_base': asr_api_base,
        'asr_model_name': asr_model_name,
        'tts_model_name': tts_model_name,
    }


def save_runtime_env_settings(*, chat_payload, asr_payload):
    env_path, store, _ = _load_runtime_store()
    now = _now_iso()
    provider = str(chat_payload['provider']).strip()
    if provider not in PROVIDER_CONFIGS:
        raise ValueError('不支持的模型提供方。')

    store['chat'][provider] = {
        'api_base': str(chat_payload['api_base']).strip() or get_provider_config(provider)['default_api_base'],
        'model_name': str(chat_payload['model_name']).strip() or get_provider_config(provider)['default_model_name'],
        'updated_at': now,
    }
    store['api_keys'][provider] = str(chat_payload['api_key']).strip()
    store['active']['chat_provider'] = provider
    store['voice'] = {
        'provider': str(asr_payload.get('provider', 'aliyun')).strip() or 'aliyun',
        'api_base': str(asr_payload['asr_api_base']).strip() or ASR_DEFAULT_API_BASE,
        'asr_model_name': str(asr_payload['asr_model_name']).strip() or ASR_DEFAULT_MODEL_NAME,
        'tts_model_name': str(asr_payload['tts_model_name']).strip() or TTS_DEFAULT_MODEL_NAME,
        'updated_at': now,
    }
    store['api_keys'][VOICE_API_KEY_NAME] = str(asr_payload['asr_api_key']).strip()
    store['version'] = RUNTIME_STORE_VERSION

    _save_runtime_store_to_env(env_path, store)
    return _serialize_runtime_settings_from_store(store, env_path=env_path)


def get_server_ai_runtime_defaults():
    settings = get_current_runtime_settings()
    return {
        'chat': {
            'enabled': settings.enabled,
            'provider': settings.provider,
            'api_key': settings.api_key,
            'api_base': settings.api_base,
            'model_name': settings.model_name,
            'source': settings.source,
        },
        'asr': {
            'enabled': settings.asr_enabled,
            'provider': 'aliyun',
            'api_key': settings.asr_api_key,
            'api_base': settings.asr_api_base,
            'model_name': settings.asr_model_name,
            'source': settings.source,
        },
        'tts': {
            'provider': 'aliyun',
            'model_name': settings.tts_model_name,
        },
        'demo_quota': getattr(django_settings, 'AI_RUNTIME', {}).get('demo_quota', {}),
    }


def _build_runtime_label(*, kind='chat', provider=''):
    if kind == 'asr':
        return 'Studio / .env 当前语音配置'
    if kind == 'tts':
        return 'Studio / .env 当前语音播报配置'
    provider_label = get_provider_config(provider or 'custom')['label']
    return f'Studio / .env 当前聊天提供方 ({provider_label})'


def get_runtime_ai_resolution():
    runtime = get_server_ai_runtime_defaults()
    chat = runtime.get('chat', {})
    provider = str(chat.get('provider', '')).strip() or 'openai'
    provider_config = get_provider_config(provider)

    if not chat.get('enabled', False):
        return {'status': 'missing', 'reason': 'runtime_disabled', 'config': None}

    api_key = str(chat.get('api_key', '')).strip()
    api_base = str(chat.get('api_base', '')).strip() or provider_config['default_api_base']
    model_name = str(chat.get('model_name', '')).strip() or provider_config['default_model_name']
    source = str(chat.get('source', '')).strip() or 'runtime_env'

    if not api_key:
        return {'status': 'invalid', 'reason': 'local_missing_api_key', 'config': None}
    if not api_base:
        return {'status': 'invalid', 'reason': 'local_missing_api_base', 'config': None}
    if not model_name:
        return {'status': 'invalid', 'reason': 'local_missing_model_name', 'config': None}

    return {
        'status': 'ok',
        'reason': '',
        'config': {
            'source': source,
            'provider': provider,
            'api_key': api_key,
            'api_base': api_base,
            'model_name': model_name,
            'label': _build_runtime_label(kind='chat', provider=provider),
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
            'source': asr.get('source', 'runtime_env'),
            'provider': str(asr.get('provider', '')).strip() or 'aliyun',
            'api_key': api_key,
            'api_base': str(asr.get('api_base', '')).strip() or ASR_DEFAULT_API_BASE,
            'model_name': str(asr.get('model_name', '')).strip() or ASR_DEFAULT_MODEL_NAME,
            'label': _build_runtime_label(kind='asr'),
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
    model_name = str(server_tts.get('model_name', '')).strip() or TTS_DEFAULT_MODEL_NAME
    return {
        'source': dashscope_runtime['source'],
        'provider': dashscope_runtime['provider'],
        'api_base': get_dashscope_websocket_api_url(dashscope_runtime['api_base']),
        'model_name': model_name,
        'label': _build_runtime_label(kind='tts'),
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
        'asr_runtime': serialize_runtime_config(asr_runtime_config, fallback_label='当前未启用语音配置'),
        'tts_runtime': serialize_runtime_config(tts_runtime_config, fallback_label='当前未启用语音播报'),
        'chat_runtime_status': chat_resolution['status'],
        'chat_runtime_reason': chat_resolution['reason'],
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
