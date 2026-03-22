from django.db import migrations, models


def populate_character_sort_order(apps, schema_editor):
    Character = apps.get_model('web', 'Character')
    characters = list(Character.objects.all().order_by('-updated_at', '-id'))
    for index, character in enumerate(characters):
        Character.objects.filter(pk=character.pk).update(sort_order=index)


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0013_single_instance_local_runtime'),
    ]

    operations = [
        migrations.AddField(
            model_name='character',
            name='sort_order',
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.RunPython(populate_character_sort_order, migrations.RunPython.noop),
    ]
