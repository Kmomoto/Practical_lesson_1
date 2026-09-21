import socket
import getpass

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QLineEdit


def make_title():
    user = getpass.getuser()
    host = socket.gethostname()
    return "Эмулятор - [" + user + "@" + host + "]"


def run_command(command, args):
    if command == "ls":
        return "ls: вызвана с аргументами " + str(args)
    elif command == "cd":
        return "cd: вызвана с аргументами " + str(args)
    else:
        return "Ошибка: команда не найдена: " + command


class MainWindow(QMainWindow):
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
        line = self.input_field.text()
        self.input_field.clear()

        self.log.append("> " + line)

        line = line.strip()
        if line == "":
            return

        parts = line.split()
        command = parts[0]
        args = parts[1:]

        if command == "exit":
            self.close()
            return

        result = run_command(command, args)
        self.log.append(result)


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
