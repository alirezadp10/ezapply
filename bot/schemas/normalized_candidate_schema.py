from typing import List, Optional

from pydantic import BaseModel, Field


class NormalizedCandidateSchema(BaseModel):
    name: Optional[str] = None
    experience_years: Optional[int] = None
    primary_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    infra: List[str] = Field(default_factory=list)
    message_queues: List[str] = Field(default_factory=list)
    frontend: List[str] = Field(default_factory=list)
    other_tools: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    english_level: Optional[str] = None
    seniority: Optional[str] = None
