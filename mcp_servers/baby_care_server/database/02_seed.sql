-- Care Server 로컬 테스트에서만 사용하는 아기 ID입니다.
INSERT INTO babies (id)
VALUES ('baby-001')
ON CONFLICT (id) DO NOTHING;
