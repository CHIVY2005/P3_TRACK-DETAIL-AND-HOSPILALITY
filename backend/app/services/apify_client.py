import json
import os
import time
from pathlib import Path

from apify_client import ApifyClient
from apify_client.errors import ApifyApiError

from app.config import settings


class ApifyClientService:
    def __init__(self):
        self.token = os.getenv("APIFY_API_TOKEN")
        if not self.token:
            raise ValueError("APIFY_API_TOKEN is not set in the environment variables.")
        self.client = ApifyClient(self.token)

    def run_scraper(self, actor_id: str, target_url: str, timeout_seconds: int = 30) -> list:
        try:
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
            return self._fallback_results_or_raise(str(e))

    def _fallback_results_or_raise(self, reason: str) -> list:
        if settings.APIFY_FIXTURE_FALLBACK:
            fixture_path = Path(__file__).resolve().parents[3] / settings.APIFY_FIXTURE_PATH
            if fixture_path.exists():
                with fixture_path.open("r", encoding="utf-8") as f:
                    fixture_data = json.load(f)
                if isinstance(fixture_data, list):
                    return fixture_data
                return [fixture_data]

        raise Exception(reason)


def get_apify_service():
    return ApifyClientService()

