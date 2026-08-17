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

def send_tg_with_buttons(token, chat_id, text):
    url = f"{config.TELEGRAM_API_BASE}{token}/sendMessage"
    reply_markup = {
        "keyboard": [[{"text": "🔄 Проверить скидки и отчет"}], [{"text": "🛠️ Проверить статус системы"}]],
        "resize_keyboard": True
    }
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True, "reply_markup": reply_markup}
    try: requests.post(url, json=payload)
    except: pass

def delete_tg_message(token, chat_id, message_id):
    url = f"{config.TELEGRAM_API_BASE}{token}/deleteMessage"
    try: requests.post(url, json={"chat_id": chat_id, "message_id": message_id})
    except: pass

def trigger_github_action(token, repo, force_update=False):
    if not token or not repo: return "❌ Ошибка: В секретах не настроен PERSONAL_GH_TOKEN."
    url = f"https://github.com{repo}/actions/workflows/run_bot.yml/dispatches"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    payload = {"ref": "main", "inputs": {"force_update": "true" if force_update else "false"}}
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 204:
        return "🚀 *Запрос отправлен!* Проверка запущена, отчет прилетит через 1-2 минуты."
    return f"❌ Ошибка GitHub (Код {res.status_code})"

def run_diagnostics(token, channel_id):
    report = ["🛠️ **ОТЧЕТ О СТАТУСЕ СИСТЕМЫ:**\n"]
    url = f"{config.TELEGRAM_API_BASE}{token}/getChatAdministrators?chat_id={channel_id}"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("ok"): report.append("✅ *Связь с Telegram-каналом:* Успешно. Бот в админах.")
        else: report.append("❌ *Связь с Telegram-каналом:* Ошибка. Проверьте права бота.")
    except: report.append("❌ *Связь с Telegram-каналом:* Сервер ТГ недоступен.")
    report.append("✅ *Файл конфигурации config.py:* На месте.")
    report.append(f"✅ *Список игр games_list.txt:* На месте (Доступен: {os.path.exists('games_list.txt')}).")
    return "\n".join(report)

def check_admin_inline_commands(token, admin_id, gh_token, repo):
    url = f"{config.TELEGRAM_API_BASE}{token}/getUpdates?timeout=1"
    try:
        res = requests.get(url, timeout=5).json()
        updates = res.get("result", []) if isinstance(res, dict) else []
        for u in reversed(updates):
            msg = u.get("message", {})
            if str(msg.get("from", {}).get("id")) == str(admin_id):
                text = msg.get("text", "").strip()
                if text == "🔄 Проверить скидки и отчет":
                    status = trigger_github_action(gh_token, repo, force_update=False)
                    send_tg_with_buttons(token, admin_id, status)
                    return "stop"
                elif text == "🛠️ Проверить статус системы":
                    status = run_diagnostics(token, os.environ["TELEGRAM_CHANNEL_ID"])
                    send_tg_with_buttons(token, admin_id, status)
                    return "stop"
                elif text == "/update":
                    status = trigger_github_action(gh_token, repo, force_update=True)
                    send_tg_with_buttons(token, admin_id, "♻️ *Запущена полная очистка канала!* Ожидайте отчет...")
                    return "stop"
    except: pass
    return "run"
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
            
        img_url = f"{config.STEAM_IMAGE_BASE}{g['id']}/header.jpg"
        row = f"""<tr {row_class}>
                    <td><img src="{img_url}" alt="logo"></td>
                    <td><a href="{config.STEAM_STORE_APP_BASE}{g['id']}" target="_blank">{g['name']}</a></td>
                    <td style="text-align:center;"><span class="discount-cell {color_class}">{discount_text}</span></td>
                    <td>{g['price_kz']}</td><td>{g['price_ru']}</td><td>{g['price_us']}</td>
                </tr>"""
        table_rows.append(row)
        
    with open("index.html", "w", encoding="utf-8") as f: f.write(html_start + "\n".join(table_rows) + html_end)

def main():
    LIST_FILE = "games_list.txt"
    HISTORY_FILE = "history.json"
    if not os.path.exists(LIST_FILE): return

    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    admin_id = os.environ.get("ADMIN_TELEGRAM_ID")
    gh_token = os.environ.get("PERSONAL_GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")

    # 1. Проверяем новые нажатия кнопок перед запуском тяжелого парсера
    if admin_id:
        action = check_admin_inline_commands(bot_token, admin_id, gh_token, repo)
        if action == "stop":
            print("Обнаружена интерактивная команда пульта. Основная проверка отложена для перезапуска.")
            return

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

    force_update = os.environ.get("FORCE_UPDATE") == "true"
    if force_update and admin_id:
        if "posted_messages" in old_history:
            for m_id in old_history["posted_messages"]: delete_tg_message(bot_token, channel_id, m_id)
            old_history["posted_messages"] = []

    all_games_data, tg_games_to_post, admin_reports, new_history_data = [], [], [], {}

    print(f"Запуск гарантированной проверки цен. Всего игр: {len(target_games)}")
    for app_id, custom_name in target_games.items():
        kz_price, kz_initial, discount = None, None, 0
        
        # Умная система повторных попыток (до 3 раз), если Steam завис или смолчал
        for attempt in range(3):
            kz_price, kz_initial, discount = get_price_for_region(app_id, "kz")
            if kz_price is not None:
                break # Успешно получили данные, выходим из цикла попыток
            time.sleep(1.5) # Если была ошибка, ждем подольше перед повтором
            
        # Если даже после 3 попыток регион КЗ недоступен, ставим заглушку, но НЕ пропускаем игру для сайта
        if kz_price is None:
            kz_text = "н/д"
            ru_text = "н/д"
            us_text = "н/д"
            discount = 0
        else:
            kz_text = f"{kz_price} ₸" if isinstance(kz_price, int) else "Бесплатно"
            ru_text = "не доступна в РФ ❌"
            us_text = "н/д"
            
            # Запрашиваем РФ и США ТОЛЬКО если у игры есть активная скидка в КЗ
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
        
        # Делаем базовую микропаузу между играми
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

    all_games_data.sort(key=lambda x: x['discount'], reverse=True)
    generate_html(all_games_data)

    if admin_id:
        if admin_reports:
            report_text = "📊 **ОТЧЕТ ОБ ИЗМЕНЕНИИ СКИДОК:**\n\n" + "\n".join(admin_reports)
            send_tg_with_buttons(bot_token, admin_id, report_text)
        elif force_update:
            send_tg_with_buttons(bot_token, admin_id, "♻️ *Канал успешно очищен и перезаписан!* Изменений нет.")
        else:
            send_tg_with_buttons(bot_token, admin_id, "🔎 *Проверка завершена:* Изменений в скидках со времени прошлой проверки нет.")

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

