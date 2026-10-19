import getpass
import socket
import sys
import argparse

from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


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
    parser.add_argument("--vfs", default=None, help="путь к расположению VFS")
    parser.add_argument("--script", default=None, help="путь к стартовому скрипту")
    return parser.parse_args()

def run_command(command, args):
    """Выполнить команду и вернуть текст, который нужно вывести в лог."""
    if command == "ls":
        return "ls: вызвана с аргументами " + str(args)
    elif command == "cd" and len(args) == 1:
        return "cd: вызвана с аргументами " + str(args)
    elif command == "cd" and len(args) > 1:
        return "Ошибка: cd не принмает более одного аргумента "
    else:
        return "Ошибка: команда не найдена: " + command


class MainWindow(QMainWindow):
    """Главное окно эмулятора: лог диалога и строка ввода."""

    def __init__(self, vfs_path=None, script_path=None):
        super().__init__()

        self.setWindowTitle(make_title())
        self.resize(700, 450)

        self.vfs_path = vfs_path
        self.script_path = script_path

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

        if self.script_path:
            self.run_script(self.script_path)

    def process_line(self, line):
        """Показать ввод, выполнить одну команду и вывести результат."""
        self.log.append("> " + line)
        command, args = parse_command(line)
        if command is None:
            return
        if command == "exit":
            self.close()
            return
        result = run_command(command, args)
        self.log.append(result)

    def handle_input(self):
        """Обработать нажатие Enter в поле ввода."""
        line = self.input_field.text()
        self.input_field.clear()
        self.process_line(line)

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
                self.process_line(line)
            except Exception as error:
                self.log.append(f"Ошибка выполнения строки скрипта: {error}")

def main():
    """Запустить приложение эмулятора."""
    args = parse_args()
    app = QApplication(sys.argv)
    window = MainWindow(vfs_path=args.vfs, script_path=args.script)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
