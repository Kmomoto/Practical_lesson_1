"""Общие помощники для тестов."""

import os
import zipfile


def make_zip(directory, entries, name="test.zip"):
    """Создать ZIP-архив из словаря {имя записи: содержимое}.

    Имя, оканчивающееся на '/', создаёт запись о каталоге.
    """
    path = os.path.join(directory, name)
    with zipfile.ZipFile(path, "w") as archive:
        for entry, data in entries.items():
            archive.writestr(entry, data)
    return path
