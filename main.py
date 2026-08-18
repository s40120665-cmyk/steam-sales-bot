import os
import requests
import time
import json
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

def send_tg_message(token, chat_id, text):
    url = f"{config.TELEGRAM_API_BASE}{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        res = requests.post(url, json=payload).json()
        return res.get("result", {}).get("message_id")
    except:
        return None

def delete_tg_message(token, chat_id, message_id):
    url = f"{config.TELEGRAM_API_BASE}{token}/deleteMessage"
    try: requests.post(url, json={"chat_id": chat_id, "message_id": message_id})
    except: pass

def run_diagnostics(token, channel_id):
    """Проверка технического здоровья бота для вывода на сайт"""
    status_channel = "❌ Ошибка прав"
    url = f"{config.TELEGRAM_API_BASE}{token}/getChatAdministrators?chat_id={channel_id}"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("ok"): status_channel = "✅ Активно (Бот в админах)"
    except: pass
    return status_channel
def generate_html(games, system_status):
    """Генерация прокачанного сайта с поиском, сортировкой, серыми карточками и статусом системы"""
    html_start = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мониторинг цен Steam</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #1b2838; color: #c7d5e0; margin: 0; padding: 20px; }}
        h1 {{ text-align: center; color: #fff; margin-bottom: 20px; font-weight: 600; }}
        
        /* Плашка статуса системы прямо на сайте */
        .status-badge {{ max-width: 1000px; margin: 0 auto 20px auto; background: #162231; padding: 12px 20px; border-radius: 8px; border-left: 4px solid #66c0f4; font-size: 14px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }}
        .status-badge span {{ font-weight: bold; }}

        /* Стили для поиска */
        .search-container {{ max-width: 1000px; margin: 0 auto 20px auto; display: flex; justify-content: center; }}
        #search-input {{ width: 100%; max-width: 400px; padding: 12px 20px; background-color: #162231; border: 1px solid #233c51; border-radius: 25px; color: #fff; font-size: 16px; outline: none; transition: border-color 0.3s; }}
        #search-input:focus {{ border-color: #66c0f4; }}

        .table-container {{ max-width: 1000px; margin: 0 auto; background: #162231; padding: 20px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #233c51; }}
        th {{ background-color: #1f334b; color: #66c0f4; font-weight: bold; }}
        .no-discount-row {{ opacity: 0.5; transition: opacity 0.3s; }}
        .no-discount-row:hover {{ opacity: 0.9; }}
        tr:hover {{ background-color: #213143; }}
        img {{ width: 120px; border-radius: 4px; display: block; }}
        a {{ color: #66c0f4; text-decoration: none; font-weight: bold; }}
        a:hover {{ text-decoration: underline; }}
        .discount-cell {{ font-weight: bold; text-align: center; border-radius: 4px; padding: 6px 10px; color: #fff; display: inline-block; min-width: 45px; }}
        .discount-high {{ background-color: #4CAF50; }}
        .discount-medium {{ background-color: #ff9800; }}
        .discount-low {{ background-color: #f44336; }}
        .discount-none {{ background-color: #4a5a6a; color: #a0a0a0; }}
    </style>
</head>
<body>
    <h1>🎮 Мониторинг цен Steam (Казахстан / РФ / США)</h1>
    
    <div class="status-badge">
        <div>🛠️ Статус Telegram-канала: <span>{system_status}</span></div>
        <div style="color: #66c0f4;">Обновлено только что ⏱️</div>
    </div>

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
            <tbody>"""
    
    html_end = """</tbody></table></div>
    <script>
    function filterGames() {
        var filter = document.getElementById("search-input").value.toLowerCase();
        var tr = document.getElementById("games-table").getElementsByTagName("tr");
        for (var i = 1; i < tr.length; i++) {
            var td = tr[i].getElementsByTagName("td");
            if (td) {
                var txt = td.textContent || td.innerText;
                tr[i].style.display = txt.toLowerCase().indexOf(filter) > -1 ? "" : "none";
            }
        }
    }
    </script>
</body></html>"""
    
    table_rows = []
    for g in games:
        if g['discount'] == 0:
            color_class, row_class, discount_text = "discount-none", 'class="no-discount-row"', "0%"
        else:
            row_class, discount_text = "", f"-{g['discount']}%"
            if g['discount'] >= 70: color_class = "discount-high"
            elif 50 <= g['discount'] < 70: color_class = "discount-low"
            else: color_class = "discount-medium"
            
        row = f"""<tr {row_class}>
                    <td><img src="{config.STEAM_IMAGE_BASE}{g['id']}/header.jpg" alt="logo"></td>
                    <td><a href="{config.STEAM_STORE_APP_BASE}{g['id']}" target="_blank">{g['name']}</a></td>
                    <td style="text-align:center;"><span class="discount-cell {color_class}">{discount_text}</span></td>
                    <td>{g['price_kz']}</td><td>{g['price_ru']}</td><td>{g['price_us']}</td>
                </tr>"""
        table_rows.append(row)
        
    full_html = html_start + "\n".join(table_rows) + html_end
    with open("index.html", "w", encoding="utf-8") as f: f.write(full_html)
    print("Сайт index.html успешно обновлен.")

def main():
    LIST_FILE = "games_list.txt"
    HISTORY_FILE = "history.json"
    if not os.path.exists(LIST_FILE): return

    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    admin_id = os.environ.get("ADMIN_TELEGRAM_ID")

    target_games = {}
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.strip()
            if cleaned and ":" in cleaned:
                app_id, name = cleaned.split(":", 1)
                target_games[app_id.strip()] = name.strip()

    if not target_games: return

    old_history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: old_history = json.load(f)
        except: pass

    # Считываем force_update напрямую из скрытых параметров запуска пульта
    force_update = os.environ.get("FORCE_UPDATE") == "true"
    
    if force_update and admin_id:
        send_tg_message(bot_token, admin_id, "♻️ *Команда принудительного обновления принята!* Полностью очищаю старые посты в канале и перезаписываю базу...")
        if "posted_messages" in old_history:
            for m_id in old_history["posted_messages"]: delete_tg_message(bot_token, channel_id, m_id)
            old_history["posted_messages"] = []

    all_games_data, tg_games_to_post, admin_reports, new_history_data = [], [], [], {}

    print(f"Запуск гарантированной проверки цен. Всего игр: {len(target_games)}")
    for app_id, custom_name in target_games.items():
        kz_price, kz_initial, discount = None, None, 0
        
        for attempt in range(3):
            kz_price, kz_initial, discount = get_price_for_region(app_id, "kz")
            if kz_price is not None: break
            time.sleep(1.5)
            
        if kz_price is None:
            kz_text, ru_text, us_text, discount = "н/д", "н/д", "н/д", 0
        else:
            kz_text = f"{kz_price} ₸" if isinstance(kz_price, int) else "Бесплатно"
            ru_text = "не доступна в РФ ❌"
            us_text = "н/д"
            
            if discount > 0:
                for attempt in range(3):
                    ru_price, _, _ = get_price_for_region(app_id, "ru")
                    if ru_price is not None:
                        ru_text = f"{ru_price} ₽" if isinstance(ru_price, int) else "Бесплатно"
                        break
                    time.sleep(1)
                    
                for attempt in range(3):
                    us_price, _, _ = get_price_for_region(app_id, "us")
                    if us_price is not None:
                        us_text = f"${us_price}" if isinstance(us_price, int) else "Бесплатно"
                        break
                    time.sleep(1)
        
        time.sleep(0.8)
        game_entry = {"id": app_id, "name": custom_name, "discount": discount, "price_kz": kz_text, "price_ru": ru_text, "price_us": us_text}
        all_games_data.append(game_entry)
        new_history_data[app_id] = discount

        old_discount = old_history.get("discounts", {}).get(app_id, 0)
        if discount != old_discount:
            if old_discount == 0 and discount > 0: admin_reports.append(f"🟢 *Новая скидка!* {custom_name}: появился дисконт -{discount}%")
            elif old_discount > 0 and discount == 0: admin_reports.append(f"🔴 *Скидка кончилась!* {custom_name}: цена вернулась к обычной")
            else: admin_reports.append(f"🟡 *Изменение скидки!* {custom_name}: было -{old_discount}%, стало -{discount}%")

        if discount > 0: tg_games_to_post.append(game_entry)

    # Проверяем здоровье системы и отдаем на сайт
    system_status = run_diagnostics(bot_token, channel_id)
    all_games_data.sort(key=lambda x: x['discount'], reverse=True)
    generate_html(all_games_data, system_status)

    # ЛС Отчет для тебя
    if admin_id:
        if admin_reports:
            report_text = "📊 **ОТЧЕТ ОБ ИЗМЕНЕНИИ СКИДОК:**\n\n" + "\n".join(admin_reports)
            send_tg_message(bot_token, admin_id, report_text)
        elif force_update:
            send_tg_message(bot_token, admin_id, "✅ *Канал успешно очищен и перезаписан!* База синхронизирована.")
        else:
            send_tg_message(bot_token, admin_id, "🔎 *Проверка завершена:* Изменений в скидках с прошлой проверки нет. База стабильна.")

    new_posted_messages = old_history.get("posted_messages", [])
    if tg_games_to_post and (admin_reports or force_update or not new_posted_messages):
        if admin_reports and not force_update:
            for m_id in new_posted_messages: delete_tg_message(bot_token, channel_id, m_id)
            new_posted_messages = []

        tg_games_to_post.sort(key=lambda x: x['discount'], reverse=True)
        chunk_size = 10
        for i in range(0, len(tg_games_to_post), chunk_size):
            chunk = tg_games_to_post[i:i + chunk_size]
            message_lines = ["🔥 **АКТУАЛЬНЫЕ РАСПРОДАЖИ В STEAM**\n"]
            for g in chunk:
                line = f"• **[{g['name']}]({config.STEAM_STORE_APP_BASE}{g['id']})** | `-{g['discount']}%`\n  🇰🇿 {g['price_kz']} | 🇷🇺 {g['price_ru']} | 🇺🇸 {g['price_us']}\n"
                message_lines.append(line)
            
            m_id = send_tg_message(bot_token, channel_id, "\n".join(message_lines))
            if m_id: new_posted_messages.append(m_id)
            time.sleep(1)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"discounts": new_history_data, "posted_messages": new_posted_messages}, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
