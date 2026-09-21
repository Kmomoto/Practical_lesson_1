"""Эмулятор языка оболочки ОС — этап 1 (Вариант №25).

Минимальный прототип: окно с логом и полем ввода. Команды ls и cd
пока являются заглушками — они просто печатают своё имя и аргументы.
"""

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


def run_command(command, args):
    """Выполнить команду и вернуть текст, который нужно вывести в лог."""
    if command == "ls":
        return "ls: вызвана с аргументами " + str(args)
    elif command == "cd":
        return "cd: вызвана с аргументами " + str(args)
    else:
        return "Ошибка: команда не найдена: " + command


class MainWindow(QMainWindow):
    """Главное окно эмулятора: лог диалога и строка ввода."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle(make_title())
        self.resize(700, 450)

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

    def handle_input(self):
        """Обработать нажатие Enter: показать ввод и результат команды."""
        line = self.input_field.text()
        self.input_field.clear()
        self.log.append("> " + line)

        command, args = parse_command(line)
        if command is None:
            return

        if command == "exit":
            self.close()
            return

        result = run_command(command, args)
        self.log.append(result)


def main():
    """Запустить приложение эмулятора."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
