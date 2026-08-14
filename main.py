import os
import requests
import config # Подключаем наш файл со ссылками

def main():
    # 1. Безопасный запрос к Steam, используя ссылку из конфига
    try:
        response = requests.get(config.STEAM_API_URL, timeout=10).json()
    except Exception as e:
        print("Ошибка запроса к Steam:", e)
        return

    # Извлекаем игры из всех блоков витрины
    specials = response.get("specials", {}).get("items", [])
    coming_soon = response.get("coming_soon", {}).get("items", [])
    top_sellers = response.get("top_sellers", {}).get("items", [])
    new_releases = response.get("new_releases", {}).get("items", [])
    
    raw_games = specials + coming_soon + top_sellers + new_releases
    
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    
    games_to_post = []
    seen_ids = set()

    # 2. Фильтруем игры со скидками
    for game in raw_games:
        app_id = str(game.get("id"))
        
        if app_id and (app_id not in seen_ids):
            discount = game.get("discount_percent", 0)
            
            if discount > 0:
                name = game.get("name", "Unknown Game")
                final_price_raw = game.get("final_price", 0)
                new_price = int(final_price_raw / 100) if final_price_raw else 0
                
                games_to_post.append({
                    "id": app_id,
                    "name": name,
                    "discount": discount,
                    "price": new_price
                })
                seen_ids.add(app_id)

    # 3. Формируем ОДНО компактное сообщение из найденных игр
    if games_to_post:
        # Берем первые 10 игр для одного поста
        chunk = games_to_post[:10]
        
        message_lines = ["🔥 **АКТУАЛЬНЫЕ СКИДКИ STEAM (Казахстан 🇰🇿)**\n"]
        for g in chunk:
            # Собираем ссылку на игру из базовой части в конфиге и ID игры
            game_link = config.STEAM_STORE_APP_BASE + g['id']
            line = "• [" + g['name'] + "](" + game_link + ") | -" + str(g['discount']) + "% | " + str(g['price']) + " ₸"
            message_lines.append(line)
        
        full_text = "\n".join(message_lines)

        # 4. Отправляем пачку в Telegram, используя адрес из конфига
        tg_url = config.TELEGRAM_API_BASE + bot_token + "/sendMessage"
        payload = {
            "chat_id": channel_id,
            "text": full_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        res = requests.post(tg_url, json=payload)
        
        if res.status_code == 200:
            print("Успешно опубликован сборный пост.")
        else:
            print("Ошибка отправки в ТГ:", res.text)
    else:
        print("Скидок не найдено.")

if __name__ == "__main__":
    main()
