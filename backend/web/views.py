from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse


FRONTEND_INDEX_PATH = Path(settings.BASE_DIR) / 'static' / 'frontend' / 'index.html'


def spa_entry(request):
    if not FRONTEND_INDEX_PATH.exists():
        raise Http404('Frontend bundle not found. Run `npm run build` in the frontend directory.')

    return HttpResponse(
        FRONTEND_INDEX_PATH.read_text(encoding='utf-8'),
        content_type='text/html; charset=utf-8',
    )
