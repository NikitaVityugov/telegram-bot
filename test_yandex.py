import os
import requests
from dotenv import load_dotenv

# Загружаем ключи из .env
load_dotenv()

API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
headers = {
    "Authorization": f"Api-Key {API_KEY}",
    "Content-Type": "application/json"
}
data = {
    "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
    "completionOptions": {
        "stream": False,
        "temperature": 0.6,
        "maxTokens": 100
    },
    "messages": [
        {"role": "user", "text": "Придумай шутку про программистов"}
    ]
}

response = requests.post(url, headers=headers, json=data)
print("Статус:", response.status_code)
print("Ответ:", response.text)
