import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
response = requests.get(url)
print(json.dumps(response.json(), indent=2))
