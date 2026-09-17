from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenceSpan(BaseModel):
    source: str = Field(default="resume")
    text: str = Field(default="")
    start: int | None = None
    end: int | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_string_span(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"source": "resume", "text": value}
        return value

class SkillEvidence(BaseModel):
    name: str
    proficiency: str | None = None
    recency: str | None = None
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class ExperienceFact(BaseModel):
    title: str = Field(default="")
    company: str | None = None
    description: str = Field(default="")
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class ResumeClaim(BaseModel):
    claim: str
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    transformation: str = Field(default="rephrased")


class ResumeAnalysisResult(BaseModel):
    skills: list[str] = Field(default_factory=list)
    summary: str = Field(default="")
    experience_highlights: list[str] = Field(default_factory=list)
    constraints: dict[
        str, str | bool | int | float | list[str] | None
    ] = Field(default_factory=dict)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    skill_evidence: list[SkillEvidence] = Field(default_factory=list)
    experience_facts: list[ExperienceFact] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    achievements: list[dict] = Field(default_factory=list)
    publications: list[dict] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        return [item.get("name", "") if isinstance(item, dict) else item for item in value]

    @field_validator("experience_highlights", mode="before")
    @classmethod
    def normalize_experience_highlights(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        normalized = []
        for item in value:
            if isinstance(item, dict):
                role = str(item.get("role") or item.get("title") or "").strip()
                description = str(item.get("description") or item.get("summary") or "").strip()
                normalized.append(": ".join(part for part in (role, description) if part))
            else:
                normalized.append(item)
        return normalized

    @field_validator("skill_evidence", mode="before")
    @classmethod
    def normalize_skill_evidence(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = [
                {"name": name, "evidence": evidence if isinstance(evidence, list) else []}
                for name, evidence in value.items()
            ]
        if not isinstance(value, list):
            return value
        return [
            {
                **item,
                "evidence": cls._normalize_evidence_spans(item.get("evidence", [])),
            }
            if isinstance(item, dict)
            else item
            for item in value
        ]

    @field_validator("evidence_spans", mode="before")
    @classmethod
    def normalize_evidence_spans(cls, value: Any) -> Any:
        return cls._normalize_evidence_spans(value)

    @staticmethod
    def _normalize_evidence_spans(value: Any) -> Any:
        if not isinstance(value, list):
            return value
        return [
            {"source": "resume", "text": item} if isinstance(item, str) else item
            for item in value
        ]


class ResumeRewriteResult(BaseModel):
    rewritten_text: str = Field(min_length=1)


class TailoredResumeResult(BaseModel):
    resume: dict = Field(default_factory=dict)
    # Optional: derived deterministically from ``resume`` sections after generation. The
    # model no longer emits a separate prose resume, which previously duplicated the
    # structured sections and overflowed the output budget on dense two-page resumes.
    rewritten_text: str = ""
    change_summary: list[dict] = Field(default_factory=list)
    evidence_used: list[dict] = Field(default_factory=list)
    target_requirements: list[dict] = Field(default_factory=list)
    validation_results: list[dict] = Field(default_factory=list)


class ResumePlanResult(BaseModel):
    section_order: list[str] = Field(default_factory=list)
    emphasized_skills: list[str] = Field(default_factory=list)
    selected_evidence: list[EvidenceSpan] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class OpportunityScoreVector(BaseModel):
    salary_advantage: float = 0.0
    attainability: float = 0.0
    demand: float = 0.0
    entry_barrier: float = 0.0
    career_option: float = 0.0
    preference_fit: float = 0.0
    data_confidence: float = 0.0
    fit: float = 0.0


class JobRequirementSummary(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    licenses: list[str] = Field(default_factory=list)
    occupation_family: str | None = None
    seniority: str | None = None
    salary_confidence: str = "C"
    freshness_score: float = 1.0
    trust_score: float = 0.75
    raw_requirements: dict = Field(default_factory=dict)
