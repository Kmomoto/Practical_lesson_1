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

    def _resolve(self, path):
        """Разобрать путь (абсолютный или относительный) по узлам дерева.

        Возвращает пару: список имён от корня и список узлов от корня до
        найденного (узлов на один больше, чем имён). Поддерживаются '.' и
        '..'; '..' в корне остаётся в корне.
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
        return names, nodes

    def _lookup(self, path):
        """Найти узел по пути: пара (список имён от корня, узел)."""
        names, nodes = self._resolve(path)
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

    def isdir(self, path):
        """True, если путь существует и это каталог."""
        try:
            return self._lookup(path)[1].is_dir
        except VFSError:
            return False

    def _remove_empty_dir(self, names, nodes, shown):
        """Удалить пустой каталог; names и nodes - его разобранный путь."""
        if not names:
            raise VFSError("нельзя удалить корневой каталог: " + shown)
        if not nodes[-1].is_dir:
            raise VFSError("не является каталогом: " + shown)
        if nodes[-1].children:
            raise VFSError("каталог не пуст: " + shown)
        if self.cwd[: len(names)] == names:
            raise VFSError(
                "нельзя удалить текущий каталог или его родителя: " + shown
            )
        del nodes[-2].children[names[-1]]

    def rmdir(self, path, parents=False):
        """Удалить пустой каталог (как rmdir [-p] путь).

        С parents=True после него удаляются и опустевшие родители; цепочка
        прерывается ошибкой на первом каталоге, который удалить нельзя.
        """
        names, nodes = self._resolve(path)
        self._remove_empty_dir(names, nodes, path)
        if parents:
            for depth in range(len(names) - 1, 0, -1):
                shown = "/" + "/".join(names[:depth])
                self._remove_empty_dir(names[:depth], nodes[: depth + 1], shown)

    def move(self, src, dst):
        """Переместить или переименовать файл либо каталог (как mv src dst).

        Если dst - существующий каталог, src помещается внутрь него.
        Существующий файл заменяется, пустой каталог тоже; непустой - нет.
        """
        s_names, s_nodes = self._resolve(src)
        if not s_names:
            raise VFSError("нельзя переместить корневой каталог: " + src)
        node = s_nodes[-1]
        s_parent = s_nodes[-2]
        if node.is_dir and self.cwd[: len(s_names)] == s_names:
            raise VFSError(
                "нельзя переместить текущий каталог или его родителя: " + src
            )

        try:
            d_names, d_nodes = self._resolve(dst)
        except VFSError:
            d_names = None

        if d_names is not None and d_nodes[-1].is_dir:
            # dst - существующий каталог: перемещаем внутрь него
            t_names = d_names
            t_parent = d_nodes[-1]
            t_name = s_names[-1]
            shown = dst.rstrip("/") + "/" + t_name
        elif d_names is not None:
            # dst - существующий файл: он будет заменён
            t_names = d_names[:-1]
            t_parent = d_nodes[-2]
            t_name = d_names[-1]
            shown = dst
        else:
            # dst не существует: это новое имя внутри существующего каталога
            trimmed = dst.rstrip("/")
            head, _, tail = trimmed.rpartition("/")
            if tail in ("", ".", ".."):
                raise VFSError("нет такого файла или каталога: " + dst)
            if head:
                parent_path = head
            elif trimmed.startswith("/"):
                parent_path = "/"
            else:
                parent_path = "."
            try:
                t_names, t_nodes = self._resolve(parent_path)
            except VFSError:
                raise VFSError("нет такого файла или каталога: " + dst)
            t_parent = t_nodes[-1]
            if not t_parent.is_dir:
                raise VFSError("не является каталогом: " + dst)
            t_name = tail
            shown = dst

        existing = t_parent.children.get(t_name)
        if existing is node:
            raise VFSError(src + " и " + shown + " - один и тот же объект")
        if node.is_dir and t_names[: len(s_names)] == s_names:
            raise VFSError("нельзя переместить каталог в самого себя: " + src)
        if existing is not None:
            if existing.is_dir and not node.is_dir:
                raise VFSError("нельзя заменить каталог файлом: " + shown)
            if node.is_dir and not existing.is_dir:
                raise VFSError("нельзя заменить файл каталогом: " + shown)
            if existing.is_dir:
                if existing.children:
                    raise VFSError("каталог не пуст: " + shown)
                if self.cwd[: len(t_names) + 1] == t_names + [t_name]:
                    raise VFSError(
                        "нельзя заменить текущий каталог или его родителя: "
                        + shown
                    )

        del s_parent.children[s_names[-1]]
        node.name = t_name
        t_parent.children[t_name] = node
