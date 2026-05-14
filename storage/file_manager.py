"""
User file manager.

Directory structure:
  {user_data_root}/
      {uid}/                        <- user root dir (uses integer uid, not username)
          {session_id}/             <- session isolation dir
              sample.bam
              samplesheet.csv
          {session_id_2}/
              ...
"""
import hashlib
import os
import shutil
import threading
from typing import Dict, List, Optional

_user_locks: dict[int, threading.Lock] = {}
_locks_meta = threading.Lock()


def file_hash(file):
    return hashlib.md5(file.getvalue()).hexdigest()


def _dir_size(path: str) -> int:
    total = 0
    for entry in os.scandir(path):
        if entry.is_file(follow_symlinks=False):
            total += entry.stat().st_size
        elif entry.is_dir(follow_symlinks=False):
            total += _dir_size(entry.path)
    return total


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


class FileManager:
    def __init__(self, user_data_root: str, quota_bytes: int):
        self.root = user_data_root
        self.quota = quota_bytes
        os.makedirs(self.root, exist_ok=True)

    def _user_lock(self, uid: int) -> threading.Lock:
        with _locks_meta:
            if uid not in _user_locks:
                _user_locks[uid] = threading.Lock()
            return _user_locks[uid]

    def user_dir(self, uid: int) -> str:
        p = os.path.join(self.root, str(uid))
        os.makedirs(p, exist_ok=True)
        return p

    def session_dir(self, uid: int, session_id: str) -> str:
        p = os.path.join(self.user_dir(uid), session_id)
        os.makedirs(p, exist_ok=True)
        return p

    def save_file(self, uid: int, session_id: str, filename: str, data) -> str:
        with self._user_lock(uid):
            return self._save_file_locked(uid, session_id, filename, data)

    def _save_file_locked(self, uid: int, session_id: str, filename: str, data) -> str:
        usage = self.get_usage(uid)
        dest = os.path.join(self.session_dir(uid, session_id), filename)

        if isinstance(data, (bytes, bytearray)):
            if usage["total_bytes"] + len(data) > self.quota:
                raise ValueError(
                    f"Storage quota exceeded: used {fmt_size(usage['total_bytes'])}, "
                    f"quota {fmt_size(self.quota)}"
                )
            with open(dest, "wb") as f:
                f.write(data)
        else:
            written = 0
            chunk = 8 * 1024 * 1024
            try:
                with open(dest, "wb") as f:
                    while True:
                        buf = data.read(chunk)
                        if not buf:
                            break
                        if usage["total_bytes"] + written + len(buf) > self.quota:
                            raise ValueError(
                                f"Storage quota exceeded: used {fmt_size(usage['total_bytes'])}, "
                                f"quota {fmt_size(self.quota)}"
                            )
                        f.write(buf)
                        written += len(buf)
            except Exception:
                if os.path.exists(dest):
                    os.unlink(dest)
                raise
        return dest

    def list_session_files(self, uid: int, session_id: str) -> List[Dict]:
        d = os.path.join(self.user_dir(uid), session_id)
        if not os.path.isdir(d):
            return []
        return [
            {"name": e.name, "path": e.path, "size": e.stat().st_size}
            for e in sorted(os.scandir(d), key=lambda x: x.name)
            if e.is_file()
        ]

    def get_usage(self, uid: int) -> Dict:
        udir = os.path.join(self.root, str(uid))
        if not os.path.isdir(udir):
            return {"total_bytes": 0, "sessions": {}}
        sessions: Dict[str, int] = {}
        for entry in os.scandir(udir):
            if entry.is_dir():
                sessions[entry.name] = _dir_size(entry.path)
        return {"total_bytes": sum(sessions.values()), "sessions": sessions}

    def delete_file(self, uid: int, session_id: str, filename: str) -> bool:
        fp = os.path.join(self.user_dir(uid), session_id, filename)
        if os.path.isfile(fp):
            os.remove(fp)
            return True
        return False

    def delete_session_files(self, uid: int, session_id: str):
        sdir = os.path.join(self.user_dir(uid), session_id)
        if os.path.isdir(sdir):
            shutil.rmtree(sdir)

    def delete_session_run_dirs(self, uid: int, session_id: str):
        sdir = os.path.join(self.user_dir(uid), session_id)
        if not os.path.isdir(sdir):
            return
        for entry in os.scandir(sdir):
            if entry.is_dir() and entry.name.startswith("run_"):
                shutil.rmtree(entry.path, ignore_errors=True)

    def get_session_breakdown(self, uid: int, session_id: str) -> Dict:
        sdir = os.path.join(self.user_dir(uid), session_id)
        if not os.path.isdir(sdir):
            return {"upload_bytes": 0, "run_bytes": 0, "run_dirs": []}

        upload_bytes = 0
        run_bytes = 0
        run_dirs: list = []

        for entry in os.scandir(sdir):
            if entry.is_file(follow_symlinks=False):
                upload_bytes += entry.stat().st_size
            elif entry.is_dir() and entry.name.startswith("run_"):
                sz = _dir_size(entry.path)
                run_bytes += sz
                run_dirs.append({"name": entry.name, "size": sz})

        run_dirs.sort(key=lambda x: x["name"])
        return {"upload_bytes": upload_bytes, "run_bytes": run_bytes, "run_dirs": run_dirs}


_fm: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    global _fm
    if _fm is None:
        from configs.path_config import OTHER_PATH, USER_QUOTA_BYTES
        _fm = FileManager(OTHER_PATH["user_data_root"], USER_QUOTA_BYTES)
    return _fm
