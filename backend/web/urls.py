from django.urls import path

from web.ai_settings_views import (
    test_user_ai_settings_view,
    test_user_asr_settings_view,
    user_ai_settings_view,
)
from web.asr_views import speech_to_text_view
from web.character_views import (
    create_character_view,
    get_single_character_view,
    list_character_voices_view,
    list_characters_view,
    reorder_characters_view,
    remove_character_view,
    remove_character_voice_view,
    save_character_voice_view,
    update_character_view,
)
from web.feed_views import homepage_index_view, public_character_detail_view
from web.message_views import get_history_view, message_chat_view, reset_conversation_view
from web.studio_views import studio_overview_view
from web.tts_views import message_tts_view, preview_tts_view
from web.werewolf_views import (
    advance_werewolf_game_view,
    create_werewolf_game_view,
    get_werewolf_game_view,
    list_werewolf_games_view,
    reset_werewolf_game_view,
)

urlpatterns = [
    path('runtime/settings/', user_ai_settings_view, name='runtime_settings'),
    path('runtime/settings/test/', test_user_ai_settings_view, name='runtime_settings_test'),
    path('runtime/settings/test_asr/', test_user_asr_settings_view, name='runtime_settings_asr_test'),
    path('studio/overview/', studio_overview_view, name='studio_overview'),
    path('character/public/<int:character_id>/', public_character_detail_view, name='character_public_detail'),
    path('character/list/', list_characters_view, name='character_list'),
    path('character/voice/list/', list_character_voices_view, name='character_voice_list'),
    path('character/voice/save/', save_character_voice_view, name='character_voice_save'),
    path('character/voice/<int:voice_id>/remove/', remove_character_voice_view, name='character_voice_remove'),
    path('character/create/', create_character_view, name='character_create'),
    path('character/reorder/', reorder_characters_view, name='character_reorder'),
    path('character/<int:character_id>/', get_single_character_view, name='character_get_single'),
    path('character/<int:character_id>/update/', update_character_view, name='character_update'),
    path('character/<int:character_id>/remove/', remove_character_view, name='character_remove'),
    path('homepage/index/', homepage_index_view, name='homepage_index'),
    path('session/history/', get_history_view, name='session_message_history'),
    path('session/chat/', message_chat_view, name='session_message_chat'),
    path('session/reset/', reset_conversation_view, name='session_message_reset'),
    path('session/asr/', speech_to_text_view, name='session_message_asr'),
    path('session/tts/', message_tts_view, name='session_message_tts'),
    path('character/voice/preview/', preview_tts_view, name='character_voice_preview'),
    path('werewolf/games/', list_werewolf_games_view, name='werewolf_game_list'),
    path('werewolf/games/create/', create_werewolf_game_view, name='werewolf_game_create'),
    path('werewolf/games/<int:game_id>/', get_werewolf_game_view, name='werewolf_game_detail'),
    path('werewolf/games/<int:game_id>/advance/', advance_werewolf_game_view, name='werewolf_game_advance'),
    path('werewolf/games/<int:game_id>/reset/', reset_werewolf_game_view, name='werewolf_game_reset'),
]
