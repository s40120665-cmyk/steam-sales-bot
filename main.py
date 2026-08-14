import os
import requests
import time
import config

def get_price_for_region(app_id, region_code):
    """Вспомогательная функция для безопасного запроса цены в конкретном регионе"""
    url = f"{config.STEAM_PRICE_API_BASE}{app_id}&cc={region_code}"
    try:
        res = requests.get(url, timeout=10).json()
        if res and res.get(app_id, {}).get("success"):
            data = res[app_id]["data"]
            # Если игра бесплатная
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

def main():
    LIST_FILE = "games_list.txt"

    if not os.path.exists(LIST_FILE):
        print(f"Файл {LIST_FILE} не найден!")
        return

    # Читаем список игр
    target_games = {}
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            cleaned_line = line.strip()
            if not cleaned_line or ":" not in cleaned_line:
                continue
            try:
                app_id, name = cleaned_line.split(":", 1)
                target_games[app_id.strip()] = name.strip()
            except:
                continue

    if not target_games:
        print("Список игр пуст.")
        return

    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    
    games_to_post = []

    print(f"Запуск публичной проверки цен. Всего игр: {len(target_games)}")
    
    for app_id, custom_name in target_games.items():
        # 1. Проверяем Казахстан (базовый регион для детекта скидки)
        kz_price, discount = get_price_for_region(app_id, "kz")
        time.sleep(0.5) # Пауза, чтобы не спамить сервера Steam
        
        # Если нашли скидку в КЗ, собираем цены для остальных регионов
        if discount > 0 and kz_price is not None:
            # 2. Проверяем Россию
            ru_price, _ = get_price_for_region(app_id, "ru")
            time.sleep(0.5)
            
            # 3. Проверяем США (для долларов)
            us_price, _ = get_price_for_region(app_id, "us")
            time.sleep(0.5)
            
            # Форматируем текст цен для вывода
            ru_text = f"{ru_price} ₽" if isinstance(ru_price, int) else "не доступна в РФ ❌"
            if ru_price == "Бесплатно":
                ru_text = "Бесплатно"
                
            us_text = f"${us_price}" if isinstance(us_price, int) else "н/д"
            if us_price == "Бесплатно":
                us_text = "Бесплатно"

            games_to_post.append({
                "id": app_id,
                "name": custom_name,
                "discount": discount,
                "price_kz": kz_price,
                "price_ru": ru_text,
                "price_us": us_text
            })
            print(f"Добавлена игра: {custom_name} (-{discount}%)")

    # 4. Публикация сборного поста для аудитории
    if games_to_post:
        chunk_size = 10
        for i in range(0, len(games_to_post), chunk_size):
            chunk = games_to_post[i:i + chunk_size]
            
            # Новый красивый заголовок без лишних слов
            message_lines = ["🔥 **АКТУАЛЬНЫЕ РАСПРОДАЖИ В STEAM**\n"]
            
            for g in chunk:
                game_link = config.STEAM_STORE_APP_BASE + g['id']
                
                # Собираем красивый блок для каждой игры
                line = (
                    f"• **[{g['name']}]({game_link})** | `-{g['discount']}%`\n"
                    f"  🇰🇿 {g['price_kz']} ₸ | 🇷🇺 {g['price_ru']} | 🇺🇸 {g['price_us']}\n"
                )
                message_lines.append(line)
            
            full_text = "\n".join(message_lines)

            # Отправка в Telegram
            tg_url = config.TELEGRAM_API_BASE + bot_token + "/sendMessage"
            payload = {
                "chat_id": channel_id,
                "text": full_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            res = requests.post(tg_url, json=payload)
            if res.status_code == 200:
                print("Профессиональный пост успешно опубликован.")
            else:
                print("Ошибка отправки в ТГ:", res.text)
    else:
        print("Новых скидок в проверенных валютах не обнаружено.")

if __name__ == "__main__":
    main()
