import json
import os
import time
import re
import psycopg2
from psycopg2.extras import execute_values
from zoneinfo import ZoneInfo
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()
TODAY = datetime.today().strftime("%Y%m%d")
TODAY = "20260101"

# =========================
# Selenium 설정
# =========================
url = f"https://m.sports.naver.com/kbaseball/news?sectionId=kbo&sort=latest&date={TODAY}&isPhoto=N"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)

wait = WebDriverWait(driver, 10)
driver.get(url)


# =========================
# 기사 전처리 함수
# =========================
def parse_korean_datetime(s):
    pattern = r"(\d{4})\.(\d{2})\.(\d{2})\.\s*(오전|오후)\s*(\d{1,2}):(\d{2})"
    m = re.match(pattern, s.strip())
    if not m:
        raise ValueError(f"invalid datetime format: {s}")

    year, month, day, ampm, hour, minute = m.groups()
    hour = int(hour)
    minute = int(minute)
 
    if ampm == "오후" and hour != 12:
        hour += 12
    if ampm == "오전" and hour == 12:
        hour = 0

    return datetime(
        int(year),
        int(month),
        int(day),
        hour,
        minute
    )


# =========================
# URL 중복 관리 함수
# =========================
def load_seen_urls():
    os.makedirs("data/urls", exist_ok=True)
    path = f"data/urls/article_{TODAY}.txt"

    if not os.path.exists(path):
        return set()

    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def append_seen_url(article_url):
    path = f"data/urls/article_{TODAY}.txt"
    with open(path, "a", encoding="utf-8") as f:
        f.write(article_url + "\n")


# =========================
# 뉴스 크롤링 코드
# =========================
def crawl_article_urls():
    # 뉴스 더보기 버튼 모두 클릭
    while True:
        try:
            more_button = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.NewsList_button_more__YH1sc"))
            )

            driver.execute_script("arguments[0].click();", more_button)
            time.sleep(0.5)

        except TimeoutException:
            break

    # 기사 링크 크롤링
    try:
        elements = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "a.NewsItem_link_news__tD7x3"))
        )
        hrefs = [
            el.get_attribute("href")
            for el in elements
            if el.get_attribute("href")
        ]
    except TimeoutException:
        hrefs = []
        
    return hrefs


def crawl_article_detail(article_urls, retry=False):
    # 기사 상세 크롤링
    articles = []
    seen_urls = load_seen_urls()
    
    for article_url in article_urls:
        try:
            driver.get(article_url)
            wait = WebDriverWait(driver, 10)
            
            # 중복 발견 → 즉시 종료
            if not retry and article_url in seen_urls:
                print(f"[{datetime.now()}] [Warning] Skip Duplicate Article: {article_url}")
                continue

            # 중복 아님 → 즉시 기록
            if not retry:
                append_seen_url(article_url)
                seen_urls.add(article_url)

            # 입력 시간
            published_at = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "em.date"))
            ).text.strip()

            # 제목
            title = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "h2[class*='ArticleHead_article_title']"))
            ).text.strip()

            # 본문
            content_element = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div._article_content"))
            )
            body = content_element.text.strip()

            # 언론사
            try:
                press = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a[class*='PressLogo_article_head_press_logo'] img")
                    )
                ).get_attribute("alt")
            except TimeoutException:
                press = None

            # # 원문 링크
            # try:
            #     origin_url = driver.find_element(
            #         By.CSS_SELECTOR, "a[class*='DateInfo_link_origin_article']"
            #     ).get_attribute("href")
            # except NoSuchElementException:
            #     origin_url = None

            # 기자명
            try:
                reporter = driver.find_element(
                    By.CSS_SELECTOR, "em[class*='JournalistCard_name']"
                ).text.replace(" 기자", "")
            except NoSuchElementException:
                reporter = None

            # 이미지
            images = [
                img.get_attribute("src")
                for img in content_element.find_elements(By.TAG_NAME, "img")
                if img.get_attribute("src")
            ]
            
            # 비디오 유무 여부
            has_video = len(
                content_element.find_elements(By.TAG_NAME, "video")
            ) > 0

            article_json = {
                "platform": "article",
                "url": article_url,
                "press": press,
                "title": title,
                "body": body,
                "creator": reporter,
                "published_at": str(parse_korean_datetime(published_at)),
                "image_urls": images,
                "representative_image_url": images[0] if images else None,
                "has_video": has_video
            }

            articles.append(article_json)
            print(f"[{datetime.now()}] [Info] Crawl Success: {article_url}")

        except (TimeoutException, NoSuchElementException):
            print(article_url)
            continue
        
    return articles


# =========================
# 결과 저장(local)
# =========================
def save_local(articles):
    os.makedirs("data/content", exist_ok=True)
    path = f"data/content/article_{TODAY}.json"

    existing = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if not isinstance(existing, list):
            raise ValueError("json root must be a list")

    merged = existing + articles
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    return 0


# =========================
# 결과 저장(postgres)
# =========================
def save_db(articles): 
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
        platform, url, press, title, body, creator, 
        published_at, representative_image_url, has_video
    )
    VALUES (
        %(platform)s,
        %(url)s,
        %(press)s,
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

    for article in articles:
        cur.execute(sql, article)
        content_id = cur.fetchone()[0]
        image_urls = article.get("image_urls") or []
        
        if image_urls:
            rows = [
                (content_id, image_url, order_index) 
                for order_index, image_url in enumerate(image_urls)
            ]
            execute_values(
                cur, 
                "INSERT INTO kbonote.image (content_id, image_url, order_index) VALUES %s", 
                rows
            )

    conn.commit()
    cur.close()
    conn.close()
    return 0


def get_missing_article_urls():
    txt_path = f"data/urls/article_{TODAY}.txt"
    json_path = f"data/content/article_{TODAY}.json"

    # TXT 로드
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"txt not found: {txt_path}")
    with open(txt_path, "r", encoding="utf-8") as f:
        txt_urls = set(line.strip() for line in f if line.strip())

    # JSON 로드
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"json not found: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_urls = set()
    for item in data:
        if isinstance(item, dict):
            url = item.get("url")
            if url:
                json_urls.add(url)

    missing_urls = txt_urls - json_urls  # 차집합
    return missing_urls


if __name__ == "__main__":
    # date_list = [
    #     "20260207", "20260208", "20260209", "20260210", "20260211", "20260212", "20260213",
    #     "20260214", "20260215", "20260216", "20260217", "20260218", "20260219", "20260220",
    #     "20260221"
    # ]
    # for date in date_list:
    #     TODAY = date
    #     url = f"https://m.sports.naver.com/kbaseball/news?sectionId=kbo&sort=latest&date={TODAY}&isPhoto=N"
    #     driver.get(url)
        
    article_urls = crawl_article_urls()
    articles = crawl_article_detail(article_urls)
        # missing_urls = get_missing_article_urls()
        # articles = crawl_article_detail(missing_urls, True)
        
    save_local(articles)
    save_db(articles)
    
    driver.quit()