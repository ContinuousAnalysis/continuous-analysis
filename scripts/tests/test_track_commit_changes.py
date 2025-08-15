import sys
import os

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from track_commit_changes import process_patch_data
from unidiff import PatchSet


def test_rename_file():
    diff = """diff --git a/old.py b/new.py
--- a/old.py
+++ b/new.py
"""
    patch = PatchSet(diff)
    result = process_patch_data(patch)
    assert result["renames"] == {"new.py": "old.py"}


def test_new_file_changes():
    diff = """diff --git a/sample.py b/sample.py
index 3333333..4444444 100644
--- a/sample.py
+++ b/sample.py
@@ -0,0 +1,2 @@
+new line 1
+new line 2
"""
    patch = PatchSet(diff)
    result = process_patch_data(patch)
    assert "sample.py" in result["new_file_changes"]
    assert any(isinstance(r, tuple) for r in result["new_file_changes"]["sample.py"])


def test_no_changes():
    diff = """diff --git a/empty.py b/empty.py
index 5555555..5555555 100644
--- a/empty.py
+++ b/empty.py
"""
    patch = PatchSet(diff)
    result = process_patch_data(patch)
    assert result["renames"] == {}
    assert result["offsets"] == {"empty.py": {}}
    assert result["new_file_changes"] == {}


def test_multiple_files():
    diff = """diff --git a/a.py b/a.py
index 1111111..2222222 100644
--- a/a.py
+++ b/a.py
@@ -0,0 +1,1 @@
+added line

diff --git a/b.py b/b.py
index 3333333..4444444 100644
--- a/b.py
+++ b/b.py
@@ -0,0 +1,2 @@
+new line 1
+new line 2
"""
    patch = PatchSet(diff)
    result = process_patch_data(patch)
    assert "a.py" in result["new_file_changes"]
    assert "b.py" in result["new_file_changes"]


def test_multiple_hunks():
    diff = """diff --git a/c.py b/c.py
index 5555555..6666666 100644
--- a/c.py
+++ b/c.py
@@ -2,0 +2,2 @@
+new line 1
+new line 2
@@ -3,2 +5,2 @@
-old line 3
+new line 3
-old line 4
+new line 4
@@ -10,0 +12,2 @@
+new line 5
+new line 6
"""
    patch = PatchSet(diff)
    result = process_patch_data(patch)
    assert result["offsets"]["c.py"] == {2: 2, 3: 2, 10: 4}


def test_multiple_files_multiple_hunks():
    diff = """diff --git a/d.py b/d.py
index 7777777..8888888 100644
--- a/d.py
+++ b/d.py
@@ -0,0 +1,2 @@
+new line 1
+new line 2
@@ -5,2 +7,0 @@
-old line 3
-old line 4

diff --git a/a.py b/a.py
index 1111111..2222222 100644
--- a/a.py
+++ b/a.py
@@ -0,0 +1,2 @@
+new line 1
+new line 2
@@ -3,2 +5,2 @@
-old line 3
+new line 3
-old line 4
+new line 4
"""
    patch = PatchSet(diff)
    result = process_patch_data(patch)
    assert result["offsets"]["a.py"] == {0: 2, 3: 2}
    assert result["offsets"]["d.py"] == {0: 2, 5: 0}
