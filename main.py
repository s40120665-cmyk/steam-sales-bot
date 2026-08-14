import os
import requests

def main():
    TXT_FILE = "posted_games.txt"

    # 1. Читаем базу данных
    if os.path.exists(TXT_FILE):
        with open(TXT_FILE, "r", encoding="utf-8") as f:
            published_ids = [line.strip() for line in f.readlines()]
    else:
        published_ids = []

    # 2. Запрос к API Steam с регионом Казахстана (cc=kz, валюта KZT, язык RU)
    # Используем метод, который вытягивает расширенный список всех скидок региона
    url = "https://store.steampowered.com/api/featuredcategories/?cc=kz&l=ru"
    try:
        response = requests.get(url, timeout=10).json()
    except Exception as e:
        print(f"Ошибка запроса к Steam: {e}")
        return

    # Достаем списки скидок из разных категорий Steam (главные скидки и спец. предложения)
    specials_items = response.get("specials", {}).get("items", [])
    top_sellers = response.get("top_sellers", {}).get("items", [])
    
    # Объединяем их в один список, убирая дубликаты
    all_games = {game["id"]: game for game in (specials_items + top_sellers) if "discount_percent" in game and game["discount_percent"] > 0}
    
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    
    new_published_ids = []
    games_to_post = []

    # 3. Фильтруем только новые скидки
    for app_id, game in all_games.items():
        str_id = str(app_id)
        if str_id not in published_ids:
            name = game["name"]
            discount = game["discount_percent"]
            
            # Цены в Казахстане приходят в тиынах (как копейки, делим на 100)
            # Если игра бесплатная, ставим 0
            final_price_raw = game.get("final_price", 0)
            new_price = int(final_price_raw / 100) if final_price_raw else 0
            
            # Сохраняем игру для общего списка
            games_to_post.append({
                "id": str_id,
                "name": name,
                "discount": discount,
                "price": new_price
            })
            new_published_ids.append(str_id)

    # 4. Формируем ОДНО сообщение из всех найденных игр (не более 10 штук за раз, чтобы влезло в лимит ТГ)
    if games_to_post:
        # Берем первые 10 новых игр для одного поста
        chunk = games_to_post[:10]
        
        message_lines = ["🔥 **НОВЫЕ СКИДКИ STEAM (Казахстан 🇰🇿)**\n"]
        for g in chunk:
            line = f"• [{g['name']}](https://steampowered.com{g['id']}) | -{g['discount']}% | {g['price']} ₸"
            message_lines.append(line)
        
        full_text = "\n".join(message_lines)

        # Отправляем весь список одним постом в Telegram
        tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": channel_id,
            "text": full_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True # Выключаем превью ссылок, чтобы пост был компактным
        }
        
        res = requests.post(tg_url, json=payload)
        
        if res.status_code == 200:
            print(f"Успешно опубликован сборный пост из {len(chunk)} игр.")
            # Записываем в базу только те игры, которые РЕАЛЬНО вошли в этот пост
            with open(TXT_FILE, "a", encoding="utf-8") as f:
                for g in chunk:
                    f.write(f"{g['id']}\n")
            print("База данных на GitHub обновлена.")
        else:
            print(f"Ошибка отправки сборного поста в ТГ: {res.text}")
    else:
        print("Новых скидок со времени последней проверки не найдено.")

if __name__ == "__main__":
    main()
