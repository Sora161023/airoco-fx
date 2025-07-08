import requests
import json

BASE_URL = "http://localhost:5000"  # サーバーのURLとポートに応じて変更

def post_score(id: str, user_name: str, score: int):
    """スコアを投稿"""
    url = BASE_URL
    payload = {
        "id": id,
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


def get_my_ranking(id: str):
    """自分のランキングを取得"""
    url = f"{BASE_URL}?id={id}"
    response = requests.get(url)
    print(f"GET /?id={id} - Status: {response.status_code}")
    print("Response:", json.dumps(response.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # 任意のテストケースをここで実行
    post_score("user90", "000000000", 10)
    post_score("user81", "bbbbbb", 20900)
    post_score("user82", "af55555", 721)  # 上書きされるはず

    get_top_ranking(limit=5)
    get_my_ranking("user123")
