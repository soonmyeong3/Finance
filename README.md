# Bobi Backend

카드 소비 패턴 기반 초개인화 보험 추천 서비스 "보비"의 백엔드. 생명보험협회 공모전 2차 구현.

- 프론트엔드: https://github.com/sujeong0903/bobi-fe
- 팀 기획/데이터 문서: Notion "🧑‍💻 금융 공모전" 워크스페이스

## 지금까지 한 일

### 1. 노션 보험상품 DB 동기화

팀이 노션 "보험 보장 표준 분류체계"에 이미 수집해둔 실제 보험 데이터를 백엔드 DB로 가져왔다.

- **보험상품** 19건 (삼성화재·현대해상·DB손해보험·KB손해보험·메리츠화재 5개 손보사, 건강/운전자/치아/여행/주택재물/반려동물/기타 7개 분류)
- **표준보장** 65건 (보험사 간 담보 비교 기준 — `HEALTH_CANCER_DIAG` 같은 표준코드)
- **상품-보장매핑** 122건 (상품의 원본 담보명 ↔ 표준보장코드 연결, 전량 매칭 검증 완료)

`data/notion_export/*.json`이 스냅샷이고, `scripts/load_notion_insurance_export.py`가 이걸 자연키 기준으로 upsert한다. 노션이 계속 단일 소스(source of truth) — 재수집 시 export 다시 뜨고 스크립트 재실행하면 된다 (멱등).

### 2. 가짜 카드 데이터 생성기

`app/services/fake_data_generator.py` — 페르소나 기반 가짜 카드결제 생성기. 실제 카드 데이터는 마이데이터 사업자 라이선스 문제로 못 쓰므로 합성 데이터로 대체 (`industrial_area_worker`, `new_pet_owner`, `frequent_dental` 3개 시나리오, 가맹점 카테고리 가중치 기반).

산업단지/인구밀도/질병통계 지리 매칭 파이프라인과 그 위의 스코어링 로직은 한 번 만들었다가 걷어냈다 — 실제 추천 랭킹은 추천 모델 담당자의 영역이라 백엔드가 미리 설계를 정해버리는 게 맞지 않다고 판단.

### 3. 생애주기 변화 감지 → 알림함

`app/services/life_event_detector.py` — `Notification` 테이블이 모델만 있고 채워주는 로직이 없던 걸 구현. 카드 거래를 최근 30일 vs 그 이전 30일로 나눠 규칙 기반으로 diff:

- 반려동물 관련 카테고리(동물병원·반려동물용품)가 최근에 **처음** 등장 → "생애주기 변화"
- 치과 결제가 최근 30일에 **3회 이상 반복** → "생활 패턴 변화"
- 병원·약국 지출이 이전 기간 대비 **1.5배 이상 급증** → "지출 급증"

순수 집계/카운팅이라 추천 모델 스코어링과는 다른 영역(감지 vs 랭킹)으로 판단해 백엔드에 뒀다. `POST /users/{id}/notifications/detect`로 트리거 — 실서비스라면 주기적 배치 잡이 될 자리.

### 4. 카드 명세서 업로드 파서 (CSV/PDF)

`app/services/card_statement_parser.py` — 가짜 데이터 생성 말고, 실제 파일을 올려서 거래내역으로 바꾸는 경로. `POST /users/{id}/cards/statements` (multipart).

- **CSV**: 카드사마다 컬럼명이 달라서(`이용일자`/`거래일자`, `가맹점명`/`가맹점` 등) 헤더를 휴리스틱으로 매칭. 가맹점명은 키워드 매칭으로 `merchant_category`(동물병원/치과/편의점 등)로 분류.
- **PDF**: `pdfplumber`로 텍스트 뽑고 "날짜 가맹점명 금액" 한 줄 패턴을 정규식으로 매칭. **이 부분이 가장 검증이 약한 곳** — 실제 카드사 명세서 PDF 레이아웃은 회사마다 다른데 샘플 파일이 없어서 합성 PDF로 파서 로직 자체만 검증했다. 실제 파일이 생기면 다시 봐야 함.

`CardTransaction`에 `merchant_name`(원본 가맹점명), `source`(fake/csv_upload/pdf_upload) 필드를 추가해서 가짜 데이터랑 실제 업로드 데이터를 구분할 수 있게 함.

### 5. 보장 공백 분석 (Coverage Gap Analysis)

`app/services/coverage_gap.py` — 동기화한 상품-보장매핑(122건)이 지금까지 상품 하나 조회할 때 담보 목록 보여주는 데만 쓰이고 있었는데, 이 데이터의 원래 목적(보험사 간 담보를 표준코드로 묶어 비교)을 처음으로 실제 기능에 씀.

`GET /users/{id}/insurance/gaps` — 사용자가 **가입중**인 보험이 커버하는 표준보장코드를 전부 모아서, 전체 65종 표준보장 카탈로그와 보장영역별로 diff. 놓치고 있는 담보 목록을 알려주고, 최근 생애주기 알림(`cta_product_category`)과 같은 영역이면 우선 노출.

- "이걸 사세요"(스코어링)가 아니라 "이게 비어있어요"(diff)라서 생애주기 감지와 같은 이유로 추천 모델 영역이 아니라고 판단
- **가입예정(planned) 보험은 공백을 메꾼 걸로 안 침** — 아직 효력이 없으니까. (리팩토링 중 발견한 버그: 처음엔 가입예정도 커버로 쳐서, 전부 "가입예정"으로만 등록해도 공백이 0으로 나오는 허점이 있었음)

## 프로젝트 구조

FastAPI + SQLAlchemy 기반.

```
app/
├── main.py              FastAPI 앱, 라우터 등록
├── core/                설정, DB 세션
├── models/               SQLAlchemy 모델
├── schemas/              Pydantic 스키마
├── api/routes/           엔드포인트
└── services/             비즈니스 로직 (가짜 카드데이터 생성, 생애주기 감지, 명세서 파서, 보장 공백 분석, 스크래퍼)
scripts/                 DB 초기화, 노션 동기화 스크립트
tests/                   pytest 슈트
data/notion_export/      노션에서 뜬 보험 데이터 스냅샷 (JSON)
docker-compose.yml        Postgres
```

## 로컬 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d                                # Postgres 기동
cp .env.example .env

python scripts/init_db.py                           # 테이블 생성
python scripts/load_notion_insurance_export.py       # 노션 보험 데이터 적재

uvicorn app.main:app --reload                        # http://localhost:8000/docs
```

**테스트**: `tests/` — pytest + 인메모리 SQLite, 20개 (생애주기 감지·노션 로더 멱등성·명세서 파서·보장 공백 분석).

```bash
pip install -r requirements-dev.txt
pytest
```
