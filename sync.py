import os
import re
import json
import urllib.request
import urllib.parse

raw_token = os.environ.get("BOT_TOKEN", "")
m = re.search(r"(\d+:[A-Za-z0-9_-]+)", raw_token)
if not m:
    raise RuntimeError("В секрете BOT_TOKEN не найден валидный токен")
BOT_TOKEN = m.group(1)
CHANNEL = "OceanLumeGlow"

TAG_MAP = {
    "#fish": "snorkeling",
    "#sharks": "snorkeling",
    "#shark": "snorkeling",
    "#snorkel": "snorkeling",
    "#рыбки": "snorkeling",
    "#dive": "diving",
    "#diving": "diving",
    "#owd": "diving",
    "#дайвинг": "diving",
    "#freedive": "freediving",
    "#freediving": "freediving",
    "#фридайвинг": "freediving",
}

def make_tg_link(post_id):
    return "/".join(["https://t.me", CHANNEL, str(post_id)])

def tg_api(method, params=None):
    query = urllib.parse.urlencode(params) if params else ""
    url = urllib.parse.urlunparse(("https", "api.telegram.org", f"/bot{BOT_TOKEN}/{method}", "", query, ""))
    req = urllib.request.urlopen(url, timeout=20)
    return json.loads(req.read().decode("utf-8"))

def download_thumb(file_id, post_id):
    os.makedirs("thumbs", exist_ok=True)
    local_path = "/".join(["thumbs", f"{post_id}.jpg"])
    try:
        info = tg_api("getFile", {"file_id": file_id})
        file_path = info.get("result", {}).get("file_path")
        if file_path:
            dl_url = urllib.parse.urlunparse(("https", "api.telegram.org", f"/file/bot{BOT_TOKEN}/{file_path}", "", "", ""))
            urllib.request.urlretrieve(dl_url, local_path)
            return local_path
    except Exception:
        pass
    return ""

def main():
    existing = {}
    if os.path.exists("videos.json"):
        try:
            with open("videos.json", "r", encoding="utf-8") as f:
                for item in json.load(f):
                    if "placehold.co" not in item.get("thumb", "") and not item.get("thumb", "").startswith("data:"):
                        item["link"] = make_tg_link(item["id"])
                        existing[item["id"]] = item
        except Exception:
            pass

    data = tg_api("getUpdates", {"limit": 100})
    updates = data.get("result", [])
    last_update_id = None

    for upd in updates:
        last_update_id = upd["update_id"]
        msg = upd.get("channel_post") or upd.get("edited_channel_post") or upd.get("message")
        if not msg:
            continue

        post_id = None
        if upd.get("channel_post") or upd.get("edited_channel_post"):
            chat_user = msg.get("chat", {}).get("username", "")
            if chat_user.lower() == CHANNEL.lower():
                post_id = msg.get("message_id")
        elif msg.get("forward_origin", {}).get("type") == "channel":
            fwd = msg["forward_origin"]
            if fwd.get("chat", {}).get("username", "").lower() == CHANNEL.lower():
                post_id = fwd.get("message_id")

        if not post_id:
            continue

        video = msg.get("video") or msg.get("animation")
        if not video:
            continue

        caption = msg.get("caption") or msg.get("text") or ""
        lower_text = caption.lower()

        categories = []
        for tag, cat in TAG_MAP.items():
            if tag in lower_text and cat not in categories:
                categories.append(cat)

        clean_text = caption
        for tag in TAG_MAP:
            clean_text = re.sub(re.escape(tag), "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text).strip()

        title = next((line.strip() for line in clean_text.split('\n') if line.strip()), f"Видео #{post_id}")

        dur = video.get("duration", 0)
        mins, secs = divmod(dur, 60)
        duration_str = f"{mins}:{secs:02d}" if dur else ""

        thumb_path = existing.get(post_id, {}).get("thumb", "")
        thumb_obj = video.get("thumbnail") or video.get("thumb")
        if thumb_obj and thumb_obj.get("file_id"):
            downloaded = download_thumb(thumb_obj["file_id"], post_id)
            if downloaded:
                thumb_path = downloaded

        existing[post_id] = {
            "id": post_id,
            "title": title,
            "categories": categories,
            "thumb": thumb_path,
            "duration": duration_str,
            "link": make_tg_link(post_id)
        }

    if last_update_id is not None:
        try:
            tg_api("getUpdates", {"offset": last_update_id + 1, "limit": 1})
        except Exception:
            pass

    videos = sorted(existing.values(), key=lambda x: x["id"], reverse=True)
    with open("videos.json", "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
