from dotenv import load_dotenv

load_dotenv()

from app_pev import app


def main():
    client = app.test_client()
    resp = client.post(
        "/api/companies/13/process-instances",
        json={"process_id": 95, "title": "Teste via test_client", "trigger_type": "manual"},
    )
    print("status", resp.status_code)
    print("body", resp.get_data(as_text=True))


if __name__ == "__main__":
    main()

