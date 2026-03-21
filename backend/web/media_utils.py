from pathlib import Path


def remove_stored_file(file_field):
    if not file_field or not getattr(file_field, 'name', ''):
        return

    storage = getattr(file_field, 'storage', None)
    name = getattr(file_field, 'name', '')

    if storage and name and storage.exists(name):
        storage.delete(name)
        return

    path = getattr(file_field, 'path', '')
    if path and Path(path).exists():
        Path(path).unlink()


def replace_stored_file(instance, field_name, new_file):
    current_file = getattr(instance, field_name)
    remove_stored_file(current_file)
    setattr(instance, field_name, new_file)
