import os
import socket
import getpass
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import main


app = QApplication.instance() or QApplication([])


class TestMakeTitle(unittest.TestCase):

    def test_format(self):
        expected = "Эмулятор - [" + getpass.getuser() + "@" + socket.gethostname() + "]"
        self.assertEqual(main.make_title(), expected)

    def test_starts_with_name(self):
        self.assertTrue(main.make_title().startswith("Эмулятор - ["))

    def test_ends_with_bracket(self):
        self.assertTrue(main.make_title().endswith("]"))

    def test_contains_user_and_host(self):
        title = main.make_title()
        self.assertIn(getpass.getuser(), title)
        self.assertIn(socket.gethostname(), title)
        self.assertIn("@", title)


class TestRunCommand(unittest.TestCase):

    def test_ls_without_args(self):
        self.assertEqual(main.run_command("ls", []), "ls: вызвана с аргументами []")

    def test_ls_with_one_arg(self):
        self.assertEqual(main.run_command("ls", ["-l"]), "ls: вызвана с аргументами ['-l']")

    def test_ls_with_many_args(self):
        self.assertEqual(
            main.run_command("ls", ["-l", "-a", "/home"]),
            "ls: вызвана с аргументами ['-l', '-a', '/home']",
        )

    def test_cd_without_args(self):
        self.assertEqual(main.run_command("cd", []), "cd: вызвана с аргументами []")

    def test_cd_with_arg(self):
        self.assertEqual(main.run_command("cd", ["/usr"]), "cd: вызвана с аргументами ['/usr']")

    def test_unknown_command(self):
        self.assertEqual(main.run_command("abc", []), "Ошибка: команда не найдена: abc")

    def test_unknown_command_with_args(self):
        self.assertEqual(
            main.run_command("mkdir", ["test"]), "Ошибка: команда не найдена: mkdir"
        )

    def test_command_is_case_sensitive(self):
        # "LS" - это не "ls", как и в настоящей оболочке
        self.assertEqual(main.run_command("LS", []), "Ошибка: команда не найдена: LS")

    def test_exit_is_not_handled_here(self):
        # exit обрабатывается в окне, а не в run_command
        self.assertEqual(main.run_command("exit", []), "Ошибка: команда не найдена: exit")


class TestMainWindow(unittest.TestCase):

    def setUp(self):
        self.window = main.MainWindow()
        self.window.show()

    def tearDown(self):
        self.window.close()

    def type_command(self, text):
        # Имитируем ввод строки пользователем и нажатие Enter
        self.window.input_field.setText(text)
        self.window.input_field.returnPressed.emit()

    def log_lines(self):
        return self.window.log.toPlainText().split("\n")

    def test_window_title(self):
        self.assertEqual(self.window.windowTitle(), main.make_title())

    def test_start_message(self):
        self.assertEqual(self.log_lines(), ["Эмулятор запущен. Команды: ls, cd, exit"])

    def test_log_is_read_only(self):
        self.assertTrue(self.window.log.isReadOnly())

    def test_input_field_is_empty_at_start(self):
        self.assertEqual(self.window.input_field.text(), "")

    def test_ls_output(self):
        self.type_command("ls")
        self.assertEqual(self.log_lines()[-2:], ["> ls", "ls: вызвана с аргументами []"])

    def test_ls_with_args_output(self):
        self.type_command("ls -l -a")
        self.assertEqual(
            self.log_lines()[-2:], ["> ls -l -a", "ls: вызвана с аргументами ['-l', '-a']"]
        )

    def test_cd_output(self):
        self.type_command("cd /home")
        self.assertEqual(
            self.log_lines()[-2:], ["> cd /home", "cd: вызвана с аргументами ['/home']"]
        )

    def test_unknown_command_output(self):
        self.type_command("abc")
        self.assertEqual(self.log_lines()[-2:], ["> abc", "Ошибка: команда не найдена: abc"])

    def test_extra_spaces_are_ignored(self):
        self.type_command("  ls    -l   ")
        self.assertEqual(self.log_lines()[-1], "ls: вызвана с аргументами ['-l']")

    def test_input_is_cleared_after_enter(self):
        self.type_command("ls")
        self.assertEqual(self.window.input_field.text(), "")

    def test_empty_line_gives_no_result(self):
        before = len(self.log_lines())
        self.type_command("")
        after = self.log_lines()

        self.assertEqual(len(after), before + 1)
        self.assertEqual(after[-1].strip(), ">")

    def test_spaces_only_gives_no_result(self):
        before = len(self.log_lines())
        self.type_command("     ")
        after = self.log_lines()
        self.assertEqual(len(after), before + 1)
        self.assertEqual(after[-1].strip(), ">")

    def test_several_commands_in_a_row(self):
        self.type_command("ls")
        self.type_command("cd")
        self.type_command("xyz")
        self.assertEqual(
            self.log_lines()[1:],
            [
                "> ls",
                "ls: вызвана с аргументами []",
                "> cd",
                "cd: вызвана с аргументами []",
                "> xyz",
                "Ошибка: команда не найдена: xyz",
            ],
        )

    def test_exit_closes_window(self):
        self.assertTrue(self.window.isVisible())
        self.type_command("exit")
        self.assertFalse(self.window.isVisible())

    def test_exit_with_spaces_closes_window(self):
        self.type_command("   exit  ")
        self.assertFalse(self.window.isVisible())

    def test_exit_with_args_closes_window(self):
        self.type_command("exit 0")
        self.assertFalse(self.window.isVisible())


if __name__ == "__main__":
    unittest.main(verbosity=2)
