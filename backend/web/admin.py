from django.contrib import admin

from web.models import (
    Character,
    Friend,
    Message,
    SystemPrompt,
    UserAISettings,
    UserProfile,
    Voice,
    WerewolfEvent,
    WerewolfGame,
    WerewolfSeat,
    WerewolfSpeech,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'display_name')
    search_fields = ('user__username', 'display_name', 'bio')


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'voice', 'updated_at')
    search_fields = ('name', 'user__username', 'voice__name', 'voice__voice_code')


@admin.register(Voice)
class VoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'voice_code', 'model_name', 'source', 'owner', 'is_active')
    list_filter = ('provider', 'source', 'is_active', 'model_name')
    search_fields = ('name', 'voice_code', 'description', 'owner__username')


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'character', 'created_at')
    search_fields = ('user__username', 'character__name')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'friend', 'role', 'created_at')
    search_fields = ('friend__user__username', 'friend__character__name', 'content')


@admin.register(SystemPrompt)
class SystemPromptAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'title', 'updated_at')
    search_fields = ('key', 'title', 'content')


@admin.register(UserAISettings)
class UserAISettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'provider', 'enabled', 'updated_at')
    search_fields = ('user__username', 'provider', 'model_name', 'api_base')


@admin.register(WerewolfGame)
class WerewolfGameAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'phase', 'winner', 'updated_at')
    search_fields = ('title',)
    list_filter = ('status', 'phase', 'winner')


@admin.register(WerewolfSeat)
class WerewolfSeatAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'seat_order', 'display_name', 'identity', 'is_alive', 'source_type')
    search_fields = ('display_name', 'game__title')
    list_filter = ('identity', 'is_alive', 'source_type')


@admin.register(WerewolfEvent)
class WerewolfEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'event_type', 'phase', 'created_at')
    search_fields = ('game__title', 'title', 'content')
    list_filter = ('event_type', 'phase')


@admin.register(WerewolfSpeech)
class WerewolfSpeechAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'seat', 'phase', 'audience', 'created_at')
    search_fields = ('game__title', 'seat__display_name', 'content')
    list_filter = ('phase', 'audience')
