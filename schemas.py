from typing import Optional, List
from pydantic import BaseModel, Field

class InboundEnquiry(BaseModel):
    sender_name: Optional[str] = Field(default=None, description="Sender name if available")
    sender_email: Optional[str] = Field(default=None, description="Sender email address")
    company_name: Optional[str] = Field(default=None, description="Company name if mentioned")
    message: str = Field(..., description="Raw inbound message from customer")

class ExtractedLeadData(BaseModel):
    contact_name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    use_case: str = Field(description="Summary of customer requirements")
    budget_detected: Optional[float] = Field(default=None, description="Estimated budget in USD if stated")
    urgency: str = Field(description="Low, Medium, or High")
    team_size: Optional[int] = Field(default=None, description="Team or company seat size")

class LeadEvaluation(BaseModel):
    lead_score: int = Field(..., ge=0, le=100, description="Qualification score between 0 and 100")
    qualification_status: str = Field(..., description="QUALIFIED, DISQUALIFIED, or ESCALATE")
    matched_criteria: List[str]
    missing_criteria: List[str]
    escalation_reason: Optional[str] = None
    recommended_action: str

class LeadQualificationResponse(BaseModel):
    inbound_message: str
    extracted_data: ExtractedLeadData
    evaluation: LeadEvaluation
    routed_destination: str