import json

from app.main import ensure_compat_schema
from app.db.session import SessionLocal
from app.services.demo_seed import seed_demo_dataset


def main() -> None:
    ensure_compat_schema()
    db = SessionLocal()
    try:
        result = seed_demo_dataset(db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
