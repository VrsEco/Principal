import requests
import json

def check_process(process_id):
    url = f"http://127.0.0.1:5032/api/processes/{process_id}"
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        else:
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_process(118)
