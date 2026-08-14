import os
import requests

def main():
    TXT_FILE = "posted_games.txt"

    # 1. Читаем уже опубликованные ID игр из файла
    if os.path.exists(TXT_FILE):
        with open(TXT_FILE, "r", encoding="utf-8") as f:
            published_ids = [line.strip() for line in f.readlines()]
    else:
        published_ids = []

    # 2. Запрос к официальному API Steam (Регион RU, язык RU)
    url = "https://store.steampowered.com/api/featuredcategories/?cc=ru&l=ru"
    try:
        response = requests.get(url, timeout=10).json()
    except Exception as e:
        print(f"Ошибка запроса к Steam: {e}")
        return

    # Забираем блок со скидками (specials)
    specials = response.get("specials", {}).get("items", [])
    
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    
    new_published_ids = []

    # 3. Проверяем каждую игру со скидкой
    for game in specials:
        app_id = str(game["id"])
        
        # Если этой игры еще нет в нашей базе данных
        if app_id not in published_ids:
            name = game["name"]
            discount = game["discount_percent"]
            # Цены в API приходят в копейках (например, 49900 вместо 499 руб)
            new_price = int(game["final_price"] / 100) 
            
            # Красиво оформляем текст поста
            text = (
                f"🔥 **{name}**\n\n"
                f"💰 Скидка: -{discount}%\n"
                f"💳 Новая цена: {new_price} руб.\n\n"
                f"🔗 [Открыть в Steam](https://steampowered.com{app_id})"
            )
            
            # Отправляем в Telegram
            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": channel_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            res = requests.post(tg_url, json=payload)
            
            if res.status_code == 200:
                print(f"Успешно опубликовано: {name}")
                new_published_ids.append(app_id)
            else:
                print(f"Ошибка отправки в ТГ: {res.text}")

    # 4. Дописываем новые опубликованные ID обратно в файл на GitHub
    if new_published_ids:
        with open(TXT_FILE, "a", encoding="utf-8") as f:
            for app_id in new_published_ids:
                f.write(f"{app_id}\n")
        print("База данных на GitHub успешно обновлена.")

if __name__ == "__main__":
    main()
