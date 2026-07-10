import sys
import os
import requests
import json

API_ORIGIN = os.getenv("API_ORIGIN", "http://127.0.0.1:8001").rstrip("/")
BASE_URL = f"{API_ORIGIN}/api/v1"

def test_health():
    print("Testing health check...")
    try:
      res = requests.get(f"{API_ORIGIN}/")
      print(f"Status code: {res.status_code}")
      print(f"Response: {res.json()}")
      return res.status_code == 200
    except Exception as e:
      print(f"Failed to connect to backend: {e}")
      return False

def test_list_products():
    print("\nTesting list products endpoint...")
    res = requests.get(f"{BASE_URL}/products")
    print(f"Status code: {res.status_code}")
    products = res.json()
    print(f"Found {len(products)} products in database.")
    if len(products) > 0:
        print(f"Sample product: {products[0]['name']} (Barcode: {products[0]['barcode']})")
    return res.status_code == 200

def test_pricing_overview():
    print("\nTesting pricing overview metrics...")
    res = requests.get(f"{BASE_URL}/pricing/overview")
    print(f"Status code: {res.status_code}")
    print(f"Metrics: {json.dumps(res.json(), indent=2)}")
    return res.status_code == 200


def test_channel_intelligence():
    print("\nTesting omnichannel CPI and coverage...")
    res = requests.get(f"{BASE_URL}/pricing/channel-index")
    payload = res.json()
    print(f"Status code: {res.status_code}")
    print(f"Summary: {json.dumps(payload.get('summary', {}), indent=2, default=str)}")
    return res.status_code == 200 and len(payload.get("channels", [])) > 0

def test_trigger_scraper(product_id):
    print("\nTesting one-SKU scraper trigger...")
    res = requests.post(f"{BASE_URL}/scraper/trigger", json={"product_id": product_id})
    print(f"Status code: {res.status_code}")
    print(f"Response: {res.json()}")
    return res.status_code in [200, 202]

def test_trigger_agent():
    print("\nTesting trigger AI Agent pricing optimization...")
    res = requests.post(f"{BASE_URL}/agent/run", json={})
    print(f"Status code: {res.status_code}")
    print(f"Response: {res.json()}")
    return res.status_code in [200, 202, 409]

def test_list_agent_tasks():
    print("\nTesting fetch AI Agent execution history...")
    res = requests.get(f"{BASE_URL}/agent/tasks")
    print(f"Status code: {res.status_code}")
    tasks = res.json()
    print(f"Found {len(tasks)} historical agent task runs.")
    if len(tasks) > 0:
        print(f"Latest task status: {tasks[0]['status']}, Started at: {tasks[0]['started_at']}")
    return res.status_code == 200

if __name__ == "__main__":
    print("=== STARTING BACKEND BOILERPLATE API TESTS ===")
    print("Ensure uvicorn is running on 127.0.0.1:8001 (inside backend folder)")
    print("==============================================")
    
    if not test_health():
        print("\n[ERROR] Backend is offline or not reachable. Exiting test.")
        sys.exit(1)
        
    test_list_products()
    test_pricing_overview()
    test_channel_intelligence()
    products = requests.get(f"{BASE_URL}/products").json()
    if products:
        test_trigger_scraper(products[0]["id"])
    test_trigger_agent()
    test_list_agent_tasks()
    
    print("\n=== TESTS COMPLETED ===")
