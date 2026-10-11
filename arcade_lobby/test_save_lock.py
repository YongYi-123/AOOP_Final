"""SaveLock: one running copy of the arcade per save folder.

Run headless from this folder:   python -m unittest test_save_lock -v
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from save_lock import LOCK_NAME, SaveLock, SaveLockedError

HERE = os.path.dirname(os.path.abspath(__file__))
CHILD = """
import sys, time
sys.path.insert(0, {here!r})
from save_lock import SaveLock
lock = SaveLock({directory!r})
print("locked" if lock.acquire() else "busy", flush=True)
time.sleep({hold})
"""


class SaveLockTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.children = []

    def tearDown(self):
        for c in self.children:
            c.kill()
            c.wait()
            c.stdout.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def child(self, hold=30):
        proc = subprocess.Popen([sys.executable, "-c", CHILD.format(here=HERE, directory=self.dir, hold=hold)],
                                stdout=subprocess.PIPE, text=True)
        self.children.append(proc)
        return proc, proc.stdout.readline().strip()

    def test_acquire_and_release(self):
        lock = SaveLock(self.dir)
        self.assertTrue(lock.acquire())
        self.assertTrue(lock.held)
        self.assertTrue(lock.acquire())                    # already ours: still fine
        lock.release()
        lock.release()                                     # releasing twice is harmless
        self.assertFalse(lock.held)
        self.assertTrue(os.path.exists(os.path.join(self.dir, LOCK_NAME)))

    def test_a_second_holder_in_the_same_process_is_refused(self):
        first, second = SaveLock(self.dir), SaveLock(self.dir)
        self.assertTrue(first.acquire())
        self.assertFalse(second.acquire())
        self.assertFalse(second.held)
        first.release()
        self.assertTrue(second.acquire())
        second.release()

    def test_another_running_process_blocks_us_until_it_exits(self):
        proc, state = self.child()
        self.assertEqual(state, "locked")
        mine = SaveLock(self.dir)
        self.assertFalse(mine.acquire())
        proc.kill()
        proc.wait()
        for _ in range(50):                                # the OS frees the lock when the process is gone
            if mine.acquire():
                break
            time.sleep(0.05)
        self.assertTrue(mine.held)
        mine.release()

    def test_a_crashed_holder_leaves_no_stale_lock(self):
        proc, state = self.child()
        self.assertEqual(state, "locked")
        proc.kill()                                        # SIGKILL: no cleanup code runs at all
        proc.wait()
        lock = SaveLock(self.dir)
        for _ in range(50):
            if lock.acquire():
                break
            time.sleep(0.05)
        self.assertTrue(lock.held)
        lock.release()

    def test_a_child_that_starts_while_we_hold_the_lock_is_refused(self):
        mine = SaveLock(self.dir)
        self.assertTrue(mine.acquire())
        proc, state = self.child(hold=1)
        self.assertEqual(state, "busy")
        mine.release()

    def test_different_save_folders_do_not_block_each_other(self):
        other = tempfile.mkdtemp()
        try:
            a, b = SaveLock(self.dir), SaveLock(other)
            self.assertTrue(a.acquire() and b.acquire())
            a.release()
            b.release()
        finally:
            shutil.rmtree(other, ignore_errors=True)

    def test_context_manager_and_error(self):
        with SaveLock(self.dir) as held:
            self.assertTrue(held.held)
            with self.assertRaises(SaveLockedError) as ctx:
                with SaveLock(self.dir):
                    pass
            self.assertIn("already running", str(ctx.exception))
        self.assertTrue(SaveLock(self.dir).acquire())

    def test_the_lock_file_names_the_holder(self):
        proc, state = self.child()
        self.assertEqual(state, "locked")
        self.assertIn(f"pid {proc.pid}", SaveLock(self.dir).holder())

    def test_creates_the_folder_and_keeps_saves_readable(self):
        folder = os.path.join(self.dir, "new", "saves")
        lock = SaveLock(folder)
        self.assertTrue(lock.acquire())
        self.assertTrue(os.path.isdir(folder))
        with open(os.path.join(folder, "profiles.json"), "w", encoding="utf-8") as f:   # saves are unaffected
            f.write("{}")
        lock.release()

    @unittest.skipIf(sys.platform == "win32", "patches the POSIX flock call")
    def test_unsupported_file_systems_run_unprotected_with_a_warning(self):
        import save_lock
        lock = SaveLock(self.dir)
        real = save_lock.fcntl.flock
        def broken(fd, op):
            raise OSError(38, "Function not implemented")
        save_lock.fcntl.flock = broken
        try:
            self.assertTrue(lock.acquire())
            self.assertFalse(lock.supported)
        finally:
            save_lock.fcntl.flock = real
            lock.release()


if __name__ == "__main__":
    unittest.main()
