from pydantic import BaseModel, Field
from typing import List

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ComplianceQuery(BaseModel):
    text: str = Field(..., min_length=10, description="La consulta del usuario sobre compliance.")
    user_id: str = Field("default_user", description="Identificador del usuario que realiza la consulta.")

class DocumentSource(BaseModel):
    source_document: str
    article_number: str
    content_chunk: str

class ComplianceReport(BaseModel):
    analysis: str
    sources: List[DocumentSource]
    token_usage: TokenUsage
    trace_id: str
