import os
import requests
import config

def main():
    LIST_FILE = "games_list.txt"

    # 1. Проверяем, существует ли ваш список игр
    if not os.path.exists(LIST_FILE):
        print(f"Файл {LIST_FILE} не найден! Создайте его на GitHub.")
        return

    # Читаем ваш персональный список игр
    target_games = {}
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                app_id, name = line.strip().split(":", 1)
                target_games[app_id.strip()] = name.strip()

    if not target_games:
        print("Список игр в games_list.txt пуст.")
        return

    # Собираем все ID игр в одну строку для пакетного запроса к Steam
    app_ids_str = ",".join(target_games.keys())

    # 2. Делаем единый запрос цены, собирая адрес ИЗ КОНФИГА
    price_url = config.STEAM_PRICE_API_BASE + app_ids_str + "&cc=kz&filters=price_overview"
    try:
        response = requests.get(price_url, timeout=15).json()
    except Exception as e:
        print("Ошибка запроса к Steam:", e)
        return

    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    
    games_to_post = []

    # 3. Перебираем игры из ответа Steam
    for app_id, custom_name in target_games.items():
        game_data = response.get(app_id, {})
        
        if game_data.get("success"):
            price_info = game_data.get("data", {}).get("price_overview", {})
            
            if price_info:
                discount = price_info.get("discount_percent", 0)
                
                # Если на игру из вашего списка СЕЙЧАС есть скидка
                if discount > 0:
                    final_price_raw = price_info.get("final", 0)
                    new_price = int(final_price_raw / 100) # Переводим тиыны в тенге
                    
                    games_to_post.append({
                        "id": app_id,
                        "name": custom_name,
                        "discount": discount,
                        "price": new_price
                    })

    # 4. Формируем ОДНО общее сообщение для Телеграм-канала
    if games_to_post:
        print(f"Найдено игр со скидками из вашего списка: {len(games_to_post)}")
        
        chunk_size = 10
        for i in range(0, len(games_to_post), chunk_size):
            chunk = games_to_post[i:i + chunk_size]
            
            message_lines = ["🔥 **СКИДКИ НА ИГРЫ ИЗ НАШЕГО СПИСКА (Казахстан 🇰🇿)**\n"]
            for g in chunk:
                game_link = config.STEAM_STORE_APP_BASE + g['id']
                line = f"• [{g['name']}]({game_link}) | -{g['discount']}% | {g['price']} ₸"
                message_lines.append(line)
            
            full_text = "\n".join(message_lines)

            # Отправка в Telegram по адресу из конфига
            tg_url = config.TELEGRAM_API_BASE + bot_token + "/sendMessage"
            payload = {
                "chat_id": channel_id,
                "text": full_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            res = requests.post(tg_url, json=payload)
            if res.status_code == 200:
                print("Пачка скидок успешно опубликована.")
            else:
                print("Ошибка отправки в ТГ:", res.text)
    else:
        print("В данный момент скидок на игры из вашего списка нет.")

if __name__ == "__main__":
    main()
