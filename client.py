import requests
import json
import aiohttp
import asyncio

BASE_URL = "http://localhost:5000"  # サーバーのURLとポートに応じて変更

def post_user_data(user_name: str, money: int, stocks: dict):
    """現在の残高と保有株をバックアップとして送信"""
    url = BASE_URL
    payload = {
        "user_name": user_name,
        "money": money,
        "stocks": {
            key: {
                "stock": value["stock"],
                "special_stocks": value["special_stocks"]
            } for key, value in stocks.items()
        }
    }
    try:
        res = requests.post(url, json=payload)
        print(f"[Backup] POST / - Status: {res.status_code}")
        print("Response:", res.text)
    except Exception as e:
        print("Error:", e)

def get_top_ranking(limit: int = 10):
    url = f"{BASE_URL}?limit={limit}"
    res = requests.get(url)
    print(f"GET /?limit={limit} - Status: {res.status_code}")
    try:
        data = res.json()
        print("Response:", json.dumps(data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("Response is not valid JSON:")
        print(res.text)

def get_my_ranking(user_name: str):
    url = f"{BASE_URL}?user_name={user_name}"
    res = requests.get(url)
    print(f"GET /?user_name={user_name} - Status: {res.status_code}")
    try:
        data = res.json()
        print("Response:", json.dumps(data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("Response is not valid JSON:")
        print(res.text)

def get_user_money(user_name: str) -> int:
    """ユーザーの現在の所持金を取得"""
    try:
        url = f"{BASE_URL}?user_name={user_name}&get_money=1"
        res = requests.get(url)
        if res.status_code == 200:
            return res.json().get("money", 10000)
    except Exception as e:
        print("[ERROR] get_user_money:", e)
    return 10000

def get_user_stocks(user_name: str) -> dict:
    """ユーザーの現在の保有株情報を取得"""
    try:
        url = f"{BASE_URL}?user_name={user_name}&get_stocks=1"
        res = requests.get(url)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print("[ERROR] get_user_stocks:", e)
    return {
        "co2": {"stock": 0, "special_stocks": 0},
        "temp": {"stock": 0, "special_stocks": 0},
        "humid": {"stock": 0, "special_stocks": 0}
    }

# 上記２つのasync版
async def async_get_user_money(session: aiohttp.ClientSession, user_name: str) -> int:
    url = f"{BASE_URL}?user_name={user_name}&get_money=1"
    try:
        async with session.get(url) as res:
            if res.status == 200:
                data = await res.json()
                return data.get("money", 10000)
    except Exception as e:
        print("[ERROR] async_get_user_money:", e)
    return 10000


async def async_get_user_stocks(session: aiohttp.ClientSession, user_name: str) -> dict:
    url = f"{BASE_URL}?user_name={user_name}&get_stocks=1"
    try:
        async with session.get(url) as res:
            if res.status == 200:
                return await res.json()
    except Exception as e:
        print("[ERROR] async_get_user_stocks:", e)
    return {
        "co2": {"stock": 0, "special_stocks": 0},
        "temp": {"stock": 0, "special_stocks": 0},
        "humid": {"stock": 0, "special_stocks": 0}
    }


async def get_user_data_concurrently(user_name: str):
    async with aiohttp.ClientSession() as session:
        money_task = asyncio.create_task(async_get_user_money(session, user_name))
        stocks_task = asyncio.create_task(async_get_user_stocks(session, user_name))

        money = await money_task
        stocks = await stocks_task

        return money, stocks


def register(user_name: str, register: bool = True):
    url = f'{BASE_URL}?user_name={user_name}&register={register}'
    response = requests.get(url)

    if response.status_code != 200:
        print(f"[ERROR] status={response.status_code}")
        return False, "Request failed"

    try:
        data = response.json()
        success = data.get("success", False)
        message = data.get("message", "")
        print(f"[{'OK' if success else 'NG'}] {message}")
        return success, message
    except json.JSONDecodeError:
        print("[ERROR] Could not decode response.")
        return False, "Invalid response"
    




if __name__ == "__main__":
    user = "sora161023"

    # ユーザー登録
    register(user)

    # データ送信（バックアップ）
    post_user_data(user, 12345, {
        "co2": {"stock": 3, "special_stocks": 1},
        "temp": {"stock": 5, "special_stocks": 0},
        "humid": {"stock": 2, "special_stocks": 4}
    })

    # 取得テスト
    money = get_user_money(user)
    stocks = get_user_stocks(user)
    print(f"[確認] {user} の所持金: {money}")
    print(f"[確認] {user} の保有株: {json.dumps(stocks, indent=2)}")
