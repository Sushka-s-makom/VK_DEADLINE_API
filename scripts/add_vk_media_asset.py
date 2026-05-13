from __future__ import annotations

import argparse

from app.db.database import Base, SessionLocal, engine
from app.db.models import NotificationMediaAsset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attachment", help="VK attachment, for example photo-123456_789012")
    parser.add_argument("--title", default="Deadline image")
    parser.add_argument("--weight", type=int, default=1)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        asset = NotificationMediaAsset(
            title=args.title,
            attachment=args.attachment,
            weight=args.weight,
            is_active=True,
        )
        db.add(asset)
        db.commit()
        print("media_asset_id:", asset.id)
        print("attachment:", asset.attachment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
