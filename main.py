import os
import requests

def main():
    TXT_FILE = "posted_games.txt"

    # 1. Читаем базу данных уже опубликованных игр
    if os.path.exists(TXT_FILE):
        with open(TXT_FILE, "r", encoding="utf-8") as f:
            published_ids = [line.strip() for line in f.readlines()]
    else:
        published_ids = []

    # 2. Запрашиваем 1000 самых популярных игр в Steam через SteamSpy API
    # Этот метод выдает реальные хиты, на которые сейчас есть скидки
    url = "https://steamspy.com/api.php?request=top100in2weeks"
    try:
        steamspy_data = requests.get(url, timeout=15).json()
    except Exception as e:
        print(f"Ошибка запроса к SteamSpy: {e}")
        return

    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    
    games_to_post = []

    # 3. Фильтруем только игры со скидками, которых нет в нашей базе данных
    for app_id, game_info in steamspy_data.items():
        str_id = str(app_id)
        
        if str_id not in published_ids:
            discount = game_info.get("discount", 0)
            
            # Если на игру есть скидка (больше 0)
            if discount > 0:
                name = game_info.get("name", "Unknown Game")
                
                # Запрашиваем точную цену в тенге напрямую у Steam для этой игры
                # cc=kz гарантирует обход блокировок РФ и показ заблокированных игр
                price_url = f"https://store.steampowered.com/api/appdetails?appids={str_id}&cc=kz&filters=price_overview"
                try:
                    price_res = requests.get(price_url, timeout=5).json()
                    if price_res and price_res.get(str_id, {}).get("success"):
                        price_data = price_res[str_id]["data"].get("price_overview", {})
                        # Цена приходит в тиынах, делим на 100
                        new_price = int(price_data.get("final", 0) / 100)
                    else:
                        new_price = "Уточняйте"
                except:
                    new_price = "Уточняйте"

                games_to_post.append({
                    "id": str_id,
                    "name": name,
                    "discount": discount,
                    "price": new_price
                })

    # 4. Формируем и отправляем сборные посты по 10 игр в каждом
    if games_to_post:
        print(f"Найдено новых игр со скидками: {len(games_to_post)}")
        
        # Разбиваем огромный список на пачки по 10 штук
        chunk_size = 10
        for i in range(0, len(games_to_post), chunk_size):
            chunk = games_to_post[i:i + chunk_size]
            
            message_lines = ["🔥 **АКТУАЛЬНЫЕ СКИДКИ STEAM (Казахстан 🇰🇿)**\n"]
            for g in chunk:
                price_text = f"{g['price']} ₸" if isinstance(g['price'], int) else g['price']
                line = f"• [{g['name']}](https://store.steampowered.com/app/{g['id']}) | -{g['discount']}% | {price_text}"
                message_lines.append(line)
            
            full_text = "\n".join(message_lines)

            # Отправка пачки в Телеграм
            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": channel_id,
                "text": full_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            res = requests.post(tg_url, json=payload)
            
            if res.status_code == 200:
                # Сразу записываем отправленные игры в базу данных, чтобы не дублировать
                with open(TXT_FILE, "a", encoding="utf-8") as f:
                    for g in chunk:
                        f.write(f"{g['id']}\n")
                print(f"Успешно опубликована пачка из {len(chunk)} игр.")
            else:
                print(f"Ошибка отправки пачки в ТГ: {res.text}")
    else:
        print("Новых скидок среди популярных игр не найдено.")

if __name__ == "__main__":
    main()
