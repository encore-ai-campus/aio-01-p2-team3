from pathlib import Path

from openai import AsyncOpenAI


class AnswerGenerationError(RuntimeError):
    pass


class AnswerService:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = model
        self.prompt = (Path(__file__).parents[1] / "prompts" / "rag_answer_prompt.txt").read_text(encoding="utf-8")

    async def generate(self, query: str, context: str, safety_notice: str | None) -> str:
        if self.client is None:
            raise AnswerGenerationError("OpenAI API 설정이 필요합니다.")
        try:
            response = await self.client.responses.create(
                model=self.model,
                instructions=self.prompt,
                input=f"질문:\n{query}\n\n검색 근거:\n{context}\n\n안전 안내:\n{safety_notice or '없음'}",
            )
            answer = response.output_text.strip()
            if not answer:
                raise ValueError("빈 답변")
            return answer
        except Exception as exc:
            raise AnswerGenerationError("답변을 생성할 수 없습니다.") from exc

