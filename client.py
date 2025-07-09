import requests
import json

BASE_URL = "http://localhost:5000"  # サーバーのURLとポートに応じて変更

def post_score(user_name: str, score: int):
    """スコアを投稿"""
    url = BASE_URL
    payload = {
        "user_name": user_name,
        "score": score
    }
    response = requests.post(url, json=payload)
    print(f"POST / - Status: {response.status_code}")
    print("Response:", response.text)


def get_top_ranking(limit: int = 10):
    """上位ランキングを取得"""
    url = f"{BASE_URL}?limit={limit}"
    response = requests.get(url)
    print(f"GET /?limit={limit} - Status: {response.status_code}")
    print("Response:", json.dumps(response.json(), indent=2, ensure_ascii=False))


def get_my_ranking(user_name: str):
    """自分のランキングを取得"""
    url = f"{BASE_URL}?user_name={user_name}"
    response = requests.get(url)
    print(f"GET /?user_name={user_name} - Status: {response.status_code}")
    print("Response:", json.dumps(response.json(), indent=2, ensure_ascii=False))


def register(user_name: str, register: bool = True):
    url = f'{BASE_URL}?user_name={user_name}&register={register}'
    response = requests.get(url)
    print(response.text)


if __name__ == "__main__":
    register('id123')
    register('sora161023')
    # 任意のテストケースをここで実行
    post_score("sora161023", 1000)
    post_score("bbbbbb", 20900)
    post_score("af55555", 721)

    get_top_ranking(limit=5)
    get_my_ranking("sora161023")
