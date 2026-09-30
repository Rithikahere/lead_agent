import os
import json
from dotenv import load_dotenv
from groq import Groq
from schemas import InboundEnquiry, ExtractedLeadData, LeadEvaluation, LeadQualificationResponse
from mcp_tools import compute_lead_score, record_lead_to_crm

load_dotenv()


GROQ_MODEL = "qwen/qwen3.8-27b"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

EXTRACTION_SYSTEM_PROMPT = """You are an expert enterprise sales development representative.
Analyze the customer's raw inbound enquiry and return ONLY a valid JSON object matching this schema:
{
  "contact_name": string or null,
  "email": string or null,
  "company": string or null,
  "use_case": string,
  "budget_detected": float or null,
  "urgency": "Low" | "Medium" | "High",
  "team_size": integer or null
}
Never output markdown fences (no ```json). Output strictly the raw JSON object."""

def extract_lead_info(enquiry: InboundEnquiry) -> ExtractedLeadData:
    content = f"Sender Name: {enquiry.sender_name}\nSender Email: {enquiry.sender_email}\nCompany: {enquiry.company_name}\nMessage:\n{enquiry.message}"
    
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ],
        temperature=0.0
    )
    
    raw_content = response.choices[0].message.content.strip()
    if raw_content.startswith("```"):
        raw_content = raw_content.split("```")[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]
        raw_content = raw_content.strip()
        
    parsed = json.loads(raw_content)

    if enquiry.sender_email and not parsed.get("email"):
        parsed["email"] = enquiry.sender_email
    if enquiry.sender_name and not parsed.get("contact_name"):
        parsed["contact_name"] = enquiry.sender_name
    if enquiry.company_name and not parsed.get("company"):
        parsed["company"] = enquiry.company_name

    return ExtractedLeadData(**parsed)

def evaluate_and_route(extracted: ExtractedLeadData, raw_message: str) -> LeadQualificationResponse:
    free_providers = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]
    email = (extracted.email or "").lower()
    has_biz_email = bool(email and "@" in email and not any(email.endswith("@" + dom) for dom in free_providers))
    
    scoring_result = compute_lead_score(
        budget=extracted.budget_detected,
        urgency=extracted.urgency,
        team_size=extracted.team_size,
        has_business_email=has_biz_email
    )
    score = scoring_result["calculated_score"]
    matched = scoring_result["criteria_breakdown"]
    missing = []
    
    if not has_biz_email:
        missing.append("Missing verified business email")
    if extracted.budget_detected is None:
        missing.append("Unspecified budget")
    if extracted.team_size is None:
        missing.append("Unspecified team/seat size")

    is_enterprise_tier = (extracted.budget_detected and extracted.budget_detected >= 50000) or (extracted.team_size and extracted.team_size >= 100)
    has_urgency_escalation = extracted.urgency == "High" and score >= 60

    if is_enterprise_tier:
        status = "ESCALATE"
        escalation_reason = "High-value enterprise opportunity detected requiring immediate Account Executive assignment."
        action = "Forward priority lead alert directly to Enterprise Sales Leadership."
        destination = "SLACK_ENTERPRISE_ESCALATION"
    elif has_urgency_escalation:
        status = "ESCALATE"
        escalation_reason = "High-urgency qualified lead demands same-day human follow-up."
        action = "Assign to active SDR queue with 1-hour SLA."
        destination = "SLACK_SDR_URGENT"
    elif score >= 50:
        status = "QUALIFIED"
        escalation_reason = None
        action = "Enroll in automated high-intent booking flow and log to CRM."
        destination = "CRM_QUALIFIED_INBOUND"
    else:
        status = "DISQUALIFIED"
        escalation_reason = None
        action = "Route to automated product-led nurture email sequence."
        destination = "MARKETING_NURTURE_LIST"

    record_lead_to_crm(extracted.model_dump(), status, score)

    evaluation = LeadEvaluation(
        lead_score=score,
        qualification_status=status,
        matched_criteria=matched,
        missing_criteria=missing,
        escalation_reason=escalation_reason,
        recommended_action=action
    )

    return LeadQualificationResponse(
        inbound_message=raw_message,
        extracted_data=extracted,
        evaluation=evaluation,
        routed_destination=destination
    )

def run_lead_workflow(enquiry: InboundEnquiry) -> LeadQualificationResponse:
    extracted = extract_lead_info(enquiry)
    return evaluate_and_route(extracted, enquiry.message)