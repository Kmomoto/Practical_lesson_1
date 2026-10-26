"""Виртуальная файловая система (VFS), целиком хранящаяся в памяти.

Источник VFS - ZIP-архив. Архив только читается: на диск ничего
не распаковывается, и сам архив не изменяется.
"""

import base64
import zipfile
import zlib


NO_SUCH = "нет такого файла или каталога: "
NOT_DIR = "не является каталогом: "
NAME_CLASH = "в архиве файл и каталог с одним именем: "


def split_entry_name(name):
    """Разбить имя записи архива на части, отбросив пустые и '.'."""
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise VFSError("недопустимый путь в архиве: " + name)
    return parts


def parent_path(trimmed, head):
    """Путь к каталогу, в котором лежит последний элемент trimmed."""
    if head:
        return head
    return "/" if trimmed.startswith("/") else "."


class VFSError(Exception):
    """Ошибка работы с VFS. Текст ошибки показывается пользователю."""


class Node:
    """Узел дерева VFS: каталог (с потомками) или файл (с содержимым)."""

    def __init__(self, name, is_dir, data=b""):
        """Создать узел: имя, признак каталога и содержимое файла."""
        self.name = name
        self.is_dir = is_dir
        self.data = data
        self.children = {}


class VFS:
    """Дерево каталогов и файлов в памяти плюс текущий каталог."""

    def __init__(self):
        """Создать пустую VFS с корнем и текущим каталогом /."""
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
        parts = split_entry_name(name)
        if not parts:
            return
        dirs = parts if is_dir else parts[:-1]
        node = self._make_dirs(dirs, name)
        if not is_dir:
            self._add_file(node, parts[-1], data, name)

    def _make_dirs(self, dirs, name):
        """Создать недостающие каталоги цепочки и вернуть последний."""
        node = self.root
        for part in dirs:
            child = node.children.get(part)
            if child is None:
                child = Node(part, True)
                node.children[part] = child
            elif not child.is_dir:
                raise VFSError(NAME_CLASH + name)
            node = child
        return node

    @staticmethod
    def _add_file(node, file_name, data, name):
        """Положить файл в каталог node; name - исходное имя записи."""
        existing = node.children.get(file_name)
        if existing is not None and existing.is_dir:
            raise VFSError(NAME_CLASH + name)
        node.children[file_name] = Node(file_name, False, data)

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
                raise VFSError(NOT_DIR + path)
            if part == "..":
                if names:
                    names.pop()
                    nodes.pop()
                continue
            child = nodes[-1].children.get(part)
            if child is None:
                raise VFSError(NO_SUCH + path)
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
            raise VFSError(NOT_DIR + path)
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
            raise VFSError(NOT_DIR + shown)
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
        node = s_nodes[-1]
        self._check_movable(src, s_names, node)
        t_names, t_parent, t_name, shown = self._find_target(s_names[-1], dst)
        existing = t_parent.children.get(t_name)
        if existing is node:
            raise VFSError(src + " и " + shown + " - один и тот же объект")
        if node.is_dir and t_names[: len(s_names)] == s_names:
            raise VFSError("нельзя переместить каталог в самого себя: " + src)
        self._check_replace(existing, node, t_names, t_name, shown)
        del s_nodes[-2].children[s_names[-1]]
        node.name = t_name
        t_parent.children[t_name] = node

    def _check_movable(self, src, s_names, node):
        """Проверить, что источник можно перемещать (не корень и не cwd)."""
        if not s_names:
            raise VFSError("нельзя переместить корневой каталог: " + src)
        if node.is_dir and self.cwd[: len(s_names)] == s_names:
            raise VFSError(
                "нельзя переместить текущий каталог или его родителя: " + src
            )

    def _find_target(self, src_name, dst):
        """Определить цель mv: (имена каталога, каталог, новое имя, путь)."""
        try:
            d_names, d_nodes = self._resolve(dst)
        except VFSError:
            return self._target_new_name(dst)
        if d_nodes[-1].is_dir:
            shown = dst.rstrip("/") + "/" + src_name
            return d_names, d_nodes[-1], src_name, shown
        return d_names[:-1], d_nodes[-2], d_names[-1], dst

    def _target_new_name(self, dst):
        """dst не существует: это новое имя внутри существующего каталога."""
        trimmed = dst.rstrip("/")
        head, _, tail = trimmed.rpartition("/")
        if tail in ("", ".", ".."):
            raise VFSError(NO_SUCH + dst)
        try:
            t_names, t_nodes = self._resolve(parent_path(trimmed, head))
        except VFSError:
            raise VFSError(NO_SUCH + dst)
        if not t_nodes[-1].is_dir:
            raise VFSError(NOT_DIR + dst)
        return t_names, t_nodes[-1], tail, dst

    def _check_replace(self, existing, node, t_names, t_name, shown):
        """Проверить, можно ли заменить existing перемещаемым узлом node."""
        if existing is None:
            return
        if existing.is_dir and not node.is_dir:
            raise VFSError("нельзя заменить каталог файлом: " + shown)
        if node.is_dir and not existing.is_dir:
            raise VFSError("нельзя заменить файл каталогом: " + shown)
        if not existing.is_dir:
            return
        if existing.children:
            raise VFSError("каталог не пуст: " + shown)
        if self.cwd[: len(t_names) + 1] == t_names + [t_name]:
            raise VFSError(
                "нельзя заменить текущий каталог или его родителя: " + shown
            )
