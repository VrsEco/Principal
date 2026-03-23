import requests

def test_api_get_model(plan_id, company_id):
    url = f"http://127.0.0.1:5032/api/plans/{plan_id}/implantation/model?company_id={company_id}"
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print(f"Content keys: {data.get('content', {}).keys()}")
        print(f"Segments count: {len(data.get('content', {}).get('segments', []))}")
        print(f"Products count: {len(data.get('content', {}).get('products', []))}")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    # We know plan 10 belongs to company 5
    test_api_get_model(10, 5)
