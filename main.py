import os
import requests
import time # Библиотека для создания пауз
import config

def main():
    LIST_FILE = "games_list.txt"

    # 1. Проверяем наличие файла со списком игр
    if not os.path.exists(LIST_FILE):
        print(f"Файл {LIST_FILE} не найден! Создайте его на GitHub.")
        return

    # Читаем список игр с защитой от пустых строк
    target_games = {}
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            cleaned_line = line.strip()
            if not cleaned_line:
                continue
            if ":" in cleaned_line:
                try:
                    app_id, name = cleaned_line.split(":", 1)
                    target_games[app_id.strip()] = name.strip()
                except:
                    continue

    if not target_games:
        print("Список игр в games_list.txt пуст или заполнен неверно.")
        return

    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    
    games_to_post = []

    # 2. Поштучно проверяем каждую игру из вашего списка
    print(f"Начинаем проверку игр из списка. Всего к проверке: {len(target_games)}")
    for app_id, custom_name in target_games.items():
        # Собираем адрес запроса из базовой части в config.py
        price_url = config.STEAM_PRICE_API_BASE + app_id + "&cc=kz&filters=price_overview"
        
        try:
            response = requests.get(price_url, timeout=10).json()
            # Делаем обязательную паузу в 1 секунду, чтобы Steam не выдал бан за скорость
            time.sleep(1) 
            
            if response and response.get(app_id, {}).get("success"):
                price_info = response[app_id]["data"].get("price_overview", {})
                
                if price_info:
                    discount = price_info.get("discount_percent", 0)
                    
                    # Если на эту конкретную игру СЕЙЧАС есть скидка
                    if discount > 0:
                        final_price_raw = price_info.get("final", 0)
                        new_price = int(final_price_raw / 100) # Переводим в тенге
                        
                        games_to_post.append({
                            "id": app_id,
                            "name": custom_name,
                            "discount": discount,
                            "price": new_price
                        })
                        print(f"Найдена скидка на {custom_name}: -{discount}%")
        except Exception as e:
            print(f"Ошибка проверки игры ID {app_id}: {e}")
            continue

    # 3. Формируем ОДНО общее сообщение для Телеграм-канала
    if games_to_post:
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
        print("В данный момент скидок на игры из вашего списка нет. Все игры проверены.")

if __name__ == "__main__":
    main()
