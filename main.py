import pygame
from pygame.locals import *
import requests
# import threading
from concurrent.futures import ThreadPoolExecutor
import time
import csv

# airoco_url = 'https://airoco.necolico.jp/data-api/latest?id=CgETViZ2&subscription-key=6b8aa7133ece423c836c38af01c59880'
airoco_url = 'https://airoco.necolico.jp/data-api/day-csv?id=CgETViZ2&subscription-key=6b8aa7133ece423c836c38af01c59880'

sensors = {
    'spare-2'   : 0,
    'R3-401'    : 1,
    'R3-301'    : 2,
    'spare-3'   : 3,
    'R3-3F_EH'  : 4,
    'R3-4F_EH'  : 5,
    'spare-4'   : 6,
    'R3-403'    : 7,
    'R3-B1F_EH' : 8,
}

sensor_names = [
    'R3-401', 
    'R3-301', 
    'R3-3F_EH', 
    'R3-4F_EH', 
    'R3-403', 
    'R3-B1F_EH', 
]

WIDTH = 800
HEIGHT = 600

# グラフの設定
max_value = 2000
min_value = 0
graph_width = WIDTH - 100
graph_height = HEIGHT - 100
graph_x = 50
graph_y = 50

data = []


def fetch_data(sensor_name):
    try:
        global data
        print('fetching data...')
        curr_time = int(time.time())
        tt = curr_time - 3600 * 24

        res = requests.get(f'{airoco_url}&startDate={tt}')
        raw_data = csv.reader(res.text.strip().splitlines())
        for row in raw_data:
            if row[1] == 'Ｒ３ー３０１':
                data.append(list(map(float, row[3:7])))
        print(data)

    except:
        print('error')


def get_data(sensor_name):
    try:
        print('getting data...')
        res = requests.get(airoco_url)
        data = res.json()
        result = data[sensors[sensor_name]]
        print(f'Data received: {result}')
    except Exception as e:
        print(f'Error fetching data: {e}')


def main():
    # pygameの初期化

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Airoco FX")
    fps = 60
    clock = pygame.time.Clock()

    # Main loop
    running = True
    dx = 0
    executer = ThreadPoolExecutor(max_workers=2)

    # 更新間隔
    fetch_interval = 10
    last_fetch_time = 0

    # executer.submit(fetch_data, 'R3-3F_EH')
    fetch_data('R3-3F_EH')

    while running:
        clock.tick(fps)
        screen.fill((255, 255, 255))
        pygame.draw.circle(screen, (0, 0, 0), (WIDTH // 2 + dx, HEIGHT // 2), 50)
        dx += 1
        if dx > WIDTH // 2 + 50:
            dx = -WIDTH // 2 - 50
        pygame.display.flip()

        current_time = time.time()
        if current_time - last_fetch_time > fetch_interval:
            executer.submit(get_data, 'R3-3F_EH')
            last_fetch_time = current_time

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            if event.type == KEYDOWN:
                if event.key == K_d:
                    executer.submit(get_data, 'R3-3F_EH')
                    last_fetch_time = current_time

                if event.key == K_ESCAPE:
                    running = False

    pygame.quit()
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)