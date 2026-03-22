from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0015_werewolfgame_werewolfseat_alter_character_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='werewolfseat',
            name='identity',
            field=models.CharField(
                blank=True,
                choices=[
                    ('wolf', 'wolf'),
                    ('seer', 'seer'),
                    ('witch', 'witch'),
                    ('hunter', 'hunter'),
                    ('villager', 'villager'),
                ],
                default='',
                max_length=16,
            ),
        ),
    ]
