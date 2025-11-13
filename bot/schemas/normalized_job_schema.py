from typing import List, Optional
from pydantic import BaseModel, Field


class NormalizedJobSchema(BaseModel):
    title: Optional[str] = None
    seniority: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    must_haves: List[str] = Field(default_factory=list)
    nice_to_haves: List[str] = Field(default_factory=list)
    experience_required_years: Optional[int] = None
    responsibilities: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    job_tags: List[str] = Field(default_factory=list)
