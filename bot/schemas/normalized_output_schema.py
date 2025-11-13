from typing import List, Optional
from pydantic import BaseModel


class NormalizerOutputSchema(BaseModel):
    job_title: Optional[str] = None
    job_seniority: Optional[str] = None
    job_technologies: List[str] = []
    job_must_haves: List[str] = []
    job_nice_to_haves: List[str] = []
    job_experience_required_years: Optional[int] = None
    job_responsibilities: List[str] = []
    job_soft_skills: List[str] = []
    job_tags: List[str] = []

    candidate_name: Optional[str] = None
    candidate_experience_years: Optional[int] = None
    candidate_primary_languages: List[str] = []
    candidate_frameworks: List[str] = []
    candidate_databases: List[str] = []
    candidate_infra: List[str] = []
    candidate_message_queues: List[str] = []
    candidate_frontend: List[str] = []
    candidate_other_tools: List[str] = []
    candidate_certifications: List[str] = []
    candidate_english_level: Optional[str] = None
    candidate_seniority: Optional[str] = None
