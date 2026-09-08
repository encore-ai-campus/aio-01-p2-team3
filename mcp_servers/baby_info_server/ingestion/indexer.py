import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

import psycopg

from config import get_settings
from ingestion.chunker import chunk_text
from ingestion.document_loader import load_document
from services.embedding_service import EmbeddingService


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


RAG_DOCUMENTS: tuple[dict[str, object], ...] = (
    {
        "file": "kdca_neonatal_jaundice_pale_stool.pdf",
        "title": "신생아 황달과 무담즙변",
        "organization": "질병관리청",
        "source_url": "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5723",
        "category": "stool",
        "verified_at": "2026-09-03",
        "age_min_months": 0,
        "age_max_months": 1,
        "topic": "pale_stool",
        "urgency_level": "urgent",
    },
    {
        "file": "kdca_pediatric_bloody_black_stool.pdf",
        "title": "소아청소년의 혈변 및 흑색변",
        "organization": "질병관리청",
        "source_url": "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5721",
        "category": "stool",
        "verified_at": "2026-09-03",
        "age_min_months": 0,
        "age_max_months": 36,
        "topic": "bloody_black_stool",
        "urgency_level": "warning",
    },
    {
        "file": "kdca_infant_nutrition.pdf",
        "title": "영유아 영양 - 설사·탈수·변비 근거",
        "organization": "질병관리청",
        "source_url": "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5212",
        "category": "stool",
        "verified_at": "2026-09-03",
        "age_min_months": 0,
        "age_max_months": 36,
        "pages": [4, 5, 7],
        "topic": "diarrhea_dehydration_constipation",
        "urgency_level": "warning",
    },
    {
        "file": "kdca_infant_nutrition.pdf",
        "title": "식이영양 - 영유아",
        "organization": "질병관리청",
        "source_url": "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5212",
        "category": "feeding",
        "verified_at": "2026-09-03",
        "age_min_months": 0,
        "age_max_months": 36,
        "topic": "infant_nutrition",
    },
    {
        "file": "kdca_complementary_feeding.pdf",
        "title": "이유기 보충식",
        "organization": "질병관리청",
        "source_url": "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5470",
        "category": "weaning",
        "verified_at": "2026-09-03",
        "age_min_months": 4,
        "age_max_months": 36,
        "topic": "complementary_feeding",
    },
    {
        "file": "kca_child_safety_guide.pdf",
        "title": "어린이 안전사고 예방가이드",
        "organization": "한국소비자원",
        "source_url": "https://www.kca.go.kr/smartconsumer/sub.do?menukey=7101&mode=view&no=1002684540",
        "category": "safety",
        "verified_at": "2026-09-03",
        "age_min_months": 0,
        "age_max_months": 36,
        "topic": "child_safety",
    },
    {
        "file": "nhis_01_03_months.pdf",
        "title": "영아기 초기 보호자용 설명서 - 안전사고 예방",
        "organization": "국민건강보험공단",
        "source_url": "https://www.nhis.or.kr/file/a/001/po5a/A4_E40_all.pdf",
        "category": "safety",
        "verified_at": "2026-09-03",
        "pages": [3, 5],
        "age_min_months": 1,
        "age_max_months": 3,
        "topic": "infant_safety",
    },
    {
        "file": "nhis_04_06_months.pdf",
        "title": "4-6개월 보호자용 설명서 - 수면",
        "organization": "국민건강보험공단",
        "source_url": "https://www.nhis.or.kr/file/a/001/po5a/A4_E41_summary.pdf",
        "category": "sleep",
        "verified_at": "2026-09-03",
        "pages": [2],
        "age_min_months": 4,
        "age_max_months": 6,
        "topic": "sleep_routine",
    },
    {
        "file": "nhis_09_12_months.pdf",
        "title": "9-12개월 보호자용 설명서 - 안전사고 예방",
        "organization": "국민건강보험공단",
        "source_url": "https://www.nhis.or.kr/file/a/001/po5a/A4_E42_summary.pdf",
        "category": "safety",
        "verified_at": "2026-09-03",
        "pages": [2],
        "age_min_months": 9,
        "age_max_months": 12,
        "topic": "choking_and_transport_safety",
    },
    {
        "file": "nhis_18_24_months.pdf",
        "title": "18-24개월 보호자용 설명서 - 발달선별검사",
        "organization": "국민건강보험공단",
        "source_url": "https://www.nhis.or.kr/file/a/001/po5a/A4_E43_summary.pdf",
        "category": "development",
        "verified_at": "2026-09-03",
        "pages": [2],
        "age_min_months": 18,
        "age_max_months": 24,
        "topic": "developmental_screening",
    },
    {
        "file": "nhis_30_36_months.pdf",
        "title": "30-36개월 보호자용 설명서 - 취학 전 발달 준비",
        "organization": "국민건강보험공단",
        "source_url": "https://www.nhis.or.kr/file/a/001/po5a/A4_E44_summary.pdf",
        "category": "development",
        "verified_at": "2026-09-03",
        "pages": [2],
        "age_min_months": 30,
        "age_max_months": 36,
        "topic": "preschool_development",
    },
    {
        "file": "kdca_kdst_manual.pdf",
        "title": "한국 영유아 발달선별검사(K-DST) 개정판 사용지침서",
        "organization": "질병관리청",
        "source_url": "https://kdca.go.kr/kdca/2861/subview.do?enc=Zm5jdDF8QEB8JTJGYmJzJTJGa2RjYSUyRjU1JTJGMjI3NjExJTJGYXJ0Y2xWaWV3LmRvJTNG",
        "category": "development",
        "verified_at": "2026-09-03",
        "pages": list(range(9, 44)),
        "age_min_months": 4,
        "age_max_months": 36,
        "topic": "developmental_screening_guidance",
    },
)


def catalog_metadata(file_name: str, category: str) -> dict[str, object]:
    """파일명과 카테고리에 맞는 공식 문서 메타데이터 복사본을 반환합니다."""
    for document in RAG_DOCUMENTS:
        if document["file"] == file_name and document["category"] == category:
            return {key: value for key, value in document.items() if key != "file"}
    raise ValueError("색인 대상 공식 문서 메타데이터를 찾지 못했습니다.")


async def initialize_schema() -> None:
    """Info Server가 관리하는 공용 RAG 테이블과 검색 인덱스를 생성합니다."""
    settings = get_settings()
    dimensions = settings.embedding_dimensions
    statements = (
        "CREATE EXTENSION IF NOT EXISTS vector",
        """
        CREATE TABLE IF NOT EXISTS documents (
            id VARCHAR(100) PRIMARY KEY,
            title TEXT NOT NULL,
            organization TEXT NOT NULL,
            source_url TEXT NOT NULL,
            category VARCHAR(30) NOT NULL,
            published_at DATE,
            verified_at DATE,
            checksum VARCHAR(64) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_documents_category CHECK (
                category IN ('feeding', 'sleep', 'weaning', 'development', 'safety', 'stool')
            )
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id VARCHAR(100) PRIMARY KEY,
            document_id VARCHAR(100) NOT NULL,
            content TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            age_min_months INTEGER,
            age_max_months INTEGER,
            topic TEXT,
            urgency_level VARCHAR(30),
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            embedding vector({dimensions}) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_document_chunks_document
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            CONSTRAINT uq_document_chunks_index UNIQUE (document_id, chunk_index),
            CONSTRAINT ck_document_chunks_age_min
                CHECK (age_min_months IS NULL OR age_min_months BETWEEN 0 AND 36),
            CONSTRAINT ck_document_chunks_age_max
                CHECK (age_max_months IS NULL OR age_max_months BETWEEN 0 AND 36),
            CONSTRAINT ck_document_chunks_age_range
                CHECK (
                    age_min_months IS NULL
                    OR age_max_months IS NULL
                    OR age_min_months <= age_max_months
                )
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_documents_category_active ON documents (category, is_active)",
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks (document_id)",
        """
        CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_cosine
            ON document_chunks USING hnsw (embedding vector_cosine_ops)
        """,
    )
    async with await psycopg.AsyncConnection.connect(settings.postgres_dsn) as conn:
        async with conn.cursor() as cursor:
            for statement in statements:
                await cursor.execute(statement)
        await conn.commit()


async def index_document(text_path: str, metadata_path: str) -> None:
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    document = load_document(text_path, metadata)
    await index_loaded_document(document)


async def index_catalog(pdf_root: str) -> None:
    """코드에 등록된 공식 문서 메타데이터로 PDF 묶음을 색인합니다."""
    root = Path(pdf_root)
    for metadata in RAG_DOCUMENTS:
        file_name = str(metadata["file"])
        document_path = root / file_name
        if not document_path.is_file():
            raise FileNotFoundError(f"색인 대상 PDF를 찾을 수 없습니다: {document_path}")
        clean_metadata = {key: value for key, value in metadata.items() if key != "file"}
        await index_loaded_document(load_document(document_path, clean_metadata))


async def index_loaded_document(document: dict[str, object]) -> None:
    """검증·본문 추출이 끝난 문서 한 건을 Chunk와 벡터로 저장합니다."""
    settings = get_settings()
    chunks = chunk_text(document.pop("content"))
    embedder = EmbeddingService(
        settings.ollama_base_url,
        settings.ollama_embedding_model,
        settings.ollama_timeout_seconds,
        settings.embedding_dimensions,
    )
    document_id = str(uuid4())
    vectors = [await embedder.embed(chunk) for chunk in chunks]

    async with await psycopg.AsyncConnection.connect(settings.postgres_dsn) as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id FROM documents WHERE checksum = %s AND category = %s LIMIT 1",
                (document["checksum"], document["category"]),
            )
            if await cursor.fetchone() is not None:
                print(f"이미 색인된 문서를 건너뜁니다: {document['title']}")
                return
            await cursor.execute(
                """
                INSERT INTO documents
                    (id, title, organization, source_url, category, published_at,
                     verified_at, checksum, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                """,
                (document_id, document["title"], document["organization"],
                 document["source_url"], document["category"], document.get("published_at"),
                 document.get("verified_at"), document["checksum"]),
            )
            for index, (content, vector) in enumerate(zip(chunks, vectors, strict=True)):
                vector_text = "[" + ",".join(str(value) for value in vector) + "]"
                await cursor.execute(
                    """
                    INSERT INTO document_chunks
                        (id, document_id, content, chunk_index, age_min_months,
                         age_max_months, topic, urgency_level, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    """,
                    (str(uuid4()), document_id, content, index, document.get("age_min_months"),
                     document.get("age_max_months"), document.get("topic"),
                     document.get("urgency_level"), json.dumps(document.get("metadata", {})),
                     vector_text),
                )
        await conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("document_path", nargs="?")
    parser.add_argument("metadata_path", nargs="?")
    parser.add_argument(
        "--catalog-pdf-root",
        help="RAG_DOCUMENTS에 등록된 공식 PDF가 있는 폴더를 지정해 일괄 색인합니다.",
    )
    parser.add_argument(
        "--initialize-schema",
        action="store_true",
        help="documents와 document_chunks RAG 스키마를 생성합니다.",
    )
    args = parser.parse_args()

    if args.initialize_schema:
        if args.document_path or args.metadata_path or args.catalog_pdf_root:
            parser.error("--initialize-schema는 다른 색인 인자와 함께 사용할 수 없습니다.")
        asyncio.run(initialize_schema())
        return

    if args.catalog_pdf_root:
        if args.document_path or args.metadata_path:
            parser.error("--catalog-pdf-root는 개별 문서 경로 인자와 함께 사용할 수 없습니다.")
        asyncio.run(index_catalog(args.catalog_pdf_root))
        return

    if not args.document_path or not args.metadata_path:
        parser.error("문서 경로와 메타데이터 경로를 모두 입력해야 합니다.")
    asyncio.run(index_document(args.document_path, args.metadata_path))


if __name__ == "__main__":
    main()
