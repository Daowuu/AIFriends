from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0006_alter_useraisettings_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraisettings',
            name='asr_api_base',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
        migrations.AddField(
            model_name='useraisettings',
            name='asr_api_key',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
        migrations.AddField(
            model_name='useraisettings',
            name='asr_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='useraisettings',
            name='asr_model_name',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
