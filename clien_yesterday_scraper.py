import csv
import re
import sys

import os
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin
from typing import Dict, List, Optional, Tuple

try:
    from wordcloud import WordCloud
except ImportError:
    WordCloud = None
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from dotenv import load_dotenv

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 클리앙 요청 시 사용할 공통 HTTP 헤더(봇 차단 방지를 위해 브라우저 UA 지정)
DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    )
}
REQUEST_TIMEOUT = 10 # seconds

# Load environment variables from .env file first
load_dotenv()

# Sensitive API keys and tokens should be loaded from environment variables
# For local development, consider using python-dotenv to load from a .env file
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID_HERE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

# 키워드 빈도 분석에서 제외할 불용어 목록
STOP_WORDS = {"속보", "단독", "합니다", "더", "첫", "수","제","오늘","있다","너무","정말","속보","하는","왜"}

GEMINI_SUMMARY_PROMPT = (
    "다음은 커뮤니티의 주요 이슈 게시물들을 모아놓은 텍스트입니다. "
    "전체 내용을 핵심만 간추려 3~5 문장의 완성된 문단으로 요약해주세요.\n\n"
    "---[원문]---\n"
)


def scrape_clien_yesterday_posts():
    """
    Scrape yesterday's posts from Clien's 'Today' board, including metadata fields.
    """
    base_url = "https://www.clien.net/service/board/park"
    page_num = 0
    yesterday_posts = []
    yesterday = datetime.now().date() - timedelta(days=1)

    def normalize_count(value: str) -> int:
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else 0

    # 오늘 작성된 게시물이 없을 때까지 페이징하며 수집
    while True:
        params = {"od": "T31", "category": "0", "po": page_num}

        try:
            response = requests.get(
                base_url,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Request failed while fetching page {page_num}: {e}")
            break

        # 목록 페이지에서 공지 제외 게시글 블록 추출
        soup = BeautifulSoup(response.text, "html.parser")
        post_list = soup.select("div.list_content > div.symph_row:not(.list_notice)")

        if not post_list:
            print("No posts were returned for the current page. Stopping.")
            break

        found_yesterday_post_on_page = False

        for post in post_list:
            timestamp_span = post.select_one("div.list_time span.timestamp")
            if not timestamp_span:
                continue

            timestamp_text = timestamp_span.get_text(strip=True)
            try:
                post_datetime = datetime.strptime(timestamp_text, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Unexpected timestamp format; skip this post.
                continue

            post_date = post_datetime.date()

            if post_date < yesterday:
                print(f"Found posts older than yesterday on page {page_num}. Stopping.")
                return yesterday_posts
            elif post_date == yesterday:
                found_yesterday_post_on_page = True
            else:  # post_date is today
                continue

            title_span = post.select_one("span.subject_fixed")
            like_span = post.select_one("div.list_symph span")
            author_span = post.select_one("div.list_author span.nickname span")
            hit_span = post.select_one("div.list_hit span.hit")
            time_span = post.select_one("div.list_time span.time")
            link_tag = post.select_one("a.list_subject") or post.select_one("div.list_title a")

            title = title_span.get_text(strip=True) if title_span else ""
            recommendations = normalize_count(like_span.get_text(strip=True) if like_span else "0")
            author = author_span.get_text(strip=True) if author_span else ""
            views = normalize_count(hit_span.get_text(strip=True) if hit_span else "0")
            display_time = (
                time_span.contents[0].strip()
                if time_span and time_span.contents
                else post_datetime.strftime("%H:%M")
            )
            url = urljoin(base_url, link_tag["href"]) if link_tag and link_tag.has_attr("href") else ""

            yesterday_posts.append(
                {
                    "title": title,
                    "recommendations": recommendations,
                    "author": author,
                    "views": views,
                    "timestamp": post_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "display_time": display_time,
                    "url": url,
                }
            )

        # 현재 페이지에서 어제 게시물을 하나라도 찾았고, 다음 페이지로 넘어가도 어제 게시물이 없을 수 있으므로
        # 무조건 중단하지 않고 계속 페이징합니다. 중단은 post_date < yesterday 조건에서 처리됩니다.
        if not found_yesterday_post_on_page:
            print(f"No posts from yesterday found on page {page_num}. Continuing to next page.")

        print(f"Completed scraping page {page_num}.")
        page_num += 1
    return yesterday_posts


def tokenize_title(title: str) -> List[str]:
    """
    Extract alphanumeric and Hangul tokens from a title and normalize them.
    """
    # 한글/영문/숫자 토큰만 추출해 소문자로 정규화
    tokens = re.findall(r"[\uAC00-\uD7A3A-Za-z0-9]+", title)
    return [token.lower() for token in tokens if token]


def calculate_title_frequencies(posts, top_n: int = 20) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
    """
    Calculate most common words and bigrams within post titles.
    """
    # 단어/바이그램 빈도 수집
    word_counter: Counter = Counter()
    bigram_counter: Counter = Counter()

    for post in posts:
        tokens = tokenize_title(post["title"])
        # 불용어를 제외한 최종 토큰 목록
        filtered_tokens = [token for token in tokens if token not in STOP_WORDS]

        if not filtered_tokens:
            continue

        word_counter.update(filtered_tokens)
        if len(filtered_tokens) > 1:
            bigrams = (" ".join(pair) for pair in zip(filtered_tokens, filtered_tokens[1:]))
            bigram_counter.update(bigrams)

    return word_counter.most_common(top_n), bigram_counter.most_common(top_n)


def save_posts_to_csv(posts, csv_path: Path) -> None:
    """
    Save collected posts to a CSV file with the requested column order.
    """
    fieldnames = ["Rec", "Views", "Author", "Time", "Title", "URL"]

    rows = [
        {
            "Rec": post["recommendations"],
            "Views": post["views"],
            "Author": post["author"],
            "Time": post["display_time"],
            "Title": post["title"],
            "URL": post["url"],
        }
        for post in posts
    ]

    with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_title_frequencies_to_csv(word_freq, bigram_freq, csv_path: Path) -> None:
    """
    Save word and bigram frequency results to a CSV file.
    """
    with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Type", "Token", "Count"])

        for token, count in word_freq:
            writer.writerow(["word", token, count])

        for token, count in bigram_freq:
            writer.writerow(["bigram", token, count])


def fetch_post_content(url: str) -> Optional[str]:
    """
    Retrieve the main textual content from an individual post page.
    """
    if not url:
        return None

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    # 페이지 구조 변동을 고려해 자주 쓰이는 컨테이너 셀렉터 후보 등록
    content_selectors = [
        "div.post_content",
        "div.post_article",
        "div.post_body",
        "div.post_view",
        "div.view_content",
        "article.post_article",
        "div.content_view",
    ]

    for selector in content_selectors:
        content = soup.select_one(selector)
        if content:
            text = content.get_text("\n", strip=True)
            if text:
                return text

    fallback = soup.select_one("body")
    if fallback:
        text = fallback.get_text("\n", strip=True)
        if text:
            return text

    return None


def save_issue_posts(
    top_keyword: str,
    posts: List[dict],
    output_path: Path,
) -> bool:
    """
    Save full contents of posts that contain the top keyword into a text file.
    """
    relevant_entries = []

    for index, post in enumerate(posts, 1):
        url = post.get("url")
        if not url:
            continue

        content = fetch_post_content(url)
        if not content:
            continue

        meta_line = (
            f"Rec {post['recommendations']} / Views {post['views']} / "
            f"Author {post['author']} / Time {post['display_time']}"
        )
        entry = "\n".join(
            [
                f"[Post {index}]",
                f"Title: {post['title']}",
                f"URL: {url}",
                meta_line,
                "",
                content,
            ]
        )
        relevant_entries.append(entry)

    if not relevant_entries:
        return False

    header = f"Top keyword: {top_keyword}"
    body = ("\n\n" + ("-" * 80) + "\n\n").join(relevant_entries)
    output_path.write_text(f"{header}\n\n{body}", encoding="utf-8")
    return True


def send_file_via_telegram(
    file_path: Path,
    token: str,
    chat_id: str,
    caption: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Send a local file to Telegram using the bot API.
    """
    if not file_path.exists():
        return False, f"파일이 존재하지 않습니다: {file_path}"

    if not token:
        return False, "텔레그램 봇 토큰이 설정되지 않았습니다."

    if not chat_id:
        return False, "텔레그램 chat_id가 설정되지 않았습니다."

    url = f"https://api.telegram.org/bot{token}/sendDocument"

    try:
        # Telegram sendDocument API 호출
        with file_path.open("rb") as file_obj:
            response = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption or ""},
                files={"document": file_obj},
                timeout=REQUEST_TIMEOUT,
            )
        if response.ok:
            return True, None
        return False, f"텔레그램 전송 실패 ({response.status_code}): {response.text}"
    except requests.exceptions.RequestException as exc:
        return False, f"텔레그램 요청 중 오류가 발생했습니다: {exc}"


def send_photo_via_telegram(
    file_path: Path,
    token: str,
    chat_id: str,
    caption: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Send a local image file to Telegram using the bot API's sendPhoto.
    """
    if not file_path.exists():
        return False, f"파일이 존재하지 않습니다: {file_path}"

    if not token or "YOUR_TELEGRAM_BOT_TOKEN" in token:
        return False, "텔레그램 봇 토큰이 설정되지 않았습니다."

    if not chat_id or "YOUR_TELEGRAM_CHAT_ID" in chat_id:
        return False, "텔레그램 chat_id가 설정되지 않았습니다."

    url = f"https://api.telegram.org/bot{token}/sendPhoto"

    try:
        with file_path.open("rb") as file_obj:
            response = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption or ""},
                files={"photo": file_obj},
                timeout=REQUEST_TIMEOUT,
            )
        return response.ok, response.text if not response.ok else None
    except requests.exceptions.RequestException as exc:
        return False, f"텔레그램 사진 전송 중 오류가 발생했습니다: {exc}"


def generate_word_cloud(
    word_freq: List[Tuple[str, int]],
    image_path: Path,
    font_path: Optional[Path] = None,
    max_words: int = 10,
) -> Tuple[bool, Optional[str]]:
    """
    Generate a word cloud image using the provided word frequencies.
    """
    if WordCloud is None:
        return False, "wordcloud 라이브러리가 설치되어 있지 않습니다."

    if not word_freq:
        return False, "워드 클라우드를 생성할 단어 데이터가 없습니다."

    # 상위 N개 빈도만 추려 시각화를 구성
    frequencies = dict(word_freq[:max_words])

    try:
        font = str(font_path) if font_path else None
        word_cloud = WordCloud(
            width=800,
            height=400,
            background_color="white",
            colormap="viridis",
            font_path=font,
        )
        word_cloud.generate_from_frequencies(frequencies)
        word_cloud.to_file(str(image_path))
        return True, None
    except Exception as exc:
        return False, f"워드 클라우드 생성 중 오류가 발생했습니다: {exc}"


def summarize_text_with_gemini(
    text_to_summarize: str, api_key: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Summarize the given text using the Gemini API.
    """
    if genai is None:
        return None, "google-generativeai 라이브러리가 설치되지 않았습니다."

    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        return None, "Gemini API 키가 설정되지 않았습니다."

    try:
        genai.configure(api_key=api_key)
        # model = genai.GenerativeModel("gemini-1.5-flash-latest")
        # 'gemini-1.5-flash-latest' 대신 'gemini-1.5-flash' 사용
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"{GEMINI_SUMMARY_PROMPT}{text_to_summarize}"

        response = model.generate_content(prompt)
        return response.text, None

    except Exception as e:
        return None, f"Gemini API 호출 중 오류가 발생했습니다: {e}"


if __name__ == "__main__":
    def safe_console_text(text: str) -> str:
        encoding = sys.stdout.encoding or "utf-8"
        return text.encode(encoding, errors="replace").decode(encoding, errors="replace")

    print(safe_console_text("Starting Clien 'Yesterday' board scraper."))

    # 1) 오늘 게시글 크롤링 후 2) 통계/파일 생성 3) 텔레그램 전송
    posts = scrape_clien_yesterday_posts()

    if posts:
        print(safe_console_text("\n--- Yesterday's posts ---"))
        for i, post in enumerate(posts, 1):
            line = (
                f"{i}. Rec {post['recommendations']} / Views {post['views']} / "
                f"Author {post['author']} / Time {post['display_time']} / Title {post['title']}"
            )
            print(safe_console_text(line))
        print(safe_console_text(f"\nCollected {len(posts)} posts from yesterday in total."))

        # 파일명 뒤에 날짜(YYMMDD)를 붙여 관리
        yesterday = datetime.now() - timedelta(days=1)
        date_suffix = yesterday.strftime("%y%m%d")
        
        # ./data 디렉토리 생성
        output_dir = Path(__file__).parent / "data"
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / f"clien_yesterday_posts_{date_suffix}.csv"
        save_posts_to_csv(posts, output_path)
        print(safe_console_text(f"\nSaved CSV to {output_path}"))

        word_freq, bigram_freq = calculate_title_frequencies(posts)

        if word_freq:
            print(safe_console_text("\n--- Top words in titles ---"))
            for token, count in word_freq:
                print(safe_console_text(f"{token}: {count}"))

            top_keyword = word_freq[0][0]
            # 제목 토큰에 최다 빈도 키워드가 포함된 게시물만 필터링
            matching_posts = [
                post for post in posts if top_keyword in tokenize_title(post["title"])
            ]
            issue_file_path = output_dir / f"YESTERDAY_ISSUE_{date_suffix}.txt"
            if matching_posts:
                # 필터링된 게시물 본문 저장 후 텔레그램 공유
                if save_issue_posts(top_keyword, matching_posts, issue_file_path):
                    print(
                        safe_console_text(
                            f"\nSaved top keyword ('{top_keyword}') posts to {issue_file_path}"
                        )
                    )
                    sent, send_error = send_file_via_telegram(
                        issue_file_path,
                        TELEGRAM_BOT_TOKEN,
                        TELEGRAM_CHAT_ID,
                        caption=f"Top keyword posts: {top_keyword}",
                    )
                    if sent:
                        print(
                            safe_console_text(
                                "\nSent YESTERDAY issue text file to Telegram successfully."
                            )
                        )
                    elif send_error:
                        print(safe_console_text(f"\n{send_error}"))

                    # Gemini 요약 및 전송 로직 추가
                    full_issue_content = issue_file_path.read_text(encoding="utf-8")
                    summary, gemini_error = summarize_text_with_gemini(full_issue_content, GEMINI_API_KEY)

                    if summary:
                        summary_file_path = output_dir / f"YESTERDAY_SUMMARY_{date_suffix}.txt"
                        summary_file_path.write_text(summary, encoding="utf-8")
                        print(safe_console_text(f"\nSaved Gemini summary to {summary_file_path}"))

                        # 요약 파일을 텔레그램으로 전송
                        sent_summary, summary_error = send_file_via_telegram(
                            summary_file_path,
                            TELEGRAM_BOT_TOKEN,
                            TELEGRAM_CHAT_ID,
                            caption=f"Gemini Summary for yesterday's top keyword: {top_keyword}",
                        )
                        if sent_summary:
                            print(
                                safe_console_text(
                                    "\nSent YESTERDAY summary text file to Telegram successfully."
                                )
                            )
                        elif summary_error:
                            print(safe_console_text(f"\n{summary_error}"))

                    elif gemini_error:
                        print(safe_console_text(f"\nGemini summarization failed: {gemini_error}"))

                else:
                    print(
                        safe_console_text(
                            "\nTop keyword와 매칭되는 게시물에서 본문을 가져오지 못했습니다."
                        )
                    )
            else:
                print(
                    safe_console_text(
                        "\nTop keyword와 일치하는 게시물이 목록에서 발견되지 않았습니다."
                    )
                )

        if bigram_freq:
            print(safe_console_text("\n--- Top bigrams in titles ---"))
            for token, count in bigram_freq:
                print(safe_console_text(f"{token}: {count}"))

        freq_output_path = output_dir / f"clien_yesterday_title_frequencies_{date_suffix}.csv"
        save_title_frequencies_to_csv(word_freq, bigram_freq, freq_output_path)
        print(safe_console_text(f"\nSaved title frequencies to {freq_output_path}"))
        # 제목 빈도 CSV를 텔레그램으로 전송
        sent_freq, freq_error = send_file_via_telegram(
            freq_output_path,
            TELEGRAM_BOT_TOKEN,
            TELEGRAM_CHAT_ID,
            caption=f"Clien yesterday({date_suffix}) title word frequencies",
        )
        if sent_freq:
            print(safe_console_text("\nSent title frequencies CSV to Telegram successfully."))
        elif freq_error:
            print(safe_console_text(f"\n{freq_error}"))

        # 워드 클라우드 이미지를 생성하고 저장
        word_cloud_path = output_dir / f"clien_yesterday_wordcloud_{date_suffix}.png"
        default_font_path = Path("C:/Windows/Fonts/malgun.ttf")
        font_path = default_font_path if default_font_path.exists() else None

        success, error_message = generate_word_cloud(word_freq, word_cloud_path, font_path=font_path)
        if success:
            print(safe_console_text(f"\nSaved word cloud image to {word_cloud_path}"))
            if font_path is None:
                print(
                    safe_console_text(
                        "한글 폰트를 찾지 못해 기본 폰트로 생성했습니다. 글자가 깨지면 `generate_word_cloud` 호출 시 `font_path`를 지정해주세요."
                    )
                )
            # 생성된 워드 클라우드 이미지를 텔레그램으로 전송
            sent_wc, wc_error = send_photo_via_telegram(
                word_cloud_path,
                TELEGRAM_BOT_TOKEN,
                TELEGRAM_CHAT_ID,
                caption=f"Clien yesterday({date_suffix}) top keywords word cloud",
            )
            if sent_wc:
                print(
                    safe_console_text(
                        "\nSent word cloud image to Telegram successfully."
                    )
                )
            elif wc_error:
                print(safe_console_text(f"\n{wc_error}"))
        elif error_message:
            print(safe_console_text(f"\n{error_message}"))
    else:
        print(safe_console_text("\nNo posts from yesterday were collected."))
