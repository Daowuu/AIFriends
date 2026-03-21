import os

from web.models import UserAISettings

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
        'asr_enabled': settings.asr_enabled,
        'asr_api_base': settings.asr_api_base,
        'asr_model_name': settings.asr_model_name,
        'has_asr_api_key': bool(settings.asr_api_key.strip()),
        'resolved_asr_api_base': settings.asr_api_base.strip() or ASR_DEFAULT_API_BASE,
        'resolved_asr_model_name': settings.asr_model_name.strip() or ASR_DEFAULT_MODEL_NAME,
        'updated_at': settings.updated_at.isoformat(),
    }


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


def get_runtime_ai_config(user):
    settings = get_or_create_user_ai_settings(user)

    if settings.enabled:
        if not settings.api_key.strip():
            return None

        provider_config = get_provider_config(settings.provider)
        return {
            'source': 'user',
            'provider': settings.provider,
            'api_key': settings.api_key.strip(),
            'api_base': settings.api_base.strip() or provider_config['default_api_base'],
            'model_name': settings.model_name.strip() or provider_config['default_model_name'],
        }

    api_key = os.getenv('API_KEY', '').strip()
    api_base = os.getenv('API_BASE', '').strip()
    model_name = os.getenv('CHAT_MODEL', 'qwen-plus').strip() or 'qwen-plus'

    if not api_key or not api_base:
        return None

    return {
        'source': 'env',
        'provider': 'env',
        'api_key': api_key,
        'api_base': api_base,
        'model_name': model_name,
    }


def get_dashscope_runtime_config(user):
    settings = get_or_create_user_ai_settings(user)
    if settings.asr_enabled:
        if not settings.asr_api_key.strip():
            return None

        return {
            'source': 'user_asr',
            'provider': 'aliyun',
            'api_key': settings.asr_api_key.strip(),
            'api_base': settings.asr_api_base.strip() or ASR_DEFAULT_API_BASE,
            'model_name': settings.asr_model_name.strip() or ASR_DEFAULT_MODEL_NAME,
        }

    user_runtime = get_runtime_ai_config(user)

    if user_runtime and 'dashscope' in user_runtime['api_base']:
        return {
            'source': 'user_chat',
            'provider': 'aliyun',
            'api_key': user_runtime['api_key'],
            'api_base': user_runtime['api_base'],
            'model_name': os.getenv('ASR_MODEL', ASR_DEFAULT_MODEL_NAME).strip() or ASR_DEFAULT_MODEL_NAME,
        }

    api_key = os.getenv('ASR_API_KEY', '').strip() or os.getenv('API_KEY', '').strip()
    api_base = os.getenv('ASR_API_BASE', '').strip() or os.getenv('API_BASE', '').strip()
    model_name = os.getenv('ASR_MODEL', '').strip() or ASR_DEFAULT_MODEL_NAME

    if not api_key or 'dashscope' not in api_base:
        return None

    return {
        'source': 'env',
        'provider': 'aliyun',
        'api_key': api_key,
        'api_base': api_base,
        'model_name': model_name,
    }


def get_dashscope_websocket_api_url(api_base: str):
    api_base = str(api_base or '').strip().lower()
    if 'dashscope-intl' in api_base:
        return TTS_DEFAULT_INTL_WS_BASE
    return TTS_DEFAULT_WS_BASE
