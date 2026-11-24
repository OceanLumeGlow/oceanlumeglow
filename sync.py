import os
import re
import json
import urllib.request

CHANNEL = "OceanLumeGlow"  

TAG_MAP = {
    "#рыбки": "snorkeling",
    "#снорклинг": "snorkeling",
    "#дайвинг": "diving",
    "#фридайвинг": "freediving",
}

def main():
    os.makedirs("thumbs", exist_ok=True)
    url = f"https://t.me{CHANNEL}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")

    # Разбиваем HTML на блоки отдельных постов
    blocks = html.split('class="tgme_widget_message_wrap')
    videos = []

    for block in blocks[1:]:
        # Ищем номер поста (data-post="channel/123")
        post_match = re.search(rf'data-post="{re.escape(CHANNEL)}/(\d+)"', block)
        if not post_match:
            continue
        post_id = int(post_match.group(1))

        # Проверяем, что в посте есть видео (ищем превью видеоплеера)
        thumb_match = re.search(r'class="tgme_widget_message_video_thumb"[^>]*style="[^"]*background-image:url\(\'([^\']+)\'\)', block)
        if not thumb_match:
            continue
        thumb_remote_url = thumb_match.group(1)

        # Скачиваем превью в локальную папку thumbs/, если его еще нет
        local_thumb = f"thumbs/{post_id}.jpg"
        if not os.path.exists(local_thumb):
            try:
                urllib.request.urlretrieve(thumb_remote_url, local_thumb)
            except Exception:
                local_thumb = thumb_remote_url

        # Длительность видео
        dur_match = re.search(r'class="message_video_duration[^"]*"[^>]*>([^<]+)<', block)
        duration = dur_match.group(1).strip() if dur_match else ""

        # Текст поста
        text_match = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
        raw_text = text_match.group(1) if text_match else ""
        # Заменяем <br> на переносы строк и чистим HTML-теги
        text = re.sub(r'<br\s*/?>', '\n', raw_text)
        text = re.sub(r'<[^>]+>', '', text).strip()

        lower_text = text.lower()
        categories = []
        for tag, cat in TAG_MAP.items():
            if tag in lower_text and cat not in categories:
                categories.append(cat)

        # Вырезаем служебные хештеги из текста
        clean_text = text
        for tag in TAG_MAP:
            clean_text = re.sub(re.escape(tag), "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text).strip()

        # Первая строка текста идет в заголовок карточки
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
        title = lines[0] if lines else f"Видео #{post_id}"

        videos.append({
            "id": post_id,
            "title": title,
            "categories": categories,
            "thumb": local_thumb,
            "duration": duration,
            "link": f"https://t.me{CHANNEL}/{post_id}"
        })

    # Сортируем строго от новых постов к старым
    videos.sort(key=lambda x: x["id"], reverse=True)

    # Сохраняем историю уже спарсенных старых постов, чтобы не потерять их при росте канала
    if os.path.exists("videos.json"):
        try:
            with open("videos.json", "r", encoding="utf-8") as f:
                old_videos = json.load(f)
            new_ids = {v["id"] for v in videos}
            for ov in old_videos:
                if ov["id"] not in new_ids:
                    videos.append(ov)
            videos.sort(key=lambda x: x["id"], reverse=True)
        except Exception:
            pass

    with open("videos.json", "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
