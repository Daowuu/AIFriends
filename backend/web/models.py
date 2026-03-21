from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=64, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    avatar = models.FileField(upload_to='user/photos/', blank=True, null=True)

    def __str__(self):
        return self.display_name or self.user.username


class Character(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters')
    name = models.CharField(max_length=64)
    profile = models.TextField(blank=True, default='')
    voice = models.ForeignKey(
        'Voice',
        on_delete=models.SET_NULL,
        related_name='characters',
        blank=True,
        null=True,
    )
    photo = models.FileField(upload_to='character/photos/', blank=True, null=True)
    background_image = models.FileField(
        upload_to='character/backgrounds/',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return self.name


class Friend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friends')
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='friends')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'character'], name='unique_user_character_friend'),
        ]
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.user.username} -> {self.character.name}'


class Message(models.Model):
    ROLE_CHOICES = (
        ('user', 'user'),
        ('assistant', 'assistant'),
    )

    friend = models.ForeignKey(Friend, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.friend_id}:{self.role}:{self.id}'


class SystemPrompt(models.Model):
    key = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=128, blank=True, default='')
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['key']

    def __str__(self):
        return self.title or self.key


class Voice(models.Model):
    PROVIDER_CHOICES = (
        ('aliyun', 'aliyun'),
    )
    SOURCE_CHOICES = (
        ('system', 'system'),
        ('custom', 'custom'),
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='voices',
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=64)
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES, default='aliyun')
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default='system')
    model_name = models.CharField(max_length=128, default='cosyvoice-v3-flash')
    voice_code = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=255, blank=True, default='')
    language = models.CharField(max_length=64, blank=True, default='zh-CN')
    sample_audio = models.FileField(upload_to='voice/samples/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['source', 'name', 'id']

    def __str__(self):
        return self.name


class UserAISettings(models.Model):
    PROVIDER_CHOICES = (
        ('aliyun', 'aliyun'),
        ('deepseek', 'deepseek'),
        ('minimax', 'minimax'),
        ('openai', 'openai'),
        ('custom', 'custom'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_settings')
    enabled = models.BooleanField(default=False)
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES, default='aliyun')
    api_key = models.CharField(max_length=512, blank=True, default='')
    api_base = models.CharField(max_length=512, blank=True, default='')
    model_name = models.CharField(max_length=128, blank=True, default='')
    asr_enabled = models.BooleanField(default=False)
    asr_api_key = models.CharField(max_length=512, blank=True, default='')
    asr_api_base = models.CharField(max_length=512, blank=True, default='')
    asr_model_name = models.CharField(max_length=128, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User AI Settings'
        verbose_name_plural = 'User AI Settings'

    def __str__(self):
        return f'{self.user.username}:{self.provider}:{self.enabled}'
