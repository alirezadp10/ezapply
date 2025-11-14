from typing import List

from pydantic import BaseModel, Field


class NormalizerOutputSchema(BaseModel):
    # JOB
    job_title: str = ""
    job_seniority: str = ""
    job_technologies: List[str] = Field(default_factory=list)
    job_must_haves: List[str] = Field(default_factory=list)
    job_nice_to_haves: List[str] = Field(default_factory=list)
    job_experience_required_years: int = 0
    job_responsibilities: List[str] = Field(default_factory=list)
    job_soft_skills: List[str] = Field(default_factory=list)
    job_tags: List[str] = Field(default_factory=list)

    # CANDIDATE
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
