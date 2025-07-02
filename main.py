import pygame
import sys
import time
import csv
import requests
import datetime
import numpy as np
from typing import Tuple

WIDTH  = 500
HEIGHT = 600
WINDOW_SIZE = 288

# --- 色の定義 ---
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GREEN = (0, 180, 0)
COLOR_RED = (200, 0, 0)
COLOR_BLUE = (50, 50, 200)
COLOR_BG = (240, 240, 250)
COLOR_SCROLL_BG = (200, 200, 200)
COLOR_SCROLL_HANDLE = (100, 100, 255)
COLOR_INDICATOR = (255, 0, 0)
COLOR_BUTTON = (220, 220, 220)
COLOR_BUTTON_ACTIVE = (180, 220, 255)

# --- Pygame 初期化 ---
pygame.init()
pygame.display.set_caption('Airoco FX')
screen = pygame.display.set_mode((WIDTH, HEIGHT))
font = pygame.font.SysFont('Meiryo', 18)

def get_data(sensor_name: str) -> Tuple[list, list, list, list]:
    """過去7日間のセンサデータを取得"""
    curr_time = int(time.time())
    data = []

    airoco_url = 'https://airoco.necolico.jp/data-api/day-csv'
    id = 'CgETViZ2'
    subscription_key = '6b8aa7133ece423c836c38af01c59880'

    # 過去7日間のデータを取得
    for day in range(7):
        tt = curr_time - 3600 * 24 * (7 - day)  # 24時間ごとに1週間分
        try:
            res = requests.get(f'{airoco_url}?id={id}&subscription-key={subscription_key}&startDate={tt}')
            res.raise_for_status()  # HTTPエラーをチェック
            raw_data = csv.reader(res.text.strip().splitlines())

            for row in raw_data:
                if row[1] == 'Ｒ３ー３０１':
                    data.append(list(map(float, row[3:7])))
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            return [], [], [], []
        
    if not data:
        print("This sensor is not connected")
        return [], [], [], []
    
    data = np.array(data)
    data = np.argsort(data[:, 3])  # 時刻でソート

    timestamps   = [datetime.datetime.fromtimestamp(ts) for ts in data[:, 3]]
    co2_values   = data[:, 0].tolist()
    temp_values  = data[:, 1].tolist()
    humid_values = data[:, 2].tolist()

    return timestamps, co2_values, temp_values, humid_values

def main() -> None:
    runnning = True
    

