from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from web.character_views import (
    create_character_view,
    get_single_character_view,
    list_character_voices_view,
    list_characters_view,
    remove_character_view,
    remove_character_voice_view,
    save_character_voice_view,
    update_character_view,
)
from web.ai_settings_views import (
    test_user_ai_settings_view,
    test_user_asr_settings_view,
    user_ai_settings_view,
)
from web.asr_views import demo_speech_to_text_view, speech_to_text_view
from web.feed_views import homepage_index_view, public_character_detail_view, user_space_view
from web.friend_views import (
    get_friend_list_view,
    get_or_create_friend_view,
    remove_friend_view,
)
from web.message_views import demo_chat_view, get_history_view, message_chat_view, reset_conversation_view
from web.studio_views import studio_overview_view
from web.tts_views import demo_message_tts_view, message_tts_view, preview_tts_view
from web.auth_views import (
    get_user_info_view,
    login_view,
    logout_view,
    refresh_token_view,
    register_view,
)
from web.profile_views import update_profile_view

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/account/login/', login_view, name='user_account_login'),
    path('user/account/register/', register_view, name='user_account_register'),
    path('user/account/logout/', logout_view, name='user_account_logout'),
    path('user/account/refresh_token/', refresh_token_view, name='user_account_refresh_token'),
    path('user/account/get_user_info/', get_user_info_view, name='user_account_get_user_info'),
    path('user/profile/update/', update_profile_view, name='user_profile_update'),
    path('user/settings/ai/', user_ai_settings_view, name='user_ai_settings'),
    path('user/settings/ai/test/', test_user_ai_settings_view, name='user_ai_settings_test'),
    path('user/settings/ai/test_asr/', test_user_asr_settings_view, name='user_ai_settings_asr_test'),
    path('studio/overview/', studio_overview_view, name='studio_overview'),
    path('user/space/<int:user_id>/', user_space_view, name='user_space'),
    path('character/public/<int:character_id>/', public_character_detail_view, name='character_public_detail'),
    path('create/character/list/', list_characters_view, name='character_list'),
    path('create/character/voice/list/', list_character_voices_view, name='character_voice_list'),
    path('create/character/voice/save/', save_character_voice_view, name='character_voice_save'),
    path('create/character/voice/<int:voice_id>/remove/', remove_character_voice_view, name='character_voice_remove'),
    path('create/character/create/', create_character_view, name='character_create'),
    path('create/character/<int:character_id>/', get_single_character_view, name='character_get_single'),
    path('create/character/<int:character_id>/update/', update_character_view, name='character_update'),
    path('create/character/<int:character_id>/remove/', remove_character_view, name='character_remove'),
    path('homepage/index/', homepage_index_view, name='homepage_index'),
    path('friend/get_or_create/', get_or_create_friend_view, name='friend_get_or_create'),
    path('friend/remove/', remove_friend_view, name='friend_remove'),
    path('friend/list/', get_friend_list_view, name='friend_list'),
    path('friend/message/history/', get_history_view, name='friend_message_history'),
    path('friend/message/chat/', message_chat_view, name='friend_message_chat'),
    path('demo/chat/', demo_chat_view, name='demo_chat'),
    path('friend/message/reset/', reset_conversation_view, name='friend_message_reset'),
    path('friend/message/asr/', speech_to_text_view, name='friend_message_asr'),
    path('friend/message/tts/', message_tts_view, name='friend_message_tts'),
    path('demo/asr/', demo_speech_to_text_view, name='demo_asr'),
    path('demo/tts/', demo_message_tts_view, name='demo_tts'),
    path('create/character/voice/preview/', preview_tts_view, name='character_voice_preview'),
]
