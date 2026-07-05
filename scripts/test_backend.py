import sys
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    print("Testing health check...")
    try:
      res = requests.get("http://localhost:8000/")
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

def test_trigger_scraper():
    print("\nTesting trigger mock scraper...")
    res = requests.post(f"{BASE_URL}/scraper/trigger", json={})
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
    print("Ensure uvicorn is running: uvicorn app.main:app --reload (inside backend folder)")
    print("==============================================")
    
    if not test_health():
        print("\n[ERROR] Backend is offline or not reachable. Exiting test.")
        sys.exit(1)
        
    test_list_products()
    test_pricing_overview()
    test_trigger_scraper()
    test_trigger_agent()
    test_list_agent_tasks()
    
    print("\n=== TESTS COMPLETED ===")
