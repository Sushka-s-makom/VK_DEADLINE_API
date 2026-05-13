from __future__ import annotations

import time
import fcntl
from datetime import datetime
from pathlib import Path

from scripts.import_google_sheet_deadlines import import_deadlines
from scripts.send_due_notifications import send_due_notifications

LOCK_PATH = Path(".scheduler.lock")


def main() -> int:
    lock_file = LOCK_PATH.open("w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("local scheduler is already running")
        return 1

    print("local scheduler started")
    last_import_hour: str | None = None
    while True:
        now = datetime.now()
        current_hour = now.strftime("%Y-%m-%d %H")
        if now.minute == 0 and current_hour != last_import_hour:
            try:
                result = import_deadlines()
                print("import", now.strftime("%Y-%m-%d %H:%M:%S"), result)
                last_import_hour = current_hour
            except Exception as exc:
                print("import failed", exc)

        try:
            processed = send_due_notifications()
            if processed:
                print("send", now.strftime("%Y-%m-%d %H:%M:%S"), "processed", processed)
        except Exception as exc:
            print("send failed", exc)

        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
