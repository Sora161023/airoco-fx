# -*- coding: utf-8 -*-
import pygame
import sys
import time, csv, requests, datetime
import numpy as np

# 過去7日間のCO2濃度データをAPIから取得する関数 get_past_7_days_co2
def get_airoco_data():
    curr_time = int(time.time())
    data = []

    airoco_url = 'https://airoco.necolico.jp/data-api/day-csv'
    id = 'CgETViZ2'
    subscription_key = '6b8aa7133ece423c836c38af01c59880'
    
    # 過去7日間のデータを日ごとに取得
    for i in range(7, 0, -1):
        tt = curr_time - 3600 * 24 * i
        try:
            res = requests.get(f'{airoco_url}?id={id}&subscription-key={subscription_key}&startDate={tt}')
            res.raise_for_status()  # HTTPエラーがあれば例外を発生
            raw_data = csv.reader(res.text.strip().splitlines())

            for row in raw_data:
                if row[1] == 'Ｒ３ー４０１':
                    data.append(list(map(float, row[3:7])))  # CO2濃度, 気温, 湿度, タイムスタンプ
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            continue

    if not data:
        print("This sensor is not connected or no data available.")
        return [], [], [], []

    data = np.array(data)

    timestamps = [datetime.datetime.fromtimestamp(ts) for ts in data[:, 3]]
    co2_values = data[:, 0].tolist()  # CO2濃度
    temp_values = data[:, 1].tolist()  # 気温
    humid_values = data[:, 2].tolist()  # 湿度
    
    return timestamps, co2_values, temp_values, humid_values

# 既存のデータと新しいデータをマージする関数
def update_data(now_timestamps, now_co2, now_temp, now_humid):
    """APIから新しいデータを取得し、既存のデータとマージする"""
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] データの更新を開始します...")
    
    # データを再取得
    new_timestamps, new_co2, new_temp, new_humid = get_airoco_data()
    
    # データ取得失敗時の処理
    if not new_timestamps:
        print("更新データが取得できませんでした。")
        return now_timestamps, now_co2, now_temp, now_humid

    # 現在の時刻を取得
    last_timestamp = now_timestamps[-1] if now_timestamps else datetime.datetime.fromtimestamp(0)
    
    added_count = 0 # 追加したデータの数のカウント用

    # 新しいデータの中に、まだ持っていないものがあれば追加する
    for i, ts in enumerate(new_timestamps):     # enumerateでインデックスと時刻を同時に取得
        if ts > last_timestamp:                 # 所持してた時刻より新しい時刻のデータの場合追加
            now_timestamps.append(ts)
            now_co2.append(new_co2[i])
            now_temp.append(new_temp[i])
            now_humid.append(new_humid[i])
            added_count += 1
    
    # 追加したかどうかのログ
    if added_count > 0:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {added_count}件の新しいデータを追加しました。")
    else:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 新しいデータはありませんでした。")
        
    return now_timestamps, now_co2, now_temp, now_humid


# --- Pygame 初期化 ---
pygame.init()
screen = pygame.display.set_mode((500, 600))    # ウィンドウサイズを500x600に設定
pygame.display.set_caption("Airoco株ゲーム")    # タイトル設定
font = pygame.font.SysFont("Meiryo", 18)        # フォント設定
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
UPDATE_INTERVAL_MS = 150000  # データ更新間隔を150秒に設定
pygame.time.set_timer(UPDATE_DATA_EVENT, UPDATE_INTERVAL_MS)

# --- データ取得 ---
timestamps, co2_values, temp_values, humid_values = get_airoco_data()
# 初期データ格納庫
select_code = {
    "co2": {"value": co2_values, "label": "CO₂", "unit": "ppm"},
    "temp": {"value": temp_values, "label": "気温", "unit": "°C"},
    "humid": {"value": humid_values, "label": "湿度", "unit": "%"}
}
print(f"CO2の初期データ数: {len(co2_values)}件")
print(f"気温の初期データ数: {len(temp_values)}件")
print(f"湿度の初期データ数: {len(humid_values)}件")

now_graph = "co2"  # 現在表示中のグラフの種類

# --- ゲーム変数 ---
INITIAL_MONEY = 100000 # 初期所持金
money = INITIAL_MONEY
stocks = {
    "co2": {"stock" : 0, "then_price" : 0, "profit": 0},  # CO2株の保有数と購入価格と利益
    "temp": {"stock" : 0, "then_price" : 0, "profit": 0}, # 気温株の保有数と購入価格と利益
    "humid": {"stock" : 0, "then_price" : 0, "profit": 0} # 湿度株の保有数と購入価格と利益
}

# --- レイアウト定義 ---
GRAPH_RECT = pygame.Rect(50, 60, 400, 280)  # 基本のグラフ表示領域
SCROLL_BAR_RECT = pygame.Rect(GRAPH_RECT.left, GRAPH_RECT.bottom + 75, GRAPH_RECT.width, 10) 
HANDLE_WIDTH = 40 
handle_rect = pygame.Rect(SCROLL_BAR_RECT.left, SCROLL_BAR_RECT.top - 5, HANDLE_WIDTH, 20)
UI_AREA_Y = SCROLL_BAR_RECT.bottom + 3  # UIエリアのY座標
WINDOW_SIZE = 288   # 1日分のデータ数
scroll_index = max(0, len(select_code[now_graph]["value"]) - WINDOW_SIZE)  # スクロール位置の最初の位置（例: 1200件-288件目でスクロール開始位置が912番目から）
dragging = False

# ボタンの定義
BUTTON_WIDTH, BUTTON_HEIGHT = 50, 30
CO2_BUTTON_RECT = pygame.Rect(GRAPH_RECT.left, 20, BUTTON_WIDTH, BUTTON_HEIGHT)
TEMP_BUTTON_RECT = pygame.Rect(CO2_BUTTON_RECT.right + 10, 20, BUTTON_WIDTH, BUTTON_HEIGHT)
HUMID_BUTTON_RECT = pygame.Rect(TEMP_BUTTON_RECT.right + 10, 20, BUTTON_WIDTH, BUTTON_HEIGHT)
button_map = {
    'co2': CO2_BUTTON_RECT,
    'temp': TEMP_BUTTON_RECT,
    'humid': HUMID_BUTTON_RECT,
}

def update_handle_position():
    """scroll_indexに基づいてスクロールバーハンドルの位置を更新する"""
    max_scroll = max(0, len(select_code[now_graph]["value"]) - WINDOW_SIZE)
    if max_scroll > 0:
        scroll_ratio = scroll_index / max_scroll
        handle_rect.x = SCROLL_BAR_RECT.left + scroll_ratio * (SCROLL_BAR_RECT.width - HANDLE_WIDTH)
    else:
        handle_rect.x = SCROLL_BAR_RECT.left

# 累計収益を表示するヘッダー情報を描画する関数
def draw_header_info(profit):
    if profit >= 0:
        profit_color, sign = COLOR_BLUE, "+"
    else:
        profit_color, sign = COLOR_RED, ""
    profit_text = font_l.render(f"累計収益: ¥{sign}{profit:,}", True, profit_color)
    screen.blit(profit_text, (GRAPH_RECT.right - profit_text.get_width(), 25))

# グラフの種類を選択するボタンを描画する関数
def draw_buttons(active_type):
    for type_name, rect in button_map.items():
        color = COLOR_BUTTON_ACTIVE if type_name == active_type else COLOR_BUTTON
        pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, COLOR_BLACK, rect, 1, border_radius=5)
        text_surf = font.render(select_code[type_name]["label"], True, COLOR_BLACK)
        screen.blit(text_surf, text_surf.get_rect(center=rect.center))

# グラフを描画する関数
def draw_graph(prices, times, start_index, unit):

    """グラフを描画する"""
    pygame.draw.rect(screen, COLOR_WHITE, GRAPH_RECT) # グラフ背景
    
    end_index = min(start_index + WINDOW_SIZE, len(prices)) # 表示するデータの終端インデックス
    visible_prices = prices[start_index:end_index]
    visible_times = times[start_index:end_index]

    # データが不足している場合の処理
    if len(visible_prices) < 2:
        msg = font.render("データが不足しています", True, COLOR_BLACK)
        screen.blit(msg, msg.get_rect(center=GRAPH_RECT.center))
        pygame.draw.rect(screen, COLOR_BLACK, GRAPH_RECT, 1) # 枠線だけ描画
        return

    # グラフのスケーリング処理
    max_price = max(visible_prices)
    min_price = min(visible_prices)
    price_range = max_price - min_price
    if price_range == 0: price_range = 1

    # グラフの軸の幅
    scale_x = GRAPH_RECT.width / (len(visible_prices) - 1) if len(visible_prices) > 1 else 0
    scale_y = (GRAPH_RECT.height - 40) / price_range 

    points = []
    for i in range(len(visible_prices)):
        x = GRAPH_RECT.left + i * scale_x                                           # X座標の位置
        y = GRAPH_RECT.bottom - 20 - (visible_prices[i] - min_price) * scale_y      # Y座標の位置
        points.append((x, y))   # points[i] = (x座標, y座標)
    if len(points) > 1:
        pygame.draw.lines(screen, COLOR_GREEN, False, points, 2)

    # Y軸の目盛り
    for i in range(5):
        price = min_price + (price_range / 4 * i)   # 目盛りの値
        y = GRAPH_RECT.bottom - 20 - (price - min_price) * scale_y      # Y座標の位置
        label = font_s.render(f"{int(price)}", True, COLOR_BLACK)
        screen.blit(label, (GRAPH_RECT.left - 40, y - label.get_height()/2))
        pygame.draw.line(screen, COLOR_SCROLL_BG, (GRAPH_RECT.left-5, y), (GRAPH_RECT.left, y))     # 補助線
    # Y軸の単位ラベル
    unit_label = font_s.render(f"({unit})", True, COLOR_BLACK)
    screen.blit(unit_label, (GRAPH_RECT.left - 35, GRAPH_RECT.top - 5))

    # X軸の目盛りとラベルを描画
    num_labels = 5 
    step = max(1, len(visible_times) // num_labels)
    for i in range(0, len(visible_times), step):    # 0からvisible_timesの長さまでstep間隔でループ
        x = GRAPH_RECT.left + i * scale_x
        label_text = visible_times[i].strftime("%m/%d %H:%M")
        label = font_s.render(label_text, True, COLOR_BLACK)
        label = pygame.transform.rotate(label, 45)  # ラベルを45度回転
        screen.blit(label, (x - 15, GRAPH_RECT.bottom + 10))

    # 現在位置の縦線
    indicator_x = GRAPH_RECT.left + (len(visible_prices) - 1) * scale_x
    pygame.draw.line(screen, COLOR_INDICATOR, (indicator_x, GRAPH_RECT.top), (indicator_x, GRAPH_RECT.bottom), 1)

    # グラフの枠線を描画
    pygame.draw.rect(screen, COLOR_BLACK, GRAPH_RECT, 1)

# ユーザーインターフェースを描画する関数
def draw_ui(price, money_val, stock_val):
    status_y_start = UI_AREA_Y + 20
    
    # ステータス表示
    price_text = font.render(f"現在値: {price:.2f} rco", True, COLOR_BLACK)
    screen.blit(price_text, (GRAPH_RECT.left, status_y_start))
    money_text = font.render(f"所持金: ¥{money_val:,}", True, COLOR_BLACK)
    screen.blit(money_text, (GRAPH_RECT.left, status_y_start + 40))
    stock_text = font.render(f"保有株: {stock_val[now_graph]['stock']}株", True, COLOR_BLACK)
    screen.blit(stock_text, (GRAPH_RECT.left, status_y_start + 80))
    
    # 操作説明
    help_x = screen.get_width()/2 + 40
    buy_text = font.render("Bキー: 買う", True, COLOR_BLUE)
    sell_text = font.render("Sキー: 売る", True, COLOR_RED)
    scroll_text = font.render("←→: スクロール", True, COLOR_BLACK)
    attention_text = font.render("※CO2株は1株単位、気温・湿度株は10株単位で購入", True, COLOR_BLACK)    # 注意書き
    screen.blit(buy_text, (help_x, status_y_start))
    screen.blit(sell_text, (help_x, status_y_start + 40))
    screen.blit(scroll_text, (help_x, status_y_start + 80))
    # 注意書きの中央揃え
    center = (screen.get_width() - attention_text.get_width()) // 2
    screen.blit(attention_text, (center, status_y_start + 120))

def draw_scrollbar():
    """スクロールバーを描画する"""
    pygame.draw.rect(screen, COLOR_SCROLL_BG, SCROLL_BAR_RECT)
    pygame.draw.rect(screen, COLOR_SCROLL_HANDLE, handle_rect, border_radius=5)

# --- メインループ ---
running = True
update_handle_position()

while running:

    active_prices = select_code[now_graph]['value']     # 表示の対象（CO2, 気温, 湿度）
    active_unit = select_code[now_graph]['unit']        # 表示の単位（ppm, °C, %）
    max_scroll_len = len(active_prices) - WINDOW_SIZE   # スクロール可能な最大長さ

    # --- イベント処理 ---    1フレーム毎にイベントを取得
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # --- データ更新イベント ---
        elif event.type == UPDATE_DATA_EVENT:
            was_at_end = scroll_index >= max_scroll_len - 1
            # データを更新
            timestamps, co2_values, temp_values, humid_values = update_data(timestamps, co2_values, temp_values, humid_values)
            # 末尾にスクロールしていた場合、更新後も末尾に留まるようにする
            if was_at_end:
                scroll_index = max(0, len(active_prices) - WINDOW_SIZE)
            update_handle_position()

        # --- キー入力イベント ---
        elif event.type == pygame.KEYDOWN:
            current_price_index = min(scroll_index + WINDOW_SIZE - 1, len(active_prices) - 1)
            if current_price_index < 0: continue
            current_price = active_prices[current_price_index]

            # Bキー : 株を買う操作
            if event.key == pygame.K_b and money >= current_price:
                if now_graph == "temp" or now_graph == "humid":
                    stock_quantity = 10
                else:
                    stock_quantity = 1
                    
                if money >= current_price * stock_quantity:  # 購入可能な金額か確認
                    stocks[now_graph]["stock"] += stock_quantity
                    stocks[now_graph]["then_price"] += current_price * stock_quantity  # 購入時の価格を記録
                    money -= int(current_price * stock_quantity)

            # Sキー　: 株を売る操作
            elif event.key == pygame.K_s and stocks[now_graph]["stock"] > 0:
                stocks[now_graph]["stock"] -= 1
                money += int(current_price * 0.9)  # 売却時は10%の手数料を引く

        # --- マウス入力 ---
        # マウスボタンが押されたとき
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if handle_rect.collidepoint(event.pos):
                dragging = True
                mouse_x_offset = event.pos[0] - handle_rect.x
            else:
                for type_name, rect in button_map.items():
                    if rect.collidepoint(event.pos):    # 
                        now_graph = type_name
                        scroll_index = max(0, len(select_code[now_graph]["value"]) - WINDOW_SIZE)
                        update_handle_position()
                        break
        
        # マウスボタンが離されたとき
        elif event.type == pygame.MOUSEBUTTONUP:    
            dragging = False

        # マウスが動いたとき
        elif event.type == pygame.MOUSEMOTION:
            if dragging:
                new_x = event.pos[0] - mouse_x_offset
                handle_rect.x = max(SCROLL_BAR_RECT.left, min(new_x, SCROLL_BAR_RECT.right - HANDLE_WIDTH))
                if (SCROLL_BAR_RECT.width - HANDLE_WIDTH) > 0:
                    scroll_ratio = (handle_rect.x - SCROLL_BAR_RECT.left) / (SCROLL_BAR_RECT.width - HANDLE_WIDTH)
                    scroll_index = int(scroll_ratio * max_scroll_len)
                    
    # --- 長押し対応 ---
    pressedkeys = pygame.key.get_pressed()
    scroll_speed = 1 # スクロールで移動する量
    scroll_frame = 6 # スクロールのフレーム数 60FPSのため、0.1秒ごとになるように調整
    # →キー : スクロールバーを右に移動
    if pressedkeys[pygame.K_RIGHT]:
        scroll_counter += 1
        if scroll_counter % scroll_frame == 0:  # scroll_frameフレームごとにスクロール
            scroll_index = min(scroll_index + scroll_speed, max_scroll_len) # 末尾を超えないようにする
            update_handle_position() 
    # ←キー : スクロールバーを左に移動
    elif pressedkeys[pygame.K_LEFT]:
        scroll_counter += 1
        if scroll_counter % scroll_frame == 0:  # scroll_frameフレームごとにスクロール
            scroll_index = max(0, scroll_index - scroll_speed) # 先頭を超えないようにする
            update_handle_position()
    else:
        scroll_counter = 0  # キーを離したらカウンターをリセット

    # --- 画面描画 ---
    screen.fill(COLOR_BG)
    current_price_index = min(scroll_index + WINDOW_SIZE - 1, len(active_prices) - 1)
    current_price = active_prices[current_price_index] if current_price_index >= 0 else 0

    # 収益計算
    total_assets = money + stocks[now_graph]["stock"] * current_price
    profit = total_assets - INITIAL_MONEY

    # 各株の利益を計算
    for graph_type in select_code:
        stocks[graph_type]["profit"] = (stocks[graph_type]["stock"] * current_price ) - stocks[graph_type]["then_price"]

    # 描画関数の呼び出しs
    draw_buttons(now_graph)
    draw_header_info(stocks[now_graph]["profit"])
    draw_graph(active_prices, timestamps, scroll_index, active_unit)
    draw_ui(current_price, money, stocks)
    draw_scrollbar()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()