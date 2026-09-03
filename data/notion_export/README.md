# 노션 보험 데이터 (`data/notion_export/`)

노션 "보험 보장 표준 분류체계"에서 뜬 스냅샷 3개. `scripts/load_notion_insurance_export.py`가 이걸 DB로 적재한다. 노션이 계속 단일 소스(source of truth) — 재수집 시 이 파일들을 다시 export하고 로더를 재실행하면 된다 (멱등).

## 테이블 3개와 관계

```
products.json (보험상품, 19건)
    ↓ 상품명으로 연결
product_coverage_mapping.json (상품-보장매핑, 122건)
    ↓ 표준보장코드로 연결
standard_coverages.json (표준보장, 65건)
```

- **products.json** — 어떤 보험 상품이 있나. 보험사, 상품명, 카테고리.
- **standard_coverages.json** — 보장 항목의 공통 사전. 보험사마다 표현은 달라도 같은 성격이면 같은 코드로 묶임.
- **product_coverage_mapping.json** — 위 둘을 잇는 연결다리. "이 상품의 이 담보 조항은 저 표준코드에 해당한다."

## 왜 중간에 매핑 테이블이 필요한가

보험사마다 같은 보장을 다르게 부른다. 예를 들어 현대해상 "굿앤굿우리펫보험" 하나의 담보 목록만 봐도:

| 원본 담보명 | 표준보장코드 |
|---|---|
| 특정약물치료 | `PET_MEDICAL_TREATMENT` |
| MRI/CT 추가 보장 | `PET_MEDICAL_TREATMENT` |
| 치과치료(치석제거 및 부정교합 포함) | `PET_MEDICAL_TREATMENT` |

셋 다 이름은 다르지만 실제로는 같은 성격(반려동물 검사·치료비)이다. 이름 그대로는 프로그램이 "이 상품에 그 보장이 있나"를 비교할 수 없으니, 표준코드 하나로 묶어둔다.

## 실제 데이터로 한 줄씩 추적

**1) `products.json`에서 상품 하나:**

```json
{
  "product_id": 15,
  "insurer": "현대해상",
  "name": "굿앤굿우리펫보험",
  "category": "반려동물"
}
```

**2) `product_coverage_mapping.json`에서 이 상품의 담보 7개:**

```
"방광염·복막염 등 의료비"        →  PET_MEDICAL_TREATMENT
"반려동물 입원의료비"            →  PET_HOSPITAL
"반려동물 수술비"                →  PET_SURGERY
"특정약물치료"                   →  PET_MEDICAL_TREATMENT
"MRI/CT 추가 보장"               →  PET_MEDICAL_TREATMENT
"치과치료(치석제거 및 부정교합)"  →  PET_MEDICAL_TREATMENT
"반려동물 통원의료비"            →  PET_OUTPATIENT
```

**3) `standard_coverages.json`에서 그 코드의 정체:**

```json
{
  "code": "PET_MEDICAL_TREATMENT",
  "name": "반려동물 검사·치료비",
  "coverage_area": "반려동물",
  "risk_type": "반려동물 질병·상해",
  "coverage_form": "치료"
}
```

## 코드에서 쓰는 곳

`app/services/coverage_gap.py`가 이 3단 연결을 그대로 join한다:

1. 사용자가 가입한 보험(`UserInsurance`) → `product_id`
2. `product_id`로 `ProductCoverageMapping` 조회 → 이 사람이 실제로 커버받는 `coverage_code` 집합
3. 전체 `StandardCoverage`(65개) 중 그 집합에 없는 코드 = **보장 공백**

예를 들어 "굿앤굿우리펫보험"만 가입했다면 위 7개 매핑 덕분에 `PET_MEDICAL_TREATMENT`/`PET_HOSPITAL`/`PET_SURGERY`/`PET_OUTPATIENT` 4개 코드는 커버로 잡히고, 다른 보장영역(치아·운전자 등)은 전부 공백으로 잡혀 `GET /users/{id}/insurance/gaps`가 이걸 알려준다.
