import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")


def search_videos(query, max_results=10):
    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": API_KEY,
        "q": query,
        "type": "video",
        "part": "id",
        "maxResults": max_results,
        "order": "date"
    }

    res = requests.get(url, params=params)
    data = res.json()

    video_ids = [item["id"]["videoId"] for item in data["items"]]

    return video_ids


def get_video_details(video_ids):
    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "key": API_KEY,
        "id": ",".join(video_ids),
        "part": "snippet,statistics"
    }

    res = requests.get(url, params=params)
    data = res.json()

    results = []

    for item in data["items"]:
        results.append({
            "video_id": item["id"],
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "channel": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
            "view_count": item["statistics"].get("viewCount"),
            "like_count": item["statistics"].get("likeCount")
        })

    return results


if __name__ == "__main__":
    video_ids = search_videos("KBO 하이라이트", 5)
    videos = get_video_details(video_ids)

    for v in videos:
        print(v)
