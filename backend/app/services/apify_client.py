import os
import time
from apify_client import ApifyClient
from apify_client.errors import ApifyApiError

class ApifyClientService:
    def __init__(self):
        self.token = os.getenv("APIFY_API_TOKEN")
        if not self.token:
            raise ValueError("APIFY_API_TOKEN is not set in the environment variables.")
        self.client = ApifyClient(self.token)

    def run_scraper(self, actor_id: str, target_url: str, timeout_seconds: int = 30) -> list:
        try:
            run_input = {"startUrls": [{"url": target_url}]}
            
            # 1. Khởi chạy Actor (bất đồng bộ trên hệ thống Apify)
            run = self.client.actor(actor_id).start(run_input=run_input)
            run_id = run["id"]
            
            start_time = time.time()
            
            # 2. Vòng lặp poll kiểm tra trạng thái
            while True:
                if time.time() - start_time > timeout_seconds:
                    # Dừng actor nếu quá thời gian chờ
                    self.client.run(run_id).abort()
                    raise TimeoutError(f"Actor timeout sau {timeout_seconds} giây.")

                run_info = self.client.run(run_id).get()
                status = run_info.get("status")

                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    raise Exception(f"Actor kết thúc với lỗi. Trạng thái: {status}")

                time.sleep(2)  # Đợi 2 giây trước khi kiểm tra lại

            # 3. Lấy dữ liệu từ Dataset khi hoàn thành
            dataset_id = run_info["defaultDatasetId"]
            dataset_items = self.client.dataset(dataset_id).list_items().items
            
            return dataset_items

        except ApifyApiError as e:
            raise Exception(f"Lỗi từ Apify API: {str(e)}")
        except TimeoutError:
            raise
        except Exception as e:
            raise Exception(f"Lỗi không xác định khi chạy scraper: {str(e)}")

def get_apify_service():
    return ApifyClientService()

