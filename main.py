import pygame
from pygame.locals import *
import requests
import threading

airoco_url = 'https://airoco.necolico.jp/data-api/latest?id=CgETViZ2&subscription-key=6b8aa7133ece423c836c38af01c59880'

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
    WIDTH = 800
    HEIGHT = 600
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Airoco FX")
    fps = 60
    clock = pygame.time.Clock()

    # Main loop
    running = True
    dx = 0
    while running:
        clock.tick(fps)
        screen.fill((255, 255, 255))
        pygame.draw.circle(screen, (0, 0, 0), (WIDTH // 2 + dx, HEIGHT // 2), 50)
        dx += 1
        if dx > WIDTH // 2 + 50:
            dx = -WIDTH // 2 - 50
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            if event.type == KEYDOWN:
                # バックグラウンドでデータ取得を開始
                thread = threading.Thread(target=get_data, args=('R3-3F_EH',))
                thread.daemon = True  # メインプログラム終了時にスレッドも終了
                thread.start()

    pygame.quit()
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)