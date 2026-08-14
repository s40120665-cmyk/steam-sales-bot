import os
import requests
import time
import config

def get_price_for_region(app_id, region_code):
    url = f"{config.STEAM_PRICE_API_BASE}{app_id}&cc={region_code}"
    try:
        res = requests.get(url, timeout=10).json()
        if res and res.get(app_id, {}).get("success"):
            data = res[app_id]["data"]
            if data.get("is_free"):
                return "Бесплатно", 0
            price_info = data.get("price_overview", {})
            if price_info:
                price_raw = price_info.get("final", 0)
                discount = price_info.get("discount_percent", 0)
                return int(price_raw / 100), discount
    except:
        pass
    return None, 0

def generate_html(games):
    """Функция генерации стильного сайта-таблицы с цветовым кодированием"""
    html_start = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мониторинг скидок Steam</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #1b2838; color: #c7d5e0; margin: 0; padding: 20px; }
        h1 { text-align: center; color: #fff; margin-bottom: 30px; }
        .table-container { max-width: 1000px; margin: 0 auto; background: #162231; padding: 20px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #233c51; }
        th { background-color: #1f334b; color: #66c0f4; font-weight: bold; }
        tr:hover { background-color: #213143; }
        img { width: 120px; border-radius: 4px; display: block; }
        a { color: #66c0f4; text-decoration: none; font-weight: bold; }
        a:hover { text-decoration: underline; }
        
        /* Цветовое кодирование ячеек скидок */
        .discount-cell { font-weight: bold; text-align: center; border-radius: 4px; padding: 6px; color: #fff; }
        .discount-high { background-color: #4CAF50; } /* Зеленый от 70% */
        .discount-medium { background-color: #f44336; } /* Красный от 50% до 70% */
        .discount-low { background-color: #ff9800; } /* Оранжевый ниже 50% */
    </style>
</head>
<body>
    <h1>🎮 Актуальные Скидки Steam (Казахстан / РФ / США)</h1>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Обложка</th>
                    <th>Название игры</th>
                    <th>Скидка</th>
                    <th>Цена КЗ</th>
                    <th>Цена РФ</th>
                    <th>Цена США</th>
                </tr>
            </thead>
            <tbody>
"""
    
    html_end = """
            </tbody>
        </table>
    </div>
</body>
</html>"""
    
    table_rows = []
    for g in games:
        # Логика определения цвета ячейки скидки
        if g['discount'] >= 70:
            color_class = "discount-high"
        elif 50 <= g['discount'] < 70:
            color_class = "discount-medium"
        else:
            color_class = "discount-low"
            
        img_url = f"{config.STEAM_IMAGE_BASE}{g['id']}/header.jpg"
        game_link = config.STEAM_STORE_APP_BASE + g['id']
        
        row = f"""
                <tr>
                    <td><img src="{img_url}" alt="logo"></td>
                    <td><a href="{game_link}" target="_blank">{g['name']}</a></td>
                    <td><span class="discount-cell {color_class}">-{g['discount']}%</span></td>
                    <td>{g['price_kz']} ₸</td>
                    <td>{g['price_ru']}</td>
                    <td>{g['price_us']}</td>
                </tr>"""
        table_rows.append(row)
        
    full_html = html_start + "\n".join(table_rows) + html_end
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    print("Сайт index.html успешно сгенерирован.")

def main():
    LIST_FILE = "games_list.txt"
    if not os.path.exists(LIST_FILE): return

    target_games = {}
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            cleaned_line = line.strip()
            if not cleaned_line or ":" not in cleaned_line: continue
            try:
                app_id, name = cleaned_line.split(":", 1)
                target_games[app_id.strip()] = name.strip()
            except: continue

    if not target_games: return

    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    all_discounted_games = []

    for app_id, custom_name in target_games.items():
        kz_price, discount = get_price_for_region(app_id, "kz")
        time.sleep(0.5)
        
        if discount > 0 and kz_price is not None:
            ru_price, _ = get_price_for_region(app_id, "ru")
            time.sleep(0.5)
            us_price, _ = get_price_for_region(app_id, "us")
            time.sleep(0.5)
            
            ru_text = f"{ru_price} ₽" if isinstance(ru_price, int) else "не доступна в РФ ❌"
            us_text = f"${us_price}" if isinstance(us_price, int) else "н/д"

            all_discounted_games.append({
                "id": app_id,
                "name": custom_name,
                "discount": discount,
                "price_kz": kz_price,
                "price_ru": ru_text,
                "price_us": us_text
            })

    # Создаем сайт, если нашли игры со скидками
    if all_discounted_games:
        generate_html(all_discounted_games)
        
        # Опционально: отправляем в Телеграм ссылку на ваш будущий сайт!
        # Текст ссылки мы добавим в Шаге 4
    else:
        # Если скидок нет, создаем пустую страницу с надписью
        with open("index.html", "w", encoding="utf-8") as f:
            f.write("<html><body style='background:#1b2838;color:#fff;text-align:center;padding:50px;'><h1>Скидок пока нет, загляните позже!</h1></body></html>")

if __name__ == "__main__":
    main()
