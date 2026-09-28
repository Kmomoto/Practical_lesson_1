"""Тесты для этапа 1: parse_command, run_command и окно."""

import os
import socket
import getpass
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main


app = QApplication.instance() or QApplication([])


class TestMakeTitle(unittest.TestCase):

    def test_format(self):
        expected = "Эмулятор - [" + getpass.getuser() + "@" + socket.gethostname() + "]"
        self.assertEqual(main.make_title(), expected)


class TestParseCommand(unittest.TestCase):

    def test_command_without_args(self):
        command, args = main.parse_command("ls")
        self.assertEqual(command, "ls")
        self.assertEqual(args, [])

    def test_command_with_args(self):
        command, args = main.parse_command("cd /home")
        self.assertEqual(command, "cd")
        self.assertEqual(args, ["/home"])

    def test_empty_line(self):
        command, args = main.parse_command("")
        self.assertIsNone(command)


class TestRunCommand(unittest.TestCase):

    def test_ls(self):
        self.assertEqual(main.run_command("ls", ["-l"]), "ls: вызвана с аргументами ['-l']")

    def test_cd(self):
        self.assertEqual(main.run_command("cd", ["/home"]), "cd: вызвана с аргументами ['/home']")

    def test_unknown_command(self):
        self.assertEqual(main.run_command("abc", []), "Ошибка: команда не найдена: abc")


class TestMainWindow(unittest.TestCase):

    def setUp(self):
        self.window = main.MainWindow()
        self.window.show()

    def tearDown(self):
        self.window.close()

    def type_command(self, text):
        self.window.input_field.setText(text)
        self.window.input_field.returnPressed.emit()

    def log_lines(self):
        return self.window.log.toPlainText().split("\n")

    def test_window_title(self):
        self.assertEqual(self.window.windowTitle(), main.make_title())

    def test_ls_output(self):
        self.type_command("ls -l")
        self.assertEqual(self.log_lines()[-2:], ["> ls -l", "ls: вызвана с аргументами ['-l']"])

    def test_exit_closes_window(self):
        self.assertTrue(self.window.isVisible())
        self.type_command("exit")
        self.assertFalse(self.window.isVisible())


if __name__ == "__main__":
    unittest.main(verbosity=2)
