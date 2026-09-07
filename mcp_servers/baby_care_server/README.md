# baby_care_server

영유아 육아 기록 저장·조회와 기저귀 사진 분석을 담당할 MCP 서버입니다.

18단계 구현과 Mock 기반 검증까지 완료되었으며, 실제 stool 색인 데이터가 준비되면 조건부 통합 테스트만 실행하면 됩니다.

- `record_care_event`
- `get_care_records`
- `analyze_infant_stool`

`record_care_event`는 수유·수면·기저귀·성장 기록을 PostgreSQL에 저장합니다. `get_care_records`는 오늘·기간별 기록과 최근 수유를 조회하며 `analyze_infant_stool`은 Vision·규칙·공용 stool RAG Workflow를 실행합니다.

수유 저장은 다음 규칙을 적용합니다.

- `text`, `ui`: 별도 승인 없이 저장
- `stt`: `confirmed_by_user=true`일 때만 저장
- `amount_ml`: 입력 시 0~500
- 중복 `idempotency_key`: 기존 기록과 `duplicated=true` 반환
- `recorded_at` 생략: `Asia/Seoul` 현재 시각 사용

기저귀 기록은 다음 규칙을 적용합니다.

- `urine`, `stool` 중 하나 이상은 `true`
- `color`, `consistency`, `memo`는 입력된 값만 저장
- 수유 등 다른 이벤트용 필드는 기저귀 `details`에 저장하지 않음

성장 기록은 다음 규칙을 적용합니다.

- `weight_kg`, `height_cm`, `head_circumference_cm` 중 하나 이상 입력
- 모든 성장값은 0보다 큰 값만 허용
- 입력된 성장값만 저장하며 정상·비정상 여부는 판단하지 않음
- 다른 이벤트용 필드는 성장 `details`에 저장하지 않음

수면 기록은 다음 규칙을 적용합니다.

- `action`은 `start` 또는 `end` 필수
- 진행 중인 수면이 있는데 다시 시작하면 `SLEEP_ALREADY_STARTED`
- 시작 기록 없이 종료하면 `SLEEP_START_NOT_FOUND`
- 수면 `details`에는 `action`만 저장

기록 조회는 다음 규칙을 적용합니다.

- `today`: `Asia/Seoul` 기준 오늘 00:00부터 다음 날 00:00 전까지 조회
- `range`: `start_date`와 `end_date` 날짜를 모두 포함
- 오래된 기록부터 순서대로 반환
- 기록이 없으면 오류가 아닌 `records=[]` 반환
- 모든 조회 유형에서 공통 상위 Response Schema 사용
- `latest_feeding`: 가장 최근 수유 한 건만 `latest_feeding`에 반환
- 수유 기록이 없으면 오류가 아닌 `latest_feeding=null` 반환

패턴 조회는 다음 규칙을 적용합니다.

- `pattern`: 한국 날짜 기준 오늘을 포함한 최근 `days`일 계산 (`1~30`, 기본 7)
- 충분한 데이터: 전체 기록 5건 이상이며 서로 다른 기록 날짜 3일 이상
- 데이터가 부족해도 계산 가능한 통계는 반환하고, 계산 불가능한 평균은 `null`
- 평균 수유량은 `amount_ml`이 입력된 기록만 사용하며 `0ml`도 포함
- 평균 수유 간격은 수유 기록이 2건 이상일 때 계산
- 수면 시간은 정상적인 `start → end` 쌍만 계산
- 기저귀 소변·대변 횟수는 각각 값이 `true`인 기록을 계산

기저귀 이미지 입력은 다음 규칙을 적용합니다.

- `IMAGE_TEMP_DIRECTORY`로 지정한 공용 임시 폴더 내부 경로만 허용
- JPG, JPEG, PNG 확장자만 허용
- `IMAGE_MAX_BYTES` 이하 파일만 허용
- Pillow로 실제 이미지인지 확인하고 확장자와 실제 형식이 일치하는지 검사
- 최소 해상도·밝기·선명도를 로컬에서 검사
- 품질이 부족하면 오류가 아닌 `success=true`, `is_analyzable=false` 반환
- 품질을 통과하면 OpenAI Responses API의 구조화 출력으로 관찰 결과 생성
- 사진에서 보이는 특징만 반환하며 진단·처방을 생성하지 않음
- YAML 고정 규칙으로 `none`, `attention`, `urgent`, `emergency` 중 하나를 반환
- 붉은 영역, 검고 타르 같은 모습, 흰색·회백색 모습은 `urgent`로 안내
- 발열, 잦은 배변, 관찰 불확실성은 `attention`으로 추가 확인
- 생후 3개월 미만의 발열 입력은 `urgent`로 즉시 의료진 연락 안내
- 사진만으로 `emergency`를 판정하지 않으며 전신 상태 확인은 후속 단계에서 연동
- 발열·배변 횟수 등 입력이 없으면 필요한 추가 질문 반환
- `nomic-embed-text` 768차원 Query 임베딩과 pgvector로 `category='stool'`만 조회
- RAG 결과가 없으면 정상적으로 `sources=[]` 반환
- RAG 장애 시 분석은 유지하고 `RAG_SERVICE_ERROR` 경고 반환
- 공용 업로드 루트 기준 `temporary/{uuid}.jpg` 상대경로 지원
- 정상 처리 후 임시 이미지를 삭제하며 이미 삭제된 파일도 오류로 처리하지 않음
- 이미지 검증 → 품질 검사 → Vision → 위험도 → stool RAG → 삭제 순서를 Workflow에서 고정
- Backend 합의 응답 Schema를 유지하며 별도의 `answer` 필드는 추가하지 않음
- Workflow 순서, RAG 장애 격리, 경로 이탈 차단, 성공·실패별 파일 삭제 정책을 테스트로 검증

## 실행 준비

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 실행

팀 저장소 루트에서 실행합니다.

```powershell
python -m mcp_servers.baby_care_server.server
```

기본 MCP 주소는 `http://127.0.0.1:8101/mcp`입니다.

공유 이미지 폴더는 기본적으로 팀 저장소 루트의 `uploads`이며 환경변수로 변경할 수 있습니다.

```text
IMAGE_TEMP_DIRECTORY=uploads
IMAGE_MAX_BYTES=10485760
IMAGE_MIN_WIDTH=224
IMAGE_MIN_HEIGHT=224
IMAGE_DARK_THRESHOLD=35
IMAGE_BRIGHT_THRESHOLD=235
IMAGE_BLUR_THRESHOLD=20
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMENSION=768
OLLAMA_TIMEOUT_SECONDS=30
RAG_TOP_K=5
RAG_MIN_SIMILARITY=0.70
```

Care Server를 Docker에서 실행하고 Ollama를 Windows 호스트에서 실행할 때는 다음 주소를 사용합니다.

```text
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Ollama도 Compose의 `ollama` 서비스로 실행할 때만 `http://ollama:11434`를 사용합니다.

## 로컬 PostgreSQL

팀 저장소의 루트 `docker-compose.yml` 구성은 통합 단계에서 팀 설정에 맞춰 추가합니다. 현재는 별도로 실행한 PostgreSQL에 연결하며, 테이블 생성 SQL은 `mcp_servers/baby_care_server/database`에 있습니다.

기본 접속정보는 다음과 같습니다.

```text
host=localhost
port=5432
database=baby_ai
user=postgres
password=password
```

`database/01_schema.sql`은 실제 `care_logs`와 외래키 테스트에 필요한 최소 `babies` 테이블을 생성합니다. 실제 `babies` 기능은 Backend 담당이며, `database/02_seed.sql`의 `baby-001`은 로컬 테스트 전용입니다.

Repository는 `repositories/care_log_repository.py`에 있으며 다음 기능을 제공합니다.

- 아기 ID 존재 확인
- `idempotency_key`로 기존 기록 조회
- 육아 기록 한 건 저장
- 기간별 기록 조회
- 마지막 수유 기록 조회
- 진행 중인 수면 조회

통합 DB 계정은 `care_logs`에 필요한 기록 권한을 가지되, Info Server가 관리하는 `documents`, `document_chunks`에는 `SELECT` 권한만 가져야 합니다.

실제 PostgreSQL Repository 테스트는 DB 컨테이너를 실행한 상태에서 다음 명령으로 실행합니다.

```powershell
$env:RUN_DB_TESTS = "1"
python -m pytest -q .\mcp_servers\baby_care_server\tests
Remove-Item Env:RUN_DB_TESTS
```

## 실제 stool RAG 통합 테스트

Info Server가 공식 stool 문서를 `nomic-embed-text` 768차원으로 색인하고 Ollama가 실행된 후 아래 테스트를 실행합니다.

```powershell
$env:RUN_RAG_DB_TESTS = "1"
python -m pytest -q .\mcp_servers\baby_care_server\tests\test_stool_rag_integration.py
Remove-Item Env:RUN_RAG_DB_TESTS
```

이 테스트는 실제 Query 임베딩, `category='stool'` 검색, 월령·유사도 조건, 저장 벡터 차원과 RAG 테이블 읽기 전용 권한을 확인합니다. 색인 데이터가 준비되지 않은 일반 테스트에서는 자동으로 건너뜁니다.
