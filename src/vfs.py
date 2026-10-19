"""Виртуальная файловая система (VFS), целиком хранящаяся в памяти.

Источник VFS - ZIP-архив. Архив только читается: на диск ничего
не распаковывается, и сам архив не изменяется.
"""

import base64
import zipfile
import zlib


class VFSError(Exception):
    """Ошибка работы с VFS. Текст ошибки показывается пользователю."""


class Node:
    """Узел дерева VFS: каталог (с потомками) или файл (с содержимым)."""

    def __init__(self, name, is_dir, data=b""):
        self.name = name
        self.is_dir = is_dir
        self.data = data
        self.children = {}


class VFS:
    """Дерево каталогов и файлов в памяти плюс текущий каталог."""

    def __init__(self):
        self.root = Node("", True)
        self.cwd = []

    @classmethod
    def from_zip(cls, path):
        """Прочитать ZIP-архив в память и построить по нему дерево VFS."""
        vfs = cls()
        try:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    data = b"" if info.is_dir() else archive.read(info)
                    vfs._add_entry(info.filename, info.is_dir(), data)
        except (
            OSError,
            zipfile.BadZipFile,
            zlib.error,
            EOFError,
            NotImplementedError,
            RuntimeError,
        ) as error:
            raise VFSError("ошибка чтения архива: " + str(error))
        return vfs

    def _add_entry(self, name, is_dir, data):
        """Добавить в дерево запись архива, создав промежуточные каталоги."""
        parts = [p for p in name.split("/") if p not in ("", ".")]
        if ".." in parts:
            raise VFSError("недопустимый путь в архиве: " + name)
        if not parts:
            return

        node = self.root
        dirs = parts if is_dir else parts[:-1]
        for part in dirs:
            child = node.children.get(part)
            if child is None:
                child = Node(part, True)
                node.children[part] = child
            elif not child.is_dir:
                raise VFSError("в архиве файл и каталог с одним именем: " + name)
            node = child

        if not is_dir:
            existing = node.children.get(parts[-1])
            if existing is not None and existing.is_dir:
                raise VFSError("в архиве файл и каталог с одним именем: " + name)
            node.children[parts[-1]] = Node(parts[-1], False, data)

    def _lookup(self, path):
        """Найти узел по пути (абсолютному или относительному).

        Возвращает пару: список имён от корня и сам узел. Поддерживаются
        '.' и '..'; '..' в корне остаётся в корне.
        """
        names = [] if path.startswith("/") else list(self.cwd)
        nodes = [self.root]
        for name in names:
            nodes.append(nodes[-1].children[name])

        for part in path.split("/"):
            if part in ("", "."):
                continue
            if not nodes[-1].is_dir:
                raise VFSError("не является каталогом: " + path)
            if part == "..":
                if names:
                    names.pop()
                    nodes.pop()
                continue
            child = nodes[-1].children.get(part)
            if child is None:
                raise VFSError("нет такого файла или каталога: " + path)
            names.append(part)
            nodes.append(child)
        return names, nodes[-1]

    def pwd(self):
        """Текущий каталог в виде абсолютного пути."""
        return "/" + "/".join(self.cwd)

    def listdir(self, path=None):
        """Имена содержимого каталога (у каталогов в конце '/').

        Для пути к файлу возвращается имя самого файла.
        """
        _, node = self._lookup(path or ".")
        if not node.is_dir:
            return [node.name]
        result = []
        for name in sorted(node.children):
            if node.children[name].is_dir:
                result.append(name + "/")
            else:
                result.append(name)
        return result

    def chdir(self, path):
        """Сделать каталог по указанному пути текущим."""
        names, node = self._lookup(path)
        if not node.is_dir:
            raise VFSError("не является каталогом: " + path)
        self.cwd = names

    def read_base64(self, path):
        """Содержимое файла (в том числе двоичного) в виде строки base64."""
        _, node = self._lookup(path)
        if node.is_dir:
            raise VFSError("является каталогом: " + path)
        return base64.b64encode(node.data).decode("ascii")
