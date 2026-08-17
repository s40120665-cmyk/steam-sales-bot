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
                return "Бесплатно", 0, 0
            
            price_info = data.get("price_overview", {})
            if price_info:
                price_raw = price_info.get("final", 0)
                initial_raw = price_info.get("initial", 0)
                discount = price_info.get("discount_percent", 0)
                return int(price_raw / 100), int(initial_raw / 100), discount
    except:
        pass
    return None, None, 0

def generate_html(games):
    """Генерация прокачанного сайта с поиском, сортировкой и серыми карточками без скидок"""
    html_start = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мониторинг цен Steam</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #1b2838; color: #c7d5e0; margin: 0; padding: 20px; }
        h1 { text-align: center; color: #fff; margin-bottom: 20px; font-weight: 600; }
        
        /* Стили для поиска */
        .search-container { max-width: 1000px; margin: 0 auto 20px auto; display: flex; justify-content: center; }
        #search-input { width: 100%; max-width: 400px; padding: 12px 20px; background-color: #162231; border: 1px solid #233c51; border-radius: 25px; color: #fff; font-size: 16px; outline: none; transition: border-color 0.3s; }
        #search-input:focus { border-color: #66c0f4; }

        .table-container { max-width: 1000px; margin: 0 auto; background: #162231; padding: 20px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #233c51; }
        th { background-color: #1f334b; color: #66c0f4; font-weight: bold; }
        
        /* Эффект затухания для игр без скидки */
        .no-discount-row { opacity: 0.5; transition: opacity 0.3s; }
        .no-discount-row:hover { opacity: 0.9; }
        tr:hover { background-color: #213143; }
        
        img { width: 120px; border-radius: 4px; display: block; }
        a { color: #66c0f4; text-decoration: none; font-weight: bold; }
        a:hover { text-decoration: underline; }
        
        /* Цветовые плашки скидок */
        .discount-cell { font-weight: bold; text-align: center; border-radius: 4px; padding: 6px 10px; color: #fff; display: inline-block; min-width: 45px; }
        .discount-high { background-color: #4CAF50; }
        .discount-medium { background-color: #ff9800; }
        .discount-low { background-color: #f44336; }
        .discount-none { background-color: #4a5a6a; color: #a0a0a0; }
    </style>
</head>
<body>
    <h1>🎮 Мониторинг цен Steam (Казахстан / РФ / США)</h1>
    
    <div class="search-container">
        <input type="text" id="search-input" placeholder="Поиск игры по названию..." onkeyup="filterGames()">
    </div>

    <div class="table-container">
        <table id="games-table">
            <thead>
                <tr>
                    <th>Обложка</th>
                    <th>Название игры</th>
                    <th style="text-align:center;">Скидка</th>
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

    <script>
    function filterGames() {
        var input = document.getElementById("search-input");
        var filter = input.value.toLowerCase();
        var table = document.getElementById("games-table");
        var tr = table.getElementsByTagName("tr");

        for (var i = 1; i < tr.length; i++) {
            var tdName = tr[i].getElementsByTagName("td");
            if (tdName) {
                var txtValue = tdName[1].textContent || tdName[1].innerText;
                if (txtValue.toLowerCase().indexOf(filter) > -1) {
                    tr[i].style.display = "";
                } else {
                    tr[i].style.display = "none";
                }
            }
        }
    }
    </script>
</body>
</html>"""
    
    table_rows = []
    for g in games:
        if g['discount'] == 0:
            color_class = "discount-none"
            row_class = 'class="no-discount-row"'
            discount_text = "0%"
        else:
            row_class = ""
            discount_text = f"-{g['discount']}%"
            if g['discount'] >= 70:
                color_class = "discount-high"
            elif 50 <= g['discount'] < 70:
                color_class = "discount-low"
            else:
                color_class = "discount-medium"
            
        img_url = f"{config.STEAM_IMAGE_BASE}{g['id']}/header.jpg"
        game_link = config.STEAM_STORE_APP_BASE + g['id']
        
        row = f"""
                <tr {row_class}>
                    <td><img src="{img_url}" alt="logo"></td>
                    <td><a href="{game_link}" target="_blank">{g['name']}</a></td>
                    <td style="text-align:center;"><span class="discount-cell {color_class}">{discount_text}</span></td>
                    <td>{g['price_kz']}</td>
                    <td>{g['price_ru']}</td>
                    <td>{g['price_us']}</td>
                </tr>"""
        table_rows.append(row)
        
    full_html = html_start + "\n".join(table_rows) + html_end
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    print("Сайт index.html успешно обновлен.")

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
    
    all_games_data = []
    tg_games_to_post = []

    print(f"Запуск полной проверки цен. Всего игр в списке: {len(target_games)}")
    
    for app_id, custom_name in target_games.items():
        kz_price, kz_initial, discount = get_price_for_region(app_id, "kz")
        time.sleep(0.5)
        
        if kz_price is not None:
            ru_price, _, _ = get_price_for_region(app_id, "ru")
            time.sleep(0.5)
            us_price, _, _ = get_price_for_region(app_id, "us")
            time.sleep(0.5)
            
            kz_text = f"{kz_price} ₸" if isinstance(kz_price, int) else "н/д"
            if kz_price == "Бесплатно": kz_text = "Бесплатно"
            
            ru_text = f"{ru_price} ₽" if isinstance(ru_price, int) else "не доступна в РФ ❌"
            if ru_price == "Бесплатно": ru_text = "Бесплатно"
                
            us_text = f"${us_price}" if isinstance(us_price, int) else "н/д"
            if us_price == "Бесплатно": us_text = "Бесплатно"

            game_entry = {
                "id": app_id,
                "name": custom_name,
                "discount": discount,
                "price_kz": kz_text,
                "price_ru": ru_text,
                "price_us": us_text
            }
            all_games_data.append(game_entry)
            
            if discount > 0:
                tg_games_to_post.append(game_entry)

    # На сайт выкатываем всё (сначала скидки, потом обычные цены)
    all_games_data.sort(key=lambda x: x['discount'], reverse=True)
    generate_html(all_games_data)

    # 4. Публикация ВДОЛЬ ВСЕХ игр со скидками в Телеграм пачками по 10 штук
    if tg_games_to_post:
        # Сортируем скидки от больших к меньшим для красивого отображения в постах
        tg_games_to_post.sort(key=lambda x: x['discount'], reverse=True)
        
        chunk_size = 10
        total_posted = 0
        
        for i in range(0, len(tg_games_to_post), chunk_size):
            chunk = tg_games_to_post[i:i + chunk_size]
            
            message_lines = ["🔥 **АКТУАЛЬНЫЕ РАСПРОДАЖИ В STEAM**\n"]
            for g in chunk:
                game_link = config.STEAM_STORE_APP_BASE + g['id']
                line = (
                    f"• **[{g['name']}]({game_link})** | `-{g['discount']}%`\n"
                    f"  🇰🇿 {g['price_kz']} | 🇷🇺 {g['price_ru']} | 🇺🇸 {g['price_us']}\n"
                )
                message_lines.append(line)
            
            full_text = "\n".join(message_lines)
            tg_url = config.TELEGRAM_API_BASE + bot_token + "/sendMessage"
            payload = {
                "chat_id": channel_id,
                "text": full_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            res = requests.post(tg_url, json=payload)
            if res.status_code == 200:
                total_posted += len(chunk)
                # Микропауза между отправками постов, чтобы избежать блокировок флуд-контроля Telegram
                time.sleep(1) 
                
        print(f"Успешно опубликованы абсолютно все активные скидки. Всего игр: {total_posted}")
    else:
        print("Активных скидок среди игр не обнаружено. Посты в ТГ не отправлялись.")

if __name__ == "__main__":
    main()
