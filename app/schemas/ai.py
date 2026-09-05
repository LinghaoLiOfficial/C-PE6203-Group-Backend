from pydantic import BaseModel, Field


class ResumeAnalysisResult(BaseModel):
    skills: list[str] = Field(default_factory=list)
    summary: str = Field(default="")
    experience_highlights: list[str] = Field(default_factory=list)


class ResumeRewriteResult(BaseModel):
    rewritten_text: str = Field(min_length=1)
