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

    def setUp(self):
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

    def setUp(self):
        super().setUp()
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
        self.assertEqual(self.vfs.listdir(".."), ["docs/", "projects/", "readme.txt"])
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
