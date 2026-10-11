"""SaveLock: lets only one running copy of the arcade use a save directory.

The save files are written atomically, but two copies of the game running at once
would each keep their own balances in memory and overwrite each other's writes
(or both settle the same unfinished NEON 21 round). So the game takes an
exclusive operating-system lock on a small lock file inside the save directory for
as long as it runs:

    POSIX (Linux, macOS, WSL)  fcntl.flock(LOCK_EX | LOCK_NB)
    Windows                    msvcrt.locking(LK_NBLCK) on the first byte

The OS drops the lock when the process ends - even if it crashes or is killed - so
there is no stale lock to clean up and no PID file to trust. The file's text (pid
and start time) is only there to tell the second copy who holds it.

Limits: it protects one save directory, not each profile separately, and only
against copies that use this class (the game's entry point). A save folder on a
network share or synced drive that does not honour file locks cannot be protected;
acquire() then reports `supported = False` and the game carries on unlocked.
Standard library only.
"""
import os
import time

try:
    import fcntl
except ImportError:                     # Windows
    fcntl = None
    import msvcrt

LOCK_NAME = ".arcade.lock"


class SaveLock:
    def __init__(self, directory, name=LOCK_NAME):
        self.path = os.path.join(directory, name)
        self._directory = directory
        self._fd = None
        self.supported = True           # False: this file system would not lock (we run unprotected)

    @property
    def held(self):
        return self._fd is not None

    def acquire(self):
        """Take the lock. True if this process now holds it (or locking is not
        available here); False if another running copy holds it."""
        if self.held:
            return True
        os.makedirs(self._directory, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            self._lock(fd)
        except BlockingIOError:
            os.close(fd)
            return False
        except OSError as exc:
            if self._is_contention(exc):
                os.close(fd)
                return False
            self.supported = False      # e.g. a file system without lock support
            print(f"[save] could not lock {self.path} ({exc}); running without single-instance protection")
        self._fd = fd
        self._write_owner()
        return True

    def holder(self):
        """What the lock file says about whoever holds it ('pid 123'), or ''."""
        try:
            with open(self.path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return ""

    def release(self):
        fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            self._unlock(fd)
        except OSError:
            pass
        os.close(fd)

    def __enter__(self):
        if not self.acquire():
            raise SaveLockedError(self.holder())
        return self

    def __exit__(self, *exc):
        self.release()

    # ------------------------------------------------------------ platform
    @staticmethod
    def _is_contention(exc):
        import errno
        return exc.errno in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK, errno.EDEADLK)

    def _lock(self, fd):
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

    def _unlock(self, fd):
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
        else:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

    def _write_owner(self):
        """Informational only. On Windows the locked first byte stays unreadable
        to others, so the text starts after it."""
        text = f"\npid {os.getpid()} started {time.strftime('%Y-%m-%d %H:%M:%S')}\n".encode()
        try:
            os.lseek(self._fd, 0, os.SEEK_SET)
            os.ftruncate(self._fd, 0)
            os.write(self._fd, text)
        except OSError:
            pass


class SaveLockedError(Exception):
    """Another running copy of the arcade holds the save directory."""

    def __init__(self, holder=""):
        super().__init__("the arcade is already running" + (f" ({holder})" if holder else ""))
        self.holder = holder
