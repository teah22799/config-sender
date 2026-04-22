import os
import json
import asyncio
import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

DAYS_LIMIT = 10
BASE_DIR = "posts"
RAW_DIR = f"{BASE_DIR}/raw"
HTML_DIR = f"{BASE_DIR}/html"
MEDIA_DIR = f"{BASE_DIR}/media"
POST_PAGES_DIR = f"{BASE_DIR}/post_pages"

for d in [BASE_DIR, RAW_DIR, HTML_DIR, MEDIA_DIR, POST_PAGES_DIR]:
    os.makedirs(d, exist_ok=True)

CSS_STYLE = """
<style>
body { background:#f2f3f5; font-family:sans-serif; margin:0; padding:0; }
.navbar { background:#fff; border-bottom:1px solid #ddd; padding:10px; display:flex; gap:12px; overflow-x:auto; }
.nav_item { display:flex; align-items:center; gap:6px; padding:8px 12px; background:#f8f9fa; border-radius:18px; text-decoration:none; border:1px solid #e2e2e2; }
.nav_item img { width:28px;height:28px;border-radius:50%; }
.card { background:#fff; margin:15px auto; width:92%; max-width:600px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }
.card img { width:100%; border-radius:12px 12px 0 0; }
.card_text { padding:15px; white-space:pre-wrap; }
.download_btn { padding:8px 14px; background:#0099ff; color:#fff; text-decoration:none; border-radius:6px; margin:8px; display:inline-block; }
.source_link { margin:10px; display:block; }
.section_title { font-size:22px; font-weight:bold; padding:20px; }
</style>
"""

def build_navbar(channels_info):
    html = '<div class="navbar">'
    for ch in channels_info:
        logo = ch["profile_pic"] if ch["profile_pic"] else ""
        html += f'''
        <a class="nav_item" href="{ch["html_path"]}">
            <img src="{logo}">
            <span>{ch["title"]}</span>
        </a>
        '''
    html += "</div>"
    return html

def create_post_page(post_id, channel_username, text, media_files):
    file_path = f"{POST_PAGES_DIR}/{channel_username}_{post_id}.html"

    html = "<html><head>" + CSS_STYLE + "</head><body>"

    html += f'<div class="section_title">Post from @{channel_username}</div>'
    html += '<div class="card">'

    for mf in media_files:
        html += f'<img src="../media/{channel_username}/{mf}">'

    html += f'<div class="card_text">{text}</div>'

    for mf in media_files:
        html += f'<a class="download_btn" download href="../media/{channel_username}/{mf}">Download {mf}</a>'

    html += "</div></body></html>"

    with open(file_path, "w", encoding="utf8") as f:
        f.write(html)

    return file_path

def create_channel_page(channel_info, posts_html, navbar):
    path = f"{HTML_DIR}/{channel_info['username']}.html"
    html = "<html><head>" + CSS_STYLE + "</head><body>"
    html += navbar
    html += f'<div class="section_title">@{channel_info["username"]}</div>'
    html += posts_html
    html += "</body></html>"

    with open(path, "w", encoding="utf8") as f:
        f.write(html)

def create_index_page(channels_info, content, navbar):
    html = "<html><head>" + CSS_STYLE + "</head><body>"
    html += navbar
    html += '<div class="section_title">All Recent Posts</div>'
    html += content
    html += "</body></html>"

    with open(f"{BASE_DIR}/index.html", "w", encoding="utf8") as f:
        f.write(html)

def cleanup_old_files():
    cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=DAYS_LIMIT)
    cutoff_ts = cutoff.timestamp()

    for folder in [RAW_DIR, HTML_DIR, POST_PAGES_DIR]:
        for fname in os.listdir(folder):
            path = os.path.join(folder, fname)
            if os.path.getmtime(path) < cutoff_ts:
                os.remove(path)

async def main():
    api_id = int(os.environ["API_ID"])
    api_hash = os.environ["API_HASH"]
    session_string = os.environ["SESSION_STRING"]

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.start()

    with open("channels.txt") as f:
        channels = [c.strip() for c in f.readlines() if c.strip()]

    channels_info = []
    all_posts_html = ""

    cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=DAYS_LIMIT)

    for link in channels:
        entity = await client.get_entity(link)
        username = entity.username
        title = entity.title

        profile_dir = f"{MEDIA_DIR}/{username}"
        os.makedirs(profile_dir, exist_ok=True)

        profile_pic_path = f"{profile_dir}/profile.jpg"
        try:
            await client.download_profile_photo(entity, file=profile_pic_path)
        except:
            profile_pic_path = ""

        channels_info.append({
            "username": username,
            "title": title,
            "profile_pic": f"media/{username}/profile.jpg" if profile_pic_path else "",
            "html_path": f"html/{username}.html"
        })

        posts_html = ""

        async for msg in client.iter_messages(entity, limit=100):
            if not hasattr(msg, "date") or msg.date is None:
                continue

            msg_date = msg.date

            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=datetime.timezone.utc)

            if msg_date < cutoff:
                continue

            text = msg.message or ""
            media_files = []

            raw_path = f"{RAW_DIR}/{username}_{msg.id}.json"
            with open(raw_path, "w", encoding="utf8") as f:
                json.dump(msg.to_dict(), f, ensure_ascii=False, indent=2)

            if msg.media:
                try:
                    mf = await client.download_media(msg, file=f"{MEDIA_DIR}/{username}/")
                    if mf:
                        media_files.append(os.path.basename(mf))
                except:
                    pass

            post_page = create_post_page(msg.id, username, text, media_files)

            card = '<div class="card">'
            for mf in media_files:
                card += f'<img src="../media/{username}/{mf}">'
            card += f'<div class="card_text">{text}</div>'
            card += f'<a class="source_link" target="_blank" href="https://t.me/{username}/{msg.id}">Open on Telegram</a>'
            card += f'<a class="source_link" href="../{post_page}">Open Single Page</a>'
            card += "</div>"

            posts_html += card
            all_posts_html += card

        navbar = build_navbar(channels_info)
        create_channel_page(channels_info[-1], posts_html, navbar)

    navbar = build_navbar(channels_info)
    create_index_page(channels_info, all_posts_html, navbar)

    cleanup_old_files()
    print("Fetch completed successfully.")

asyncio.run(main())
