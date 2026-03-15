import os
import requests
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_channel_id(handle):
    url = "https://www.googleapis.com/youtube/v3/channels"

    params = {
        "key": API_KEY,
        "forHandle": handle,
        "part": "id"
    }

    res = requests.get(url, params=params).json()

    return res["items"][0]["id"]


def get_uploads_playlist(channel_id):
    url = "https://www.googleapis.com/youtube/v3/channels"

    params = {
        "key": API_KEY,
        "id": channel_id,
        "part": "contentDetails"
    }

    res = requests.get(url, params=params).json()

    return res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_video_ids(playlist_id):
    url = "https://www.googleapis.com/youtube/v3/playlistItems"

    params = {
        "key": API_KEY,
        "playlistId": playlist_id,
        "part": "snippet",
        "maxResults": 50
    }

    res = requests.get(url, params=params).json()

    return [i["snippet"]["resourceId"]["videoId"] for i in res["items"]]


def get_video_details(video_ids):
    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "key": API_KEY,
        "id": ",".join(video_ids),
        "part": "snippet,statistics,contentDetails"
    }

    res = requests.get(url, params=params).json()

    results = []

    for item in res["items"]:
        results.append({
            "video_id": item["id"],
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "channel": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
            "duration": item["contentDetails"]["duration"],
            "view_count": item["statistics"].get("viewCount"),
            "like_count": item["statistics"].get("likeCount")
        })

    return results


def save_db(videos):
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT")),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        dbname=os.getenv("PG_DBNAME")
    )

    cur = conn.cursor()

    sql = """
    INSERT INTO kbonote.content (
        platform, url, title, body, creator, published_at,
        representative_image_url, has_video
    )
    VALUES (
        %(platform)s,
        %(url)s,
        %(title)s,
        %(body)s,
        %(creator)s,
        %(published_at)s,
        %(representative_image_url)s,
        %(has_video)s
    )
    ON CONFLICT (url) DO NOTHING
    RETURNING id;
    """

    success = 0
    fail = 0

    for video in videos:
        data = {
            "platform": "youtube",
            "url": video['video_id'],
            "title": video["title"],
            "body": video["description"],
            "creator": video["channel"],
            "published_at": video["published_at"],
            "representative_image_url": video["thumbnail"],
            "has_video": True
        }
        cur.execute(sql, data)

        row = cur.fetchone()
        if row:
            content_id = row[0]
            cur.execute("INSERT INTO kbonote.content_analysis (content_id) VALUES (%s)", (content_id,))
            cur.execute(
                "INSERT INTO kbonote.image (content_id, image_url, order_index) VALUES (%s, %s, %s)",
                (content_id, video["thumbnail"], 0)
            )
            success += 1

        else:
            fail += 1
            continue

    print(f"[{datetime.now()}] [Info] {success} videos were saved, {fail} videos were duplicated.")

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":

    channel_id = get_channel_id("별별")

    playlist_id = get_uploads_playlist(channel_id)

    video_ids = get_video_ids(playlist_id)

    videos = get_video_details(video_ids)

    save_db(videos)
