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

    # 2. Безопасный запрос к API Steam (сразу забираем главные скидки региона KZ)
    url = "https://store.steampowered.com/api/featuredcategories/?cc=kz&l=ru"
    try:
        response = requests.get(url, timeout=10).json()
    except Exception as e:
        print("Ошибка запроса к Steam:", e)
        return

    # Извлекаем игры из всех рекламных блоков витрины, где есть скидки
    specials = response.get("specials", {}).get("items", [])
    coming_soon = response.get("coming_soon", {}).get("items", [])
    top_sellers = response.get("top_sellers", {}).get("items", [])
    new_releases = response.get("new_releases", {}).get("items", [])
    
    # Объединяем все блоки в один большой массив
    raw_games = specials + coming_soon + top_sellers + new_releases
    
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    
    games_to_post = []
    seen_ids = set() # Чтобы избежать дубликатов внутри одного запуска

    # 3. Фильтруем игры
    for game in raw_games:
        app_id = str(game.get("id"))
        
        if app_id and (app_id not in published_ids) and (app_id not in seen_ids):
            discount = game.get("discount_percent", 0)
            
            # Если есть скидка
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

    # 4. Формируем ОДНО сборное сообщение из найденных игр (по 10 штук)
    if games_to_post:
        print("Найдено новых игр со скидками:", len(games_to_post))
        
        chunk_size = 10
        for i in range(0, len(games_to_post), chunk_size):
            chunk = games_to_post[i:i + chunk_size]
            
            message_lines = ["🔥 **АКТУАЛЬНЫЕ СКИДКИ STEAM (Казахстан 🇰🇿)**\n"]
            for g in chunk:
                # Безопасно собираем ссылки на игры для ТГ
                game_link = "https://api.telegram.org/bot" + g['id']
                line = "• [" + g['name'] + "](" + game_link + ") | -" + str(g['discount']) + "% | " + str(g['price']) + " ₸"
                message_lines.append(line)
            
            full_text = "\n".join(message_lines)

            # Отправляем пачку в Telegram
            tg_url = "https://telegram.org" + bot_token + "/sendMessage"
            payload = {
                "chat_id": channel_id,
                "text": full_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            res = requests.post(tg_url, json=payload)
            
            if res.status_code == 200:
                # Записываем опубликованные игры в файл базы данных
                with open(TXT_FILE, "a", encoding="utf-8") as f:
                    for g in chunk:
                        f.write(g['id'] + "\n")
                print("Успешно опубликована пачка игр.")
            else:
                print("Ошибка отправки в ТГ:", res.text)
    else:
        print("Новых скидок не найдено.")

if __name__ == "__main__":
    main()
