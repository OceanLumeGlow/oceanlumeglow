import os
import re
import json
import urllib.request
import urllib.parse

OWNER_ID = -243650090
TOKEN = os.environ.get("VK_TOKEN")

TAG_MAP = {
    "#рыбки": "snorkeling",
    "#снорклинг": "snorkeling",
    "#дайвинг": "diving",
    "#фридайвинг": "freediving",
}

def fetch_videos():
    params = urllib.parse.urlencode({
        "owner_id": OWNER_ID,
        "count": 100,
        "access_token": TOKEN,
        "v": "5.199"
    })
    url = f"https://vk.com?{params}"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode("utf-8"))
    
    if "error" in data:
        raise RuntimeError(f"VK API Error: {data['error']}")
        
    items = data.get("response", {}).get("items", [])
    result = []
    
    for item in items:
        title = item.get("title", "Без названия")
        desc = item.get("description", "")
        full_text = f"{title} {desc}".lower()
        
        categories = []
        for tag, cat in TAG_MAP.items():
            if tag in full_text and cat not in categories:
                categories.append(cat)
                
        # Вырезаем служебные теги из текста описания для чистоты в интерфейсе
        clean_desc = desc
        for tag in TAG_MAP.keys():
            clean_desc = re.sub(re.escape(tag), "", clean_desc, flags=re.IGNORECASE)
        clean_desc = re.sub(r'\n\s*\n', '\n\n', clean_desc).strip()
        
        # Берем обложку лучшего качества
        images = item.get("image", [])
        thumb = images[-1]["url"] if images else ""
        
        # Форматируем длительность
        dur = item.get("duration", 0)
        mins, secs = divmod(dur, 60)
        duration_str = f"{mins}:{secs:02d}"
        
        result.append({
            "id": item["id"],
            "owner_id": item["owner_id"],
            "title": title,
            "description": clean_desc,
            "categories": categories,
            "thumb": thumb,
            "duration": duration_str,
            "date": item.get("date", 0)
        })
        
    # Сортируем строго от новых к старым
    result.sort(key=lambda x: x["date"], reverse=True)
    
    with open("videos.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_videos()
