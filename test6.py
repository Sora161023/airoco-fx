# -*- coding: utf-8 -*-
import pygame
import sys
import time, csv, requests, datetime
import numpy as np

def get_data(initial_load=True):
    """
    過去7日間のセンサーデータをAPIから取得する関数
    (CO2, 気温, 湿度)
    """
    curr_time = int(time.time())
    data = []

    for i in range(7, 0, -1):
        tt = curr_time - 3600 * 24 * i
        try:
            res = requests.get(f'https://airoco.necolico.jp/data-api/day-csv?id=CgETViZ2&subscription-key=6b8aa7133ece423c836c38af01c59880&startDate={tt}')
            res.raise_for_status()
            raw_text = res.content.decode('utf-8-sig')
            raw_data = csv.reader(raw_text.strip().splitlines())
            next(raw_data, None)

            for row in raw_data:
                if len(row) >= 7 and row[1] == 'Ｒ３ー４０１':
                    try:
                        # CO2, 気温, 湿度, タイムスタンプ の順でデータを取得
                        data.append(list(map(float, [row[3], row[4], row[5], row[6]])))
                    except (ValueError, IndexError):
                        pass

        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            continue
    
    if not data:
        if initial_load:
            print("センサーデータが取得できませんでした。ダミーデータを生成します。")
            end_time = datetime.datetime.now()
            timestamps = [end_time - datetime.timedelta(minutes=5*i) for i in range(1000)]
            timestamps.reverse()
            co2_values = [600 + 100 * np.sin(i / 50) + np.random.randint(-20, 20) for i in range(1000)]
            temp_values = [25 + 5 * np.sin(i/100) + np.random.uniform(-1, 1) for i in range(1000)]
            humid_values = [50 + 15 * np.sin(i/75) + np.random.uniform(-3, 3) for i in range(1000)]
            return timestamps, co2_values, temp_values, humid_values
        else:
            return [], [], [], []

    data_np = np.array(data)
    sorted_indices = np.argsort(data_np[:, 3]) # タイムスタンプでソート
    data_np = data_np[sorted_indices]
    
    timestamps = [datetime.datetime.fromtimestamp(ts) for ts in data_np[:, 3]]
    co2_values = list(data_np[:, 0])
    temp_values = list(data_np[:, 1])
    humid_values = list(data_np[:, 2])
    
    return timestamps, co2_values, temp_values, humid_values

def update_data(current_timestamps, current_co2, current_temp, current_humid):
    """APIから新しいデータを取得し、既存のデータとマージする"""
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] データの更新を開始します...")
    
    new_timestamps, new_co2, new_temp, new_humid = get_data(initial_load=False)
    
    if not new_timestamps:
        print("更新データが取得できませんでした。")
        return current_timestamps, current_co2, current_temp, current_humid

    last_known_timestamp = current_timestamps[-1] if current_timestamps else datetime.datetime.fromtimestamp(0)
    
    added_count = 0
    for i, ts in enumerate(new_timestamps):
        if ts > last_known_timestamp:
            current_timestamps.append(ts)
            current_co2.append(new_co2[i])
            current_temp.append(new_temp[i])
            current_humid.append(new_humid[i])
            added_count += 1
    
    if added_count > 0:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {added_count}件の新しいデータを追加しました。")
    else:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 新しいデータはありませんでした。")
        
    return current_timestamps, current_co2, current_temp, current_humid

# --- Pygame 初期化 ---
pygame.init()
screen = pygame.display.set_mode((500, 600)) 
pygame.display.set_caption("センサー株ゲーム")
font = pygame.font.SysFont("Meiryo", 18) 
font_s = pygame.font.SysFont("Meiryo", 12)
font_l = pygame.font.SysFont("Meiryo", 22)
clock = pygame.time.Clock()

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

# --- データ更新イベント定義 ---
UPDATE_DATA_EVENT = pygame.USEREVENT + 1
UPDATE_INTERVAL_MS = 30000 
pygame.time.set_timer(UPDATE_DATA_EVENT, UPDATE_INTERVAL_MS)

# --- データ取得 & マッピング ---
timestamps, co2_prices, temp_prices, humid_prices = get_data()
data_map = {
    'co2': {'prices': co2_prices, 'unit': 'ppm', 'name': 'CO2'},
    'temp': {'prices': temp_prices, 'unit': '°C', 'name': '気温'},
    'humid': {'prices': humid_prices, 'unit': '%', 'name': '湿度'},
}
current_graph_type = 'co2' # 初期表示

# --- ゲーム変数 ---
INITIAL_MONEY = 100000 
money = INITIAL_MONEY
stock = 0

# --- レイアウト定義 ---
GRAPH_RECT = pygame.Rect(50, 60, 400, 280) 
SCROLL_BAR_RECT = pygame.Rect(GRAPH_RECT.left, GRAPH_RECT.bottom + 75, GRAPH_RECT.width, 10) 
HANDLE_WIDTH = 40 
handle_rect = pygame.Rect(SCROLL_BAR_RECT.left, SCROLL_BAR_RECT.top - 5, HANDLE_WIDTH, 20)
UI_AREA_Y = SCROLL_BAR_RECT.bottom + 30
WINDOW_SIZE = 288 
scroll_index = max(0, len(data_map[current_graph_type]['prices']) - WINDOW_SIZE) 
dragging = False

# ボタンの定義
BUTTON_WIDTH, BUTTON_HEIGHT = 80, 30
CO2_BUTTON_RECT = pygame.Rect(GRAPH_RECT.left, 20, BUTTON_WIDTH, BUTTON_HEIGHT)
TEMP_BUTTON_RECT = pygame.Rect(CO2_BUTTON_RECT.right + 10, 20, BUTTON_WIDTH, BUTTON_HEIGHT)
HUMID_BUTTON_RECT = pygame.Rect(TEMP_BUTTON_RECT.right + 10, 20, BUTTON_WIDTH, BUTTON_HEIGHT)
button_map = {
    'co2': CO2_BUTTON_RECT,
    'temp': TEMP_BUTTON_RECT,
    'humid': HUMID_BUTTON_RECT,
}

def update_handle_position():
    max_scroll = max(0, len(data_map[current_graph_type]['prices']) - WINDOW_SIZE)
    if max_scroll > 0:
        scroll_ratio = scroll_index / max_scroll
        handle_rect.x = SCROLL_BAR_RECT.left + scroll_ratio * (SCROLL_BAR_RECT.width - HANDLE_WIDTH)
    else:
        handle_rect.x = SCROLL_BAR_RECT.left

def draw_header_info(profit):
    if profit >= 0:
        profit_color, sign = COLOR_BLUE, "+"
    else:
        profit_color, sign = COLOR_RED, ""
    profit_text = font_l.render(f"累計収益: ¥{sign}{profit:,}", True, profit_color)
    screen.blit(profit_text, (GRAPH_RECT.right - profit_text.get_width(), 25))

def draw_buttons(active_type):
    for type_name, rect in button_map.items():
        color = COLOR_BUTTON_ACTIVE if type_name == active_type else COLOR_BUTTON
        pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, COLOR_BLACK, rect, 1, border_radius=5)
        text_surf = font.render(data_map[type_name]['name'], True, COLOR_BLACK)
        screen.blit(text_surf, text_surf.get_rect(center=rect.center))

def draw_graph(prices, times, start_index, unit):
    pygame.draw.rect(screen, COLOR_WHITE, GRAPH_RECT) 
    
    end_index = min(start_index + WINDOW_SIZE, len(prices))
    visible_prices = prices[start_index:end_index]
    visible_times = times[start_index:end_index]

    if len(visible_prices) < 2:
        msg = font.render("データが不足しています", True, COLOR_BLACK)
        screen.blit(msg, msg.get_rect(center=GRAPH_RECT.center))
        pygame.draw.rect(screen, COLOR_BLACK, GRAPH_RECT, 1)
        return

    max_price = max(visible_prices) if visible_prices else 0
    min_price = min(visible_prices) if visible_prices else 0
    price_range = max_price - min_price
    if price_range == 0: price_range = 1

    scale_x = GRAPH_RECT.width / (len(visible_prices) - 1) if len(visible_prices) > 1 else 0
    scale_y = (GRAPH_RECT.height - 40) / price_range 

    points = []
    for i in range(len(visible_prices)):
        x = GRAPH_RECT.left + i * scale_x
        y = GRAPH_RECT.bottom - 20 - (visible_prices[i] - min_price) * scale_y
        points.append((x, y))
    if len(points) > 1:
        pygame.draw.lines(screen, COLOR_GREEN, False, points, 2)

    for i in range(5):
        price = min_price + (price_range / 4 * i)
        y = GRAPH_RECT.bottom - 20 - (price - min_price) * scale_y
        label = font_s.render(f"{price:.1f}", True, COLOR_BLACK)
        screen.blit(label, (GRAPH_RECT.left - 40, y - label.get_height()/2))
        pygame.draw.line(screen, COLOR_SCROLL_BG, (GRAPH_RECT.left-5, y), (GRAPH_RECT.left, y))

    unit_label = font_s.render(f"({unit})", True, COLOR_BLACK)
    screen.blit(unit_label, (GRAPH_RECT.left - 35, GRAPH_RECT.top - 5))

    num_labels = 5 
    step = max(1, len(visible_times) // num_labels)
    for i in range(0, len(visible_times), step):
        x = GRAPH_RECT.left + i * scale_x
        label_text = visible_times[i].strftime("%m/%d %H:%M")
        label = font_s.render(label_text, True, COLOR_BLACK)
        label = pygame.transform.rotate(label, 45) 
        screen.blit(label, (x - 15, GRAPH_RECT.bottom + 10))

    indicator_x = GRAPH_RECT.left + (len(visible_prices) - 1) * scale_x
    pygame.draw.line(screen, COLOR_INDICATOR, (indicator_x, GRAPH_RECT.top), (indicator_x, GRAPH_RECT.bottom), 1)
    pygame.draw.rect(screen, COLOR_BLACK, GRAPH_RECT, 1)

def draw_ui(price, money_val, stock_val, unit):
    status_y_start = UI_AREA_Y + 20
    price_text = font.render(f"現在値: {price:.2f} {unit}", True, COLOR_BLACK)
    screen.blit(price_text, (GRAPH_RECT.left, status_y_start))
    money_text = font.render(f"所持金: ¥{money_val:,}", True, COLOR_BLACK)
    screen.blit(money_text, (GRAPH_RECT.left, status_y_start + 40))
    stock_text = font.render(f"保有株: {stock_val} 株", True, COLOR_BLACK)
    screen.blit(stock_text, (GRAPH_RECT.left, status_y_start + 80))
    help_x = screen.get_width()/2 + 40
    buy_text = font.render("Bキー: 買う", True, COLOR_BLUE)
    sell_text = font.render("Sキー: 売る", True, COLOR_RED)
    scroll_text = font.render("←→: スクロール", True, COLOR_BLACK)
    screen.blit(buy_text, (help_x, status_y_start))
    screen.blit(sell_text, (help_x, status_y_start + 40))
    screen.blit(scroll_text, (help_x, status_y_start + 80))

def draw_scrollbar():
    pygame.draw.rect(screen, COLOR_SCROLL_BG, SCROLL_BAR_RECT)
    pygame.draw.rect(screen, COLOR_SCROLL_HANDLE, handle_rect, border_radius=5)

# --- メインループ ---
running = True
update_handle_position()

while running:
    active_prices = data_map[current_graph_type]['prices']
    active_unit = data_map[current_graph_type]['unit']
    max_scroll_len = len(active_prices) - WINDOW_SIZE

    # --- イベント処理 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == UPDATE_DATA_EVENT:
            was_at_end = scroll_index >= max_scroll_len - 1
            timestamps, co2_prices, temp_prices, humid_prices = update_data(timestamps, co2_prices, temp_prices, humid_prices)
            if was_at_end:
                scroll_index = max(0, len(active_prices) - WINDOW_SIZE)
            update_handle_position()

        elif event.type == pygame.KEYDOWN:
            current_price_index = min(scroll_index + WINDOW_SIZE - 1, len(active_prices) - 1)
            if current_price_index < 0: continue
            current_price = active_prices[current_price_index]

            if event.key == pygame.K_b and money >= current_price:
                stock += 1
                money -= int(current_price)
            elif event.key == pygame.K_s and stock > 0:
                stock -= 1
                money += int(current_price)
            
            scroll_speed = 10 
            if event.key == pygame.K_RIGHT:
                scroll_index = min(scroll_index + scroll_speed, max_scroll_len)
                update_handle_position() 
            elif event.key == pygame.K_LEFT:
                scroll_index = max(scroll_index - scroll_speed, 0)
                update_handle_position() 

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if handle_rect.collidepoint(event.pos):
                dragging = True
                mouse_x_offset = event.pos[0] - handle_rect.x
            else:
                for type_name, rect in button_map.items():
                    if rect.collidepoint(event.pos):
                        current_graph_type = type_name
                        # グラフを切り替えたらスクロール位置を最新にリセット
                        scroll_index = max(0, len(data_map[current_graph_type]['prices']) - WINDOW_SIZE)
                        update_handle_position()
                        break
        elif event.type == pygame.MOUSEBUTTONUP:
            dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if dragging:
                new_x = event.pos[0] - mouse_x_offset
                handle_rect.x = max(SCROLL_BAR_RECT.left, min(new_x, SCROLL_BAR_RECT.right - HANDLE_WIDTH))
                if (SCROLL_BAR_RECT.width - HANDLE_WIDTH) > 0:
                    scroll_ratio = (handle_rect.x - SCROLL_BAR_RECT.left) / (SCROLL_BAR_RECT.width - HANDLE_WIDTH)
                    scroll_index = int(scroll_ratio * max_scroll_len)

    # --- 画面描画 ---
    screen.fill(COLOR_BG)
    current_price_index = min(scroll_index + WINDOW_SIZE - 1, len(active_prices) - 1)
    current_price = active_prices[current_price_index] if current_price_index >= 0 else 0 

    total_assets = money + stock * current_price
    profit = int(total_assets - INITIAL_MONEY)

    draw_buttons(current_graph_type)
    draw_header_info(profit)
    draw_graph(active_prices, timestamps, scroll_index, active_unit)
    draw_ui(current_price, money, stock, active_unit)
    draw_scrollbar()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
