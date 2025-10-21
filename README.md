# Clien Today & Yesterday Scraper

Python 스크립트 `clien_today_scraper.py`와 `clien_yesterday_scraper.py`는 클리앙(Clien) 커뮤니티의 게시물을 수집하고, 통계/이슈 분석 및 요약 결과를 파일과 텔레그램으로 전송하는 자동화 도구입니다.

## 주요 기능
- **오늘/어제 게시물 수집**: 클리앙 '모두의 공원' 게시판에서 오늘 또는 어제 게시물의 메타데이터(제목, 추천, 조회수 등)를 수집합니다.
- **데이터 저장**: 수집 결과를 날짜별 CSV 파일로 저장합니다.
- **키워드 빈도 분석**: 게시물 제목을 분석하여 주요 단어/바이그램 빈도를 계산하고 CSV 파일로 저장합니다.
- **워드 클라우드 생성**: 상위 키워드를 기반으로 워드 클라우드 이미지를 생성합니다.
- **이슈 게시물 추출**: 빈도가 가장 높은 키워드가 포함된 게시물들의 본문을 텍스트 파일로 저장합니다.
- **Gemini AI 요약**: 추출된 이슈 게시물 본문을 Gemini API를 통해 3~5 문장으로 요약하고, 별도의 텍스트 파일로 저장합니다.
- **텔레그램 알림**: 생성된 모든 결과물(CSV, 이슈 TXT, 요약 TXT)을 지정된 텔레그램 채팅으로 전송합니다.

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
- **어제 게시물 수집 및 분석**
  ```bash
  python clien_yesterday_scraper.py
  ```

## 출력 파일
스크립트 실행 시점에 따라 `today` 또는 `yesterday` 접두사가 붙은 파일들이 생성됩니다.

- `clien_{day}_posts_{YYMMDD}.csv`: 게시물 메타데이터 목록
- `clien_{day}_title_frequencies_{YYMMDD}.csv`: 단어 및 바이그램 빈도표
- `clien_{day}_wordcloud_{YYMMDD}.png`: 상위 단어 기반 워드 클라우드 이미지
- `{DAY}_ISSUE_{YYMMDD}.txt`: 최상위 키워드 관련 게시물 본문 모음
- `{DAY}_SUMMARY_{YYMMDD}.txt`: Gemini AI가 요약한 이슈 본문

각 파일은 스크립트와 같은 폴더에 생성되며, 날짜 접미사(YYMMDD)가 붙습니다.

## 주의 사항
- 스크레이핑 대상 사이트 구조가 변경되면 본문 추출이나 목록 파싱이 실패할 수 있습니다. CSS 셀렉터를 업데이트해야 합니다.
- 게시글 수가 많을 경우 수집에 시간이 소요될 수 있으며, 과도한 요청은 서버에 부담이 될 수 있습니다.
- API 키나 토큰이 유효하지 않으면 텔레그램 전송 또는 AI 요약에 실패합니다. `.env` 파일의 값을 확인하세요.
