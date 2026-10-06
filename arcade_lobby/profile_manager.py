"""ProfileManager: any number of independent saved profiles.

Layout (under the saves directory):

    profiles.json              index: profile_id, display_name, created_at,
                               last_played, plus last player count / recents
    profiles/<profile-id>.json one file of gameplay progress per profile

A profile is known by its generated, stable ID; the display name is only a
label (unique, case-insensitively, so the select screen is unambiguous) and
never appears in a file name. Each profile is written to its own file by its
own autosave callback, so one profile's change can never overwrite another's:
`load_profile` hands out one shared instance per id, and `save_profile`
refuses any object that is not that instance.

The old single-profile save (`save_data.json`) is migrated into the first
profile exactly once - the index file is the "already migrated" marker, and
the old file is kept next to it as `save_data.json.migrated`.
"""
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from player_profile import PlayerProfile, ProfileStore
from settings import PROFILE_NAME_MAX, RECENT_PROFILES

INDEX_VERSION = 1
MIGRATED_NAME = "PLAYER"        # what the old single save is called after migration
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_NAME_CHARS = re.compile(r"[^A-Za-z0-9 .'!?-]")     # what the pixel font can draw


class ProfileError(ValueError):
    """A profile operation was refused."""


class InvalidNameError(ProfileError):
    pass


class DuplicateNameError(ProfileError):
    pass


class UnknownProfileError(ProfileError, KeyError):
    pass


@dataclass
class ProfileInfo:
    """What the index knows about a profile (not its progress)."""
    profile_id: str
    display_name: str
    created_at: str
    last_played: str | None = None

    def to_dict(self):
        return {"profile_id": self.profile_id, "display_name": self.display_name,
                "created_at": self.created_at, "last_played": self.last_played}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_name(name):
    """Trim, collapse inner whitespace and drop characters the game cannot
    show. Raises InvalidNameError for a blank or too long result."""
    if not isinstance(name, str):
        raise InvalidNameError("name must be text")
    cleaned = " ".join(_NAME_CHARS.sub("", name).split())
    if not cleaned:
        raise InvalidNameError("name is blank")
    if len(cleaned) > PROFILE_NAME_MAX:
        raise InvalidNameError(f"name is longer than {PROFILE_NAME_MAX} characters")
    return cleaned


def _write_json(path, data):
    """Atomic write: temp file + rename, so a crash cannot leave half a file."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(tmp, path)
    except OSError as e:
        print(f"[save] could not write {path}: {e}")
        return False
    return True


class ProfileManager:
    def __init__(self, root, clock=None, legacy_path=None, now=_now):
        self.root = root
        self.clock = clock
        self._now = now
        self.index_path = os.path.join(root, "profiles.json")
        self.profiles_dir = os.path.join(root, "profiles")
        self._infos = {}            # profile_id -> ProfileInfo, in creation order
        self._loaded = {}           # profile_id -> the one live PlayerProfile
        self.last_player_count = 1
        self.recent_ids = []        # most recently used first
        self.migrated_from = None
        os.makedirs(self.profiles_dir, exist_ok=True)
        if os.path.exists(self.index_path):
            self._read_index()
        else:
            self._first_run(legacy_path)

    # ------------------------------------------------------------ queries
    def list_profiles(self):
        """Every saved profile (no limit), in the order they were created."""
        return list(self._infos.values())

    def __len__(self):
        return len(self._infos)

    def profile_exists(self, profile_id):
        return profile_id in self._infos

    def info(self, profile_id):
        try:
            return self._infos[profile_id]
        except KeyError:
            raise UnknownProfileError(profile_id) from None

    def name_available(self, name, ignore_id=None):
        try:
            wanted = normalize_name(name).casefold()
        except InvalidNameError:
            return False
        return all(i.display_name.casefold() != wanted
                   for i in self._infos.values() if i.profile_id != ignore_id)

    def profile_path(self, profile_id):
        return os.path.join(self.profiles_dir, f"{profile_id}.json")

    # ------------------------------------------------------------ create / delete
    def create_profile(self, name):
        """Make a new profile with a fresh id. Returns the loaded PlayerProfile."""
        name = normalize_name(name)
        if not self.name_available(name):
            raise DuplicateNameError(f"a profile called {name!r} already exists")
        profile_id = uuid.uuid4().hex
        while profile_id in self._infos:        # (astronomically unlikely)
            profile_id = uuid.uuid4().hex
        self._infos[profile_id] = ProfileInfo(profile_id, name, self._now())
        profile = PlayerProfile(clock=self.clock, profile_id=profile_id, display_name=name)
        self._adopt(profile)
        self._write_profile(profile)
        self._write_index()
        return profile

    def delete_profile(self, profile_id):
        """Remove a profile and its file for good. Returns False if unknown."""
        if profile_id not in self._infos:
            return False
        del self._infos[profile_id]
        self._loaded.pop(profile_id, None)
        if profile_id in self.recent_ids:
            self.recent_ids.remove(profile_id)
        self._write_index()                     # the index first: a leftover file is harmless
        try:
            os.remove(self.profile_path(profile_id))
        except OSError:
            pass
        return True

    # ------------------------------------------------------------ load / save
    def load_profile(self, profile_id):
        """The live profile for `profile_id` (the same object every time, so
        two players can never hold two copies of one profile)."""
        info = self.info(profile_id)
        profile = self._loaded.get(profile_id)
        if profile is None:
            profile = ProfileStore(self.profile_path(profile_id), self.clock).load()
            profile.profile_id = profile_id
            profile.display_name = info.display_name
            self._adopt(profile)
        return profile

    def save_profile(self, profile):
        """Write `profile` to its own file. Refused (False) for a profile this
        manager does not know or a stale duplicate of a loaded one."""
        pid = getattr(profile, "profile_id", None)
        if pid not in self._infos or self._loaded.get(pid) is not profile:
            print(f"[save] refusing to save an unmanaged profile ({pid!r})")
            return False
        return self._write_profile(profile)

    def _adopt(self, profile):
        self._loaded[profile.profile_id] = profile
        profile.subscribe_save(lambda p=profile: self.save_profile(p))   # bound to THIS profile

    def _write_profile(self, profile):
        return ProfileStore(self.profile_path(profile.profile_id), self.clock).save(profile)

    # ------------------------------------------------------------ recents
    def record_session(self, profiles, player_count):
        """Remember who just started playing and in how many players."""
        self.last_player_count = player_count
        now = self._now()
        for profile in reversed(list(profiles)):
            info = self._infos.get(profile.profile_id)
            if info is None:
                continue
            info.last_played = now
            if info.profile_id in self.recent_ids:
                self.recent_ids.remove(info.profile_id)
            self.recent_ids.insert(0, info.profile_id)
        del self.recent_ids[RECENT_PROFILES:]
        self._write_index()

    def most_recent(self, exclude=()):
        """The id of the most recently used profile not in `exclude`, or None."""
        for pid in self.recent_ids:
            if pid in self._infos and pid not in exclude:
                return pid
        return None

    # ------------------------------------------------------------ index
    def _write_index(self):
        return _write_json(self.index_path, {
            "version": INDEX_VERSION,
            "last_player_count": self.last_player_count,
            "recent": list(self.recent_ids),
            "migrated_from": self.migrated_from,
            "profiles": [i.to_dict() for i in self._infos.values()],
        })

    def _read_index(self):
        try:
            with open(self.index_path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("index is not a JSON object")
        except (OSError, ValueError) as e:
            print(f"[save] could not read {self.index_path} ({e}); rebuilding it from the profile files")
            try:
                os.replace(self.index_path, self.index_path + ".corrupt")
            except OSError:
                pass
            self._rebuild_index()
            return
        for entry in data.get("profiles") if isinstance(data.get("profiles"), list) else []:
            if not isinstance(entry, dict):
                continue
            pid, name = entry.get("profile_id"), entry.get("display_name")
            if (isinstance(pid, str) and _ID_RE.match(pid) and isinstance(name, str) and name
                    and pid not in self._infos):
                created, played = entry.get("created_at"), entry.get("last_played")
                self._infos[pid] = ProfileInfo(pid, name, created if isinstance(created, str) else "",
                                               played if isinstance(played, str) else None)
        count = data.get("last_player_count")
        self.last_player_count = count if count in (1, 2) else 1
        recent = data.get("recent")
        self.recent_ids = [p for p in recent if p in self._infos][:RECENT_PROFILES] \
            if isinstance(recent, list) else []
        mig = data.get("migrated_from")
        self.migrated_from = mig if isinstance(mig, str) else None

    def _rebuild_index(self):
        """The index is lost: recover every profile that still has a file."""
        for name in sorted(os.listdir(self.profiles_dir)):
            stem, ext = os.path.splitext(name)
            if ext != ".json" or not _ID_RE.match(stem):
                continue
            try:
                with open(os.path.join(self.profiles_dir, name), encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            label = data.get("display_name") if isinstance(data, dict) else None
            label = label if isinstance(label, str) and label.strip() else f"PLAYER {len(self._infos) + 1}"
            while not self.name_available(label):
                label += "+"
            self._infos[stem] = ProfileInfo(stem, label[:PROFILE_NAME_MAX + 2], self._now())
        self._write_index()

    # ------------------------------------------------------------ migration
    def _first_run(self, legacy_path):
        """No index yet: carry the old single save over (once), then write the
        index so this never runs again."""
        migrated = None
        if legacy_path and os.path.exists(legacy_path):
            migrated = self._migrate_legacy(legacy_path)
            if migrated is None:
                return              # unreadable old save: leave it alone, try again next launch
        self._write_index()
        if migrated:
            try:
                os.replace(legacy_path, legacy_path + ".migrated")      # kept, never wiped
            except OSError as e:
                print(f"[save] migrated, but could not rename {legacy_path}: {e}")

    def _migrate_legacy(self, legacy_path):
        try:
            with open(legacy_path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("save data is not a JSON object")
        except (OSError, ValueError) as e:
            print(f"[save] could not read old save {legacy_path} ({e}); not migrating it")
            return None
        profile_id = uuid.uuid4().hex
        profile = PlayerProfile.from_dict(data, clock=self.clock)    # same cleaning as a normal load
        profile.profile_id, profile.display_name = profile_id, MIGRATED_NAME
        self._infos[profile_id] = ProfileInfo(profile_id, MIGRATED_NAME, self._now())
        self.migrated_from = os.path.basename(legacy_path)
        if not self._write_profile(profile):
            del self._infos[profile_id]
            self.migrated_from = None
            return None
        return profile_id
