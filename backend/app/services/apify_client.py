import json
import os
import time
from pathlib import Path
from typing import Optional

from apify_client import ApifyClient
from apify_client.errors import ApifyApiError

from app.config import settings


class ApifyClientService:
    def __init__(self):
        self.token = os.getenv("APIFY_API_TOKEN")
        self.client = ApifyClient(self.token) if self.token else None

    def run_scraper(
        self,
        actor_id: str,
        target_url: str,
        timeout_seconds: int = 30,
        platform_key: Optional[str] = None,
    ) -> list:
        try:
            if self.client is None:
                return self._fallback_results_or_raise(
                    "APIFY_API_TOKEN is not set; using fixture fallback.",
                    platform_key=platform_key,
                )

            run_input = {
                "mode": "url",
                "url": target_url,
                "scrapeDescription": True,
                "includeReviews": True,
                "currency": "VND",
            }

            run = self.client.actor(actor_id).start(run_input=run_input)
            run_id = run["id"]

            start_time = time.time()
            while True:
                if time.time() - start_time > timeout_seconds:
                    self.client.run(run_id).abort()
                    raise TimeoutError(f"Actor timeout sau {timeout_seconds} giay.")

                run_info = self.client.run(run_id).get()
                status = run_info.get("status")

                if status == "SUCCEEDED":
                    break
                if status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    raise Exception(f"Actor ket thuc voi loi. Trang thai: {status}")

                time.sleep(2)

            dataset_id = run_info["defaultDatasetId"]
            dataset_items = self.client.dataset(dataset_id).list_items().items
            return dataset_items

        except (ApifyApiError, TimeoutError, Exception) as e:
            return self._fallback_results_or_raise(str(e), platform_key=platform_key)

    def _fallback_results_or_raise(self, reason: str, platform_key: Optional[str] = None) -> list:
        if settings.APIFY_FIXTURE_FALLBACK:
            candidate_paths = self._fixture_candidates(platform_key)
            collected_items: list[dict] = []
            for fixture_path in candidate_paths:
                if fixture_path.exists():
                    with fixture_path.open("r", encoding="utf-8") as f:
                        fixture_data = json.load(f)
                    items = fixture_data if isinstance(fixture_data, list) else [fixture_data]
                    filtered = self._filter_fixture_items(items, platform_key, fixture_path)
                    collected_items.extend(filtered)

            if collected_items:
                return self._dedupe_items(collected_items)

            return []

        raise Exception(reason)

    def _filter_fixture_items(
        self,
        items: list,
        platform_key: Optional[str],
        fixture_path: Path,
    ) -> list:
        filtered = [item for item in items if isinstance(item, dict)]
        if not platform_key:
            return filtered

        is_platform_specific = fixture_path.stem.endswith(f"_{platform_key}")
        if is_platform_specific:
            return filtered

        return [
            item
            for item in filtered
            if str(item.get("platform", "")).strip().lower() == platform_key
        ]

    def _dedupe_items(self, items: list[dict]) -> list[dict]:
        deduped: list[dict] = []
        seen: set[str] = set()
        for item in items:
            signature = json.dumps(
                {
                    "platform": item.get("platform"),
                    "barcode": item.get("barcode"),
                    "title": item.get("title") or item.get("name"),
                    "url": item.get("url"),
                    "item_id": item.get("item_id") or item.get("itemId"),
                    "shop_id": item.get("shop_id") or item.get("shopId"),
                },
                sort_keys=True,
                ensure_ascii=False,
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(item)
        return deduped

    def _fixture_candidates(self, platform_key: Optional[str]) -> list[Path]:
        base_dir = Path(__file__).resolve().parents[3]
        candidates: list[Path] = []

        if platform_key:
            normalized = platform_key.lower().strip()
            candidates.extend(
                [
                    base_dir / "backend" / "data" / f"apify_fallback_{normalized}.json",
                    base_dir / "data" / f"apify_fallback_{normalized}.json",
                    base_dir / "mock_data" / f"apify_fallback_{normalized}.json",
                ]
            )
            if normalized == "shopee" and settings.APIFY_FIXTURE_PATH:
                candidates.append(base_dir / settings.APIFY_FIXTURE_PATH)

        candidates.extend(
            [
                base_dir / "backend" / "data" / "apify_fallback_fixture.json",
                base_dir / "data" / "apify_fallback_fixture.json",
            ]
        )

        deduped: list[Path] = []
        seen = set()
        for path in candidates:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(path)
        return deduped


def get_apify_service():
    return ApifyClientService()

