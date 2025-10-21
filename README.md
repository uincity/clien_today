# Clien Today Scraper

Python 스크립트 `clien_today_scraper.py`는 클리앙(Clien) 커뮤니티의 오늘자 게시물을 수집하고, 통계/이슈 분석 결과를 파일과 텔레그램으로 전송하는 자동화 도구입니다.

## 주요 기능
- 클리앙 `오늘의 게시판`에서 금일 게시물의 제목, 추천 수, 조회 수, 작성자, 시간, URL을 페이지 끝까지 수집
- 수집 결과를 `clien_today_posts_YYMMDD.csv`로 저장 (UTF-8 BOM)
- 제목에서 파생한 단어/바이그램 빈도 계산 후 `clien_today_title_frequencies_YYMMDD.csv`로 저장
- 상위 10개 단어로 워드 클라우드 이미지를 생성 (`clien_title_wordcloud_YYMMDD.png`)
- 빈도 최상위 키워드를 포함한 게시물 본문을 추출해 `TODAY_ISSUE_YYMMDD.txt`로 저장
- 빈도 CSV와 이슈 TXT를 지정된 텔레그램 챗으로 전송

## 필요 조건
- Python 3.9 이상 권장
- 설치가 필요한 패키지
  - `requests`
  - `beautifulsoup4`
  - `wordcloud` (워드 클라우드 생성 시)
- 워드 클라우드에서 한글 깨짐을 방지하려면 OS에 한글 폰트가 설치되어 있어야 합니다 (`C:/Windows/Fonts/malgun.ttf` 기본 사용).

## 실행 방법
```bash
python clien_today_scraper.py
```

스크립트는 실행 시 즉시 최신 데이터를 수집하며, 파일을 생성한 뒤 텔레그램 전송까지 자동으로 진행합니다.

## 텔레그램 연동
- 봇 토큰과 `chat_id`는 소스 상단의 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 상수로 지정되어 있습니다.
- 다른 챗으로 보내고 싶다면 해당 값을 수정하거나, 실행 전에 환경 변수 등을 활용해 주입할 수 있도록 코드를 확장하세요.
- 텔레그램 API 호출에는 인터넷 연결이 필요합니다.

## 출력 파일
- `clien_today_posts_YYMMDD.csv`: 게시물 메타데이터 목록
- `clien_today_title_frequencies_YYMMDD.csv`: 단어 및 바이그램 빈도표
- `clien_title_wordcloud_YYMMDD.png`: 상위 단어 기반 워드 클라우드 이미지
- `TODAY_ISSUE_YYMMDD.txt`: 최상위 키워드 관련 게시물 본문 모음

각 파일은 스크립트와 같은 폴더에 생성되며, 날짜 접미사(YYMMDD)가 붙습니다.

## 주의 사항
- 스크레이핑 대상 사이트 구조가 변경되면 본문 추출이나 목록 파싱이 실패할 수 있습니다. CSS 셀렉터를 업데이트해야 합니다.
- 게시글 수가 많을 경우 수집에 시간이 소요될 수 있으며, 과도한 요청은 서버에 부담이 될 수 있습니다.
- 텔레그램 전송에 실패하면 콘솔에 오류 메시지가 출력됩니다. 토큰/챗 ID, 네트워크 상태를 확인하세요.
