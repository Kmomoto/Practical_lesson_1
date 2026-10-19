import argparse
import getpass
import socket
import sys

from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from vfs import VFS, VFSError


def make_title():
    """Собрать заголовок окна вида 'Эмулятор - [user@host]'."""
    user = getpass.getuser()
    host = socket.gethostname()
    return "Эмулятор - [" + user + "@" + host + "]"


def parse_command(line):
    """Разбить строку ввода на команду и список аргументов по пробелам."""
    parts = line.split()
    if len(parts) == 0:
        return None, []
    command = parts[0]
    args = parts[1:]
    return command, args


def parse_args():
    """Разобрать аргументы командной строки: пути к VFS и стартовому скрипту."""
    parser = argparse.ArgumentParser(description="Эмулятор языка оболочки ОС")
    parser.add_argument("--vfs", default=None, help="путь к ZIP-архиву с VFS")
    parser.add_argument("--script", default=None, help="путь к стартовому скрипту")
    return parser.parse_args()


def run_command(command, args, vfs):
    """Выполнить команду над VFS и вернуть текст для вывода в лог."""
    try:
        if command == "ls":
            if len(args) > 1:
                return "Ошибка: ls не принимает более одного аргумента"
            path = args[0] if args else None
            return "\n".join(vfs.listdir(path))
        if command == "cd":
            if len(args) > 1:
                return "Ошибка: cd не принимает более одного аргумента"
            vfs.chdir(args[0] if args else "/")
            return ""
    except VFSError as error:
        return "Ошибка: " + command + ": " + str(error)
    return "Ошибка: команда не найдена: " + command


class MainWindow(QMainWindow):
    """Главное окно эмулятора: лог диалога и строка ввода."""

    def __init__(self, vfs_path=None, script_path=None):
        super().__init__()

        self.setWindowTitle(make_title())
        self.resize(700, 450)

        self.vfs_path = vfs_path
        self.script_path = script_path
        self.vfs = VFS()

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.input_field = QLineEdit()
        self.input_field.returnPressed.connect(self.handle_input)

        layout = QVBoxLayout()
        layout.addWidget(self.log)
        layout.addWidget(self.input_field)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.log.append("Эмулятор запущен. Команды: ls, cd, exit")
        self.log.append(f"[config] vfs={self.vfs_path}")
        self.log.append(f"[config] script={self.script_path}")

        self.load_vfs()

    def load_vfs(self):
        """Загрузить VFS из ZIP-архива; при ошибке остаётся пустая VFS."""
        if not self.vfs_path:
            self.log.append("VFS не указана, используется пустая VFS")
            return
        try:
            self.vfs = VFS.from_zip(self.vfs_path)
        except VFSError as error:
            self.log.append(f"Ошибка: не удалось загрузить VFS: {error}")
            self.log.append("Используется пустая VFS")
            return
        self.log.append(f"VFS загружена из {self.vfs_path}")

    def process_line(self, line):
        """Показать ввод, выполнить одну команду и вывести результат.

        Возвращает False, если команда завершает работу эмулятора (exit).
        """
        self.log.append(self.vfs.pwd() + "> " + line)
        command, args = parse_command(line)
        if command is None:
            return True
        if command == "exit":
            self.close()
            return False
        result = run_command(command, args, self.vfs)
        if result:
            self.log.append(result)
        return True

    def handle_input(self):
        """Обработать нажатие Enter в поле ввода."""
        line = self.input_field.text()
        self.input_field.clear()
        self.process_line(line)

    def run_startup_script(self):
        """Выполнить стартовый скрипт, если он указан в параметрах."""
        if self.script_path:
            self.run_script(self.script_path)

    def run_script(self, path):
        """Выполнить стартовый скрипт построчно, имитируя диалог с пользователем."""
        try:
            with open(path, encoding="utf-8") as script_file:
                lines = script_file.readlines()
        except OSError as error:
            self.log.append(f"Ошибка: не удалось открыть скрипт: {error}")
            return

        for raw_line in lines:
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if stripped == "" or stripped.startswith("#"):
                continue
            try:
                if not self.process_line(line):
                    break
            except Exception as error:
                self.log.append(f"Ошибка выполнения строки скрипта: {error}")


def main():
    """Запустить приложение эмулятора."""
    args = parse_args()
    app = QApplication(sys.argv)
    window = MainWindow(vfs_path=args.vfs, script_path=args.script)
    window.show()
    window.run_startup_script()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
