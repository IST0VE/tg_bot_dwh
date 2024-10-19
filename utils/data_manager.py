# utils/data_manager.py

import json
import os
from config import DATA_FILE

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "shared_folders": {}}
    with open(DATA_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def init_user(data, user_id):
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "current_path": [],
            "structure": {
                "folders": {},
                "files": []
            },
            "file_mappings": {}  # Добавляем поле для сопоставления short_id и file_id
        }