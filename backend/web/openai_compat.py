from __future__ import annotations


def _supports_max_completion_tokens_retry(error):
    message = str(error or '')
    lowered = message.lower()
    return (
        'unsupported parameter' in lowered
        and 'max_tokens' in lowered
        and 'max_completion_tokens' in lowered
    )


def create_chat_completion(client, **kwargs):
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as error:
        if 'max_tokens' not in kwargs or not _supports_max_completion_tokens_retry(error):
            raise

        retry_kwargs = dict(kwargs)
        retry_kwargs['max_completion_tokens'] = retry_kwargs.pop('max_tokens')
        return client.chat.completions.create(**retry_kwargs)

