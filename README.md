# Clien Daily Scraper

Python 스크립트 `clien_today_scraper.py`와 `clien_daily_scraper.py`는 클리앙(Clien) 커뮤니티의 게시물을 수집하고, 통계/이슈 분석 및 요약 결과를 파일과 텔레그램으로 전송하는 자동화 도구입니다.

- `clien_today_scraper.py`: **오늘** 게시물을 실시간으로 수집하고 분석합니다.
- `clien_daily_scraper.py`: **특정 날짜**의 게시물을 수집하고 분석합니다. (기본값: 어제)

## 주요 기능
- **일별 게시물 수집**: 클리앙 '모두의 공원' 게시판에서 지정된 날짜의 게시물 메타데이터(제목, 추천, 조회수 등)를 수집합니다.
- **데이터 저장**: 수집 결과를 날짜별 CSV 파일로 저장합니다.
- **키워드 빈도 분석**: 게시물 제목을 분석하여 주요 단어/바이그램 빈도를 계산하고 CSV 파일로 저장합니다.
- **워드 클라우드 생성**: 상위 키워드를 기반으로 워드 클라우드 이미지를 생성합니다.
- **이슈 게시물 추출**: 빈도가 가장 높은 키워드가 포함된 게시물들의 본문을 텍스트 파일로 저장합니다.
- **Gemini AI 요약**: 추출된 이슈 게시물 본문을 Gemini API를 통해 3~5 문장으로 요약하고, 별도의 텍스트 파일로 저장합니다.
- **텔레그램 알림**: 생성된 모든 결과물(CSV, 이슈 TXT, 요약 TXT, 워드 클라우드 이미지)을 지정된 텔레그램 채팅으로 전송합니다.

## 필요 조건
- Python 3.9 이상 권장
- 설치가 필요한 패키지
  - `requests`
  - `beautifulsoup4`
  - `wordcloud` (워드 클라우드 생성 시)
  - `python-dotenv` (환경 변수 관리)
  - `google-generativeai` (Gemini AI 요약)
- 워드 클라우드에서 한글 깨짐을 방지하려면 OS에 한글 폰트가 설치되어 있어야 합니다 (`C:/Windows/Fonts/malgun.ttf` 기본 사용).

## 설정 방법
1.  **필요 패키지 설치**
    ```bash
    pip install requests beautifulsoup4 wordcloud python-dotenv google-generativeai
    ```
2.  **.env 파일 생성**
    스크립트가 있는 폴더에 `.env` 파일을 생성하고 아래 내용을 채워넣습니다.
    ```
    TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID=YOUR_TELEGRAM_CHAT_ID
    GEMINI_API_KEY=YOUR_GEMINI_API_KEY
    ```

## 실행 방법
- **오늘 게시물 수집 및 분석**
    ```bash
    python clien_today_scraper.py
    ```

- **특정 날짜 게시물 수집 및 분석**
  `clien_daily_scraper.py` 스크립트를 사용합니다. `--date` 인자를 사용하여 날짜를 지정할 수 있으며, 생략 시 어제 날짜가 기본값으로 사용됩니다.

  - **어제 날짜 (기본값)**
    ```bash
    python clien_daily_scraper.py
    ```

  - **특정 날짜 지정 (YYYY-MM-DD 형식)**
    ```bash
    python clien_daily_scraper.py --date 2025-10-22
    ```

## 출력 파일
스크립트는 실행된 날짜를 기준으로 `data/` 폴더 내에 다음과 같은 결과물을 생성합니다. 파일명에는 수집 대상 날짜(`YYMMDD` 형식)가 포함됩니다.

- `clien_today_posts_{YYMMDD}.csv` / `clien_yesterday_posts_{YYMMDD}.csv`: 게시물 메타데이터 목록
- `clien_today_title_frequencies_{YYMMDD}.csv` / `clien_title_frequencies_{YYMMDD}.csv`: 단어 및 바이그램 빈도표
- `clien_today_wordcloud_{YYMMDD}.png` / `clien_wordcloud_{YYMMDD}.png`: 상위 단어 기반 워드 클라우드 이미지
- `TODAY_ISSUE_{YYMMDD}.txt` / `CLIEAN_ISSUE_{YYMMDD}.txt`: 최상위 키워드 관련 게시물 본문 모음
- `TODAY_SUMMARY_{YYMMDD}.txt` / `CLIEAN_SUMMARY_{YYMMDD}.txt`: Gemini AI가 요약한 이슈 본문

## 버전 관리
이 프로젝트는 `.gitignore` 파일을 사용하여 다음 항목들을 Git 버전 관리에서 제외합니다.
- `data/`: 스크래핑 결과물이 저장되는 폴더입니다. 생성된 데이터는 커밋되지 않습니다.
- `.env`: API 키 등 민감한 정보를 담고 있는 파일입니다. 보안을 위해 커밋되지 않습니다.
- `__pycache__/`, `*.pyc`: 파이썬 캐시 파일입니다.

## 주의 사항
- 스크레이핑 대상 사이트 구조가 변경되면 본문 추출이나 목록 파싱이 실패할 수 있습니다. CSS 셀렉터를 업데이트해야 합니다.
- 게시글 수가 많을 경우 수집에 시간이 소요될 수 있으며, 과도한 요청은 서버에 부담이 될 수 있습니다.
- API 키나 토큰이 유효하지 않으면 텔레그램 전송 또는 AI 요약에 실패합니다. `.env` 파일의 값을 확인하세요.
