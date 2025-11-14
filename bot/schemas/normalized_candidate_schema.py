from typing import List

from pydantic import BaseModel, Field


class NormalizedCandidateSchema(BaseModel):
    candidate_name: str = ""
    candidate_experience_years: int = 0
    candidate_primary_languages: List[str] = Field(default_factory=list)
    candidate_frameworks: List[str] = Field(default_factory=list)
    candidate_databases: List[str] = Field(default_factory=list)
    candidate_infra: List[str] = Field(default_factory=list)
    candidate_message_queues: List[str] = Field(default_factory=list)
    candidate_frontend: List[str] = Field(default_factory=list)
    candidate_other_tools: List[str] = Field(default_factory=list)
    candidate_certifications: List[str] = Field(default_factory=list)
    candidate_english_level: str = ""
    candidate_seniority: str = ""