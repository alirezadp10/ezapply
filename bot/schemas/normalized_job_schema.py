from typing import List

from pydantic import BaseModel, Field


class NormalizedJobSchema(BaseModel):
    job_title: str = ""
    job_seniority: str = ""
    job_technologies: List[str] = Field(default_factory=list)
    job_must_haves: List[str] = Field(default_factory=list)
    job_nice_to_haves: List[str] = Field(default_factory=list)
    job_experience_required_years: int = 0
    job_responsibilities: List[str] = Field(default_factory=list)
    job_soft_skills: List[str] = Field(default_factory=list)
    job_tags: List[str] = Field(default_factory=list)
