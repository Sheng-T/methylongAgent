"""
UI log bridge — forwards node print() output to Streamlit UI.
"""
import queue
import threading

_log_queue = queue.Queue(maxsize=10000)
_lock = threading.Lock()


def ui_print(*args, **kwargs):
    """Replacement for print() that also enqueues messages for UI display."""
    msg = " ".join(str(a) for a in args)
    try:
        _log_queue.put_nowait(msg)
    except queue.Full:
        pass  # silently discard when queue is full
    print(msg, **kwargs)


def get_log_queue():
    return _log_queue


def flush_logs():
    """Drain and return all queued log messages."""
    logs = []
    with _lock:
        while not _log_queue.empty():
            try:
                logs.append(_log_queue.get_nowait())
            except queue.Empty:
                break
    return logs


def clear_logs():
    """Clear the log queue."""
    with _lock:
        while not _log_queue.empty():
            try:
                _log_queue.get_nowait()
            except queue.Empty:
                break
