"""Тесты для этапа 3: VFS в памяти на основе ZIP-архива."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vfs import VFS, VFSError
from helpers import make_zip


class VFSTestCase(unittest.TestCase):

    def setup_method(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def load(self, entries):
        return VFS.from_zip(make_zip(self.tmp, entries))


class TestLoading(VFSTestCase):

    def test_minimal(self):
        vfs = self.load({"a.txt": "x"})
        self.assertEqual(vfs.listdir(), ["a.txt"])

    def test_implicit_directories(self):
        vfs = self.load({"a/b/c.txt": "1"})
        self.assertEqual(vfs.listdir(), ["a/"])
        self.assertEqual(vfs.listdir("a"), ["b/"])
        self.assertEqual(vfs.listdir("a/b"), ["c.txt"])

    def test_explicit_and_empty_directories(self):
        vfs = self.load({"a/": "", "a/empty/": "", "a/f.txt": "1"})
        self.assertEqual(vfs.listdir("a"), ["empty/", "f.txt"])
        self.assertEqual(vfs.listdir("a/empty"), [])

    def test_listing_is_sorted(self):
        vfs = self.load({"b": "", "a": "", "c/": ""})
        self.assertEqual(vfs.listdir(), ["a", "b", "c/"])

    def test_nothing_is_extracted_to_disk(self):
        make_zip(self.tmp, {"a/b.txt": "x"})
        VFS.from_zip(os.path.join(self.tmp, "test.zip"))
        self.assertEqual(os.listdir(self.tmp), ["test.zip"])

    def test_missing_archive(self):
        with self.assertRaises(VFSError):
            VFS.from_zip(os.path.join(self.tmp, "no_such.zip"))

    def test_not_a_zip(self):
        path = os.path.join(self.tmp, "broken.zip")
        with open(path, "w") as broken:
            broken.write("not a zip")
        with self.assertRaises(VFSError):
            VFS.from_zip(path)

    def test_parent_reference_in_archive(self):
        with self.assertRaises(VFSError):
            self.load({"../evil.txt": "x"})

    def test_file_and_directory_with_same_name(self):
        with self.assertRaises(VFSError):
            self.load({"a": "x", "a/b": "y"})


class TestNavigation(VFSTestCase):

    def setup_method(self):
        super().setup_method()
        self.vfs = self.load({
            "readme.txt": "r",
            "docs/guide.txt": "g",
            "docs/manual/chapter1/intro.txt": "i",
            "projects/": "",
        })

    def test_starts_in_root(self):
        self.assertEqual(self.vfs.pwd(), "/")

    def test_cd_relative_and_absolute(self):
        self.vfs.chdir("docs/manual")
        self.assertEqual(self.vfs.pwd(), "/docs/manual")
        self.vfs.chdir("chapter1")
        self.assertEqual(self.vfs.pwd(), "/docs/manual/chapter1")
        self.vfs.chdir("/projects")
        self.assertEqual(self.vfs.pwd(), "/projects")

    def test_dot_and_dotdot(self):
        self.vfs.chdir("/docs/manual")
        self.vfs.chdir(".")
        self.assertEqual(self.vfs.pwd(), "/docs/manual")
        self.vfs.chdir("..")
        self.assertEqual(self.vfs.pwd(), "/docs")
        self.vfs.chdir("manual/chapter1/../..")
        self.assertEqual(self.vfs.pwd(), "/docs")

    def test_dotdot_above_root_stays_in_root(self):
        self.vfs.chdir("../../..")
        self.assertEqual(self.vfs.pwd(), "/")

    def test_trailing_slash(self):
        self.vfs.chdir("docs/")
        self.assertEqual(self.vfs.pwd(), "/docs")

    def test_ls_with_paths(self):
        self.vfs.chdir("docs")
        self.assertEqual(self.vfs.listdir(), ["guide.txt", "manual/"])
        self.assertEqual(
            self.vfs.listdir(".."), ["docs/", "projects/", "readme.txt"]
        )
        self.assertEqual(self.vfs.listdir("/projects"), [])

    def test_ls_of_file(self):
        self.assertEqual(self.vfs.listdir("docs/guide.txt"), ["guide.txt"])

    def test_cd_to_missing_path(self):
        with self.assertRaises(VFSError):
            self.vfs.chdir("/no/such")

    def test_cd_to_file(self):
        with self.assertRaises(VFSError):
            self.vfs.chdir("readme.txt")

    def test_path_through_file(self):
        with self.assertRaises(VFSError):
            self.vfs.listdir("readme.txt/x")
        with self.assertRaises(VFSError):
            self.vfs.listdir("readme.txt/..")

    def test_missing_component_before_dotdot(self):
        with self.assertRaises(VFSError):
            self.vfs.chdir("missing/..")

    def test_failed_cd_keeps_current_directory(self):
        self.vfs.chdir("docs")
        with self.assertRaises(VFSError):
            self.vfs.chdir("/no/such")
        self.assertEqual(self.vfs.pwd(), "/docs")


class TestRmdir(VFSTestCase):

    def setup_method(self):
        super().setup_method()
        self.vfs = self.load({
            "a/b/c/": "",
            "full/f.txt": "x",
            "e/": "",
            "file.txt": "x",
        })

    def test_removes_empty_directory(self):
        self.vfs.rmdir("e")
        self.assertEqual(self.vfs.listdir(), ["a/", "file.txt", "full/"])

    def test_not_empty(self):
        with self.assertRaises(VFSError):
            self.vfs.rmdir("full")
        self.assertEqual(self.vfs.listdir("full"), ["f.txt"])

    def test_file_is_not_a_directory(self):
        with self.assertRaises(VFSError):
            self.vfs.rmdir("file.txt")

    def test_missing(self):
        with self.assertRaises(VFSError):
            self.vfs.rmdir("nope")

    def test_root(self):
        with self.assertRaises(VFSError):
            self.vfs.rmdir("/")
        with self.assertRaises(VFSError):
            self.vfs.rmdir("a/..")

    def test_parents_removes_whole_chain(self):
        self.vfs.rmdir("a/b/c", parents=True)
        self.assertEqual(self.vfs.listdir(), ["e/", "file.txt", "full/"])

    def test_without_parents_keeps_ancestors(self):
        self.vfs.rmdir("a/b/c")
        self.assertEqual(self.vfs.listdir("a/b"), [])

    def test_parents_stops_at_non_empty_ancestor(self):
        vfs = self.load({"d/inner/": "", "d/f.txt": "x"})
        with self.assertRaises(VFSError):
            vfs.rmdir("d/inner", parents=True)
        self.assertEqual(vfs.listdir("d"), ["f.txt"])

    def test_current_directory_and_parents_are_busy(self):
        self.vfs.chdir("a/b")
        for path in ("/a/b", ".", "..", "/a"):
            with self.assertRaises(VFSError):
                self.vfs.rmdir(path)
        self.assertEqual(self.vfs.pwd(), "/a/b")

    def test_child_of_current_directory_can_be_removed(self):
        self.vfs.chdir("a/b")
        self.vfs.rmdir("c")
        self.assertEqual(self.vfs.listdir(), [])


class TestMove(VFSTestCase):

    def setup_method(self):
        super().setup_method()
        self.vfs = self.load({
            "a.txt": "A",
            "b.txt": "B",
            "d/x.txt": "X",
            "d/sub/y.txt": "Y",
            "e/": "",
            "full/z.txt": "Z",
        })

    def test_rename_file(self):
        self.vfs.move("a.txt", "c.txt")
        self.assertEqual(
            self.vfs.listdir(), ["b.txt", "c.txt", "d/", "e/", "full/"]
        )
        self.assertEqual(self.vfs.read_base64("c.txt"), "QQ==")
        self.assertEqual(self.vfs.listdir("c.txt"), ["c.txt"])

    def test_move_file_into_directory(self):
        self.vfs.move("a.txt", "e")
        self.assertEqual(self.vfs.listdir("e"), ["a.txt"])
        self.assertNotIn("a.txt", self.vfs.listdir())

    def test_move_into_directory_with_trailing_slash(self):
        self.vfs.move("a.txt", "e/")
        self.assertEqual(self.vfs.listdir("e"), ["a.txt"])

    def test_move_with_new_name(self):
        self.vfs.move("a.txt", "e/n.txt")
        self.assertEqual(self.vfs.listdir("e"), ["n.txt"])

    def test_overwrite_file(self):
        self.vfs.move("a.txt", "b.txt")
        self.assertEqual(self.vfs.listdir()[:1], ["b.txt"])
        self.assertNotIn("a.txt", self.vfs.listdir())
        self.assertEqual(self.vfs.read_base64("b.txt"), "QQ==")

    def test_move_directory_into_directory(self):
        self.vfs.move("d/sub", "e")
        self.assertEqual(self.vfs.listdir("e"), ["sub/"])
        self.assertEqual(self.vfs.listdir("e/sub"), ["y.txt"])
        self.assertEqual(self.vfs.listdir("d"), ["x.txt"])

    def test_rename_directory(self):
        self.vfs.move("d", "dd")
        self.assertIn("dd/", self.vfs.listdir())
        self.assertNotIn("d/", self.vfs.listdir())
        self.assertEqual(self.vfs.listdir("dd/sub"), ["y.txt"])

    def test_replace_empty_directory(self):
        vfs = self.load({"p/q/": "", "r/q/": ""})
        vfs.move("p/q", "r")
        self.assertEqual(vfs.listdir("p"), [])
        self.assertEqual(vfs.listdir("r"), ["q/"])

    def test_do_not_replace_non_empty_directory(self):
        vfs = self.load({"p/q/f": "1", "r/q/g": "2"})
        with self.assertRaises(VFSError):
            vfs.move("p/q", "r")
        self.assertEqual(vfs.listdir("p"), ["q/"])
        self.assertEqual(vfs.listdir("r/q"), ["g"])

    def test_directory_over_file(self):
        with self.assertRaises(VFSError):
            self.vfs.move("d", "a.txt")

    def test_directory_into_itself(self):
        for dst in ("d/sub", "d", "d/sub/.."):
            with self.assertRaises(VFSError):
                self.vfs.move("d", dst)
        self.assertEqual(self.vfs.listdir("d"), ["sub/", "x.txt"])

    def test_same_object(self):
        with self.assertRaises(VFSError):
            self.vfs.move("a.txt", "a.txt")
        with self.assertRaises(VFSError):
            self.vfs.move("a.txt", ".")
        self.assertEqual(self.vfs.read_base64("a.txt"), "QQ==")

    def test_root(self):
        with self.assertRaises(VFSError):
            self.vfs.move("/", "e")

    def test_missing_source_and_destination_parent(self):
        with self.assertRaises(VFSError):
            self.vfs.move("nope", "e")
        with self.assertRaises(VFSError):
            self.vfs.move("a.txt", "nope/x")
        with self.assertRaises(VFSError):
            self.vfs.move("a.txt", "b.txt/x")
        self.assertIn("a.txt", self.vfs.listdir())

    def test_current_directory_and_parents_are_busy(self):
        self.vfs.chdir("d/sub")
        for src in ("/d", "..", "/d/sub", "."):
            with self.assertRaises(VFSError):
                self.vfs.move(src, "/e")
        self.assertEqual(self.vfs.pwd(), "/d/sub")

    def test_cannot_replace_current_directory(self):
        vfs = self.load({"p/q/": "", "r/q/": ""})
        vfs.chdir("r/q")
        with self.assertRaises(VFSError):
            vfs.move("/p/q", "/r")
        self.assertEqual(vfs.listdir("/p"), ["q/"])

    def test_move_inside_current_directory_tree(self):
        self.vfs.chdir("d")
        self.vfs.move("sub", "/e")
        self.assertEqual(self.vfs.listdir("/e"), ["sub/"])
        self.vfs.move("x.txt", "../e")
        self.assertEqual(self.vfs.listdir("/e"), ["sub/", "x.txt"])

    def test_isdir(self):
        self.assertTrue(self.vfs.isdir("d"))
        self.assertTrue(self.vfs.isdir("/"))
        self.assertFalse(self.vfs.isdir("a.txt"))
        self.assertFalse(self.vfs.isdir("nope"))


class TestBase64(VFSTestCase):

    def test_binary_file(self):
        vfs = self.load({"data.bin": b"\x00\x01\xff"})
        self.assertEqual(vfs.read_base64("data.bin"), "AAH/")

    def test_directory_is_not_readable(self):
        vfs = self.load({"d/": ""})
        with self.assertRaises(VFSError):
            vfs.read_base64("d")


if __name__ == "__main__":
    unittest.main(verbosity=2)
