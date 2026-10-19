"""Тесты: parse_command, run_command, окно эмулятора, конфигурация и VFS."""

import os
import socket
import getpass
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main
from helpers import make_zip
from vfs import VFS


app = QApplication.instance() or QApplication([])


class TestMakeTitle(unittest.TestCase):

    def test_format(self):
        expected = (
            "Эмулятор - ["
            + getpass.getuser()
            + "@"
            + socket.gethostname()
            + "]"
        )
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

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.vfs = VFS.from_zip(
            make_zip(tmp.name, {"docs/a.txt": "a", "readme.txt": "r"})
        )

    def test_ls(self):
        self.assertEqual(
            main.run_command("ls", [], self.vfs), "docs/\nreadme.txt"
        )

    def test_ls_with_path(self):
        self.assertEqual(main.run_command("ls", ["docs"], self.vfs), "a.txt")

    def test_ls_missing_path(self):
        self.assertEqual(
            main.run_command("ls", ["nope"], self.vfs),
            "Ошибка: ls: нет такого файла или каталога: nope",
        )

    def test_ls_too_many_args(self):
        self.assertEqual(
            main.run_command("ls", ["a", "b"], self.vfs),
            "Ошибка: ls не принимает более одного аргумента",
        )

    def test_cd_changes_directory(self):
        self.assertEqual(main.run_command("cd", ["docs"], self.vfs), "")
        self.assertEqual(self.vfs.pwd(), "/docs")

    def test_cd_without_args_goes_to_root(self):
        main.run_command("cd", ["docs"], self.vfs)
        main.run_command("cd", [], self.vfs)
        self.assertEqual(self.vfs.pwd(), "/")

    def test_cd_to_file(self):
        self.assertEqual(
            main.run_command("cd", ["readme.txt"], self.vfs),
            "Ошибка: cd: не является каталогом: readme.txt",
        )

    def test_cd_too_many_args(self):
        self.assertEqual(
            main.run_command("cd", ["a", "b"], self.vfs),
            "Ошибка: cd не принимает более одного аргумента",
        )

    def test_pwd(self):
        self.assertEqual(main.run_command("pwd", [], self.vfs), "/")
        main.run_command("cd", ["docs"], self.vfs)
        self.assertEqual(main.run_command("pwd", [], self.vfs), "/docs")

    def test_pwd_with_args(self):
        self.assertEqual(
            main.run_command("pwd", ["x"], self.vfs),
            "Ошибка: pwd не принимает аргументов",
        )

    def test_history_all(self):
        history = ["ls", "cd docs", "history"]
        self.assertEqual(
            main.run_command("history", [], self.vfs, history),
            "1 ls\n2 cd docs\n3 history",
        )

    def test_history_last_n_keeps_numbers(self):
        history = ["ls", "cd docs", "pwd", "history 2"]
        self.assertEqual(
            main.run_command("history", ["2"], self.vfs, history),
            "3 pwd\n4 history 2",
        )

    def test_history_zero_and_too_large(self):
        history = ["ls", "history 0"]
        self.assertEqual(main.run_command("history", ["0"], self.vfs, history), "")
        self.assertEqual(
            main.run_command("history", ["100"], self.vfs, history),
            "1 ls\n2 history 0",
        )

    def test_history_without_list_is_empty(self):
        self.assertEqual(main.run_command("history", [], self.vfs), "")

    def test_history_errors(self):
        self.assertEqual(
            main.run_command("history", ["abc"], self.vfs, ["x"]),
            "Ошибка: history: неверный аргумент: abc",
        )
        self.assertEqual(
            main.run_command("history", ["-1"], self.vfs, ["x"]),
            "Ошибка: history: неверный аргумент: -1",
        )
        self.assertEqual(
            main.run_command("history", ["1", "2"], self.vfs, ["x"]),
            "Ошибка: history не принимает более одного аргумента",
        )

    def test_unknown_command(self):
        self.assertEqual(
            main.run_command("abc", [], self.vfs),
            "Ошибка: команда не найдена: abc",
        )


class WindowTestCase(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.windows = []
        self.addCleanup(self.close_windows)

    def close_windows(self):
        for window in self.windows:
            window.close()

    def make_window(self, **kwargs):
        window = main.MainWindow(**kwargs)
        window.show()
        window.run_startup_script()
        self.windows.append(window)
        return window

    def make_vfs(self):
        return make_zip(
            self.tmp,
            {"docs/guide.txt": "g", "docs/manual/intro.txt": "i", "readme.txt": "r"},
        )

    def write_script(self, text):
        path = os.path.join(self.tmp, "script.txt")
        with open(path, "w", encoding="utf-8") as script_file:
            script_file.write(text)
        return path

    @staticmethod
    def type_command(window, text):
        window.input_field.setText(text)
        window.input_field.returnPressed.emit()

    @staticmethod
    def log_lines(window):
        return window.log.toPlainText().split("\n")


class TestMainWindow(WindowTestCase):

    def setUp(self):
        super().setUp()
        self.window = self.make_window()

    def test_window_title(self):
        self.assertEqual(self.window.windowTitle(), main.make_title())

    def test_unknown_command_output(self):
        self.type_command(self.window, "abc")
        self.assertEqual(
            self.log_lines(self.window)[-2:],
            ["/> abc", "Ошибка: команда не найдена: abc"],
        )

    def test_empty_vfs_when_not_specified(self):
        self.assertIn("VFS не указана", self.window.log.toPlainText())
        self.type_command(self.window, "ls")
        self.assertEqual(self.log_lines(self.window)[-1], "/> ls")

    def test_exit_closes_window(self):
        self.assertTrue(self.window.isVisible())
        self.type_command(self.window, "exit")
        self.assertFalse(self.window.isVisible())


class TestWindowWithVFS(WindowTestCase):

    def setUp(self):
        super().setUp()
        self.window = self.make_window(vfs_path=self.make_vfs())

    def test_vfs_loaded_message(self):
        self.assertIn("VFS загружена из", self.window.log.toPlainText())

    def test_ls_output(self):
        self.type_command(self.window, "ls")
        self.assertEqual(
            self.log_lines(self.window)[-3:],
            ["/> ls", "docs/", "readme.txt"],
        )

    def test_prompt_shows_current_directory(self):
        self.type_command(self.window, "cd docs/manual")
        self.type_command(self.window, "ls")
        self.assertEqual(
            self.log_lines(self.window)[-2:],
            ["/docs/manual> ls", "intro.txt"],
        )

    def test_cd_error_is_logged(self):
        self.type_command(self.window, "cd readme.txt")
        self.assertEqual(
            self.log_lines(self.window)[-2:],
            ["/> cd readme.txt", "Ошибка: cd: не является каталогом: readme.txt"],
        )


class TestWindowHistory(WindowTestCase):

    def setUp(self):
        super().setUp()
        self.window = self.make_window(vfs_path=self.make_vfs())

    def test_pwd_output(self):
        self.type_command(self.window, "cd docs")
        self.type_command(self.window, "pwd")
        self.assertEqual(
            self.log_lines(self.window)[-2:], ["/docs> pwd", "/docs"]
        )

    def test_history_records_commands_including_errors_and_itself(self):
        self.type_command(self.window, "ls")
        self.type_command(self.window, "abc")
        self.type_command(self.window, "")
        self.type_command(self.window, "   ")
        self.type_command(self.window, "cd   docs")
        self.type_command(self.window, "history")
        self.assertEqual(
            self.log_lines(self.window)[-5:],
            ["/docs> history", "1 ls", "2 abc", "3 cd docs", "4 history"],
        )

    def test_history_last_n(self):
        for command in ("ls", "pwd", "cd docs", "history 2"):
            self.type_command(self.window, command)
        self.assertEqual(
            self.log_lines(self.window)[-2:], ["3 cd docs", "4 history 2"]
        )

    def test_script_commands_are_in_history(self):
        script = self.write_script("ls\npwd\n")
        window = self.make_window(vfs_path=self.make_vfs(), script_path=script)
        self.assertEqual(window.history, ["ls", "pwd"])


class TestWindowConfig(WindowTestCase):

    def test_config_is_printed(self):
        window = self.make_window(vfs_path=self.make_vfs(), script_path=None)
        text = window.log.toPlainText()
        self.assertIn("[config] vfs=" + window.vfs_path, text)
        self.assertIn("[config] script=None", text)

    def test_missing_archive_keeps_emulator_working(self):
        window = self.make_window(vfs_path=os.path.join(self.tmp, "no.zip"))
        self.assertIn("Ошибка: не удалось загрузить VFS", window.log.toPlainText())
        self.type_command(window, "ls")
        self.assertEqual(self.log_lines(window)[-1], "/> ls")

    def test_broken_archive_keeps_emulator_working(self):
        path = os.path.join(self.tmp, "broken.zip")
        with open(path, "w") as broken:
            broken.write("not a zip")
        window = self.make_window(vfs_path=path)
        self.assertIn("Ошибка: не удалось загрузить VFS", window.log.toPlainText())
        self.assertIn("Используется пустая VFS", window.log.toPlainText())

    def test_missing_script(self):
        window = self.make_window(script_path=os.path.join(self.tmp, "no.txt"))
        self.assertIn("не удалось открыть скрипт", window.log.toPlainText())

    def test_script_runs_commands_and_skips_comments(self):
        script = self.write_script("# комментарий\n\ncd docs\nls\nabc\n")
        window = self.make_window(vfs_path=self.make_vfs(), script_path=script)
        self.assertEqual(
            self.log_lines(window)[-5:],
            [
                "/docs> ls",
                "guide.txt",
                "manual/",
                "/docs> abc",
                "Ошибка: команда не найдена: abc",
            ],
        )
        self.assertIn("Ошибка: команда не найдена: abc", window.log.toPlainText())

    def test_script_stops_after_exit(self):
        script = self.write_script("ls\nexit\ncd docs\n")
        window = self.make_window(vfs_path=self.make_vfs(), script_path=script)
        self.assertFalse(window.isVisible())
        self.assertNotIn("cd docs", window.log.toPlainText())
        self.assertEqual(window.vfs.pwd(), "/")


if __name__ == "__main__":
    unittest.main(verbosity=2)
