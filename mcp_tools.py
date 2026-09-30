from fastmcp import FastMCP
from schemas import ExtractedLeadData

mcp = FastMCP("LeadQualificationTools")

@mcp.tool()
def compute_lead_score(
    budget: float | None,
    urgency: str,
    team_size: int | None,
    has_business_email: bool
) -> dict:
    """Computes a deterministic base lead score from extracted metrics."""
    score = 20  # Base score for genuine inquiry
    reasons = []

    # Business domain evaluation
    if has_business_email:
        score += 20
        reasons.append("Verified enterprise/business email (+20)")
    
    # Budget sizing
    if budget is not None:
        if budget >= 25000:
            score += 30
            reasons.append("Enterprise budget >= $25k (+30)")
        elif budget >= 5000:
            score += 15
            reasons.append("Mid-market budget >= $5k (+15)")
        else:
            reasons.append("Low budget detected (+0)")

    # Team size
    if team_size is not None:
        if team_size >= 50:
            score += 20
            reasons.append("Enterprise team size 50+ (+20)")
        elif team_size >= 10:
            score += 10
            reasons.append("Mid-tier team size 10+ (+10)")

    # Urgency weighting
    urgency_upper = urgency.upper() if urgency else "LOW"
    if urgency_upper == "HIGH":
        score += 10
        reasons.append("High implementation urgency (+10)")
    elif urgency_upper == "MEDIUM":
        score += 5
        reasons.append("Moderate implementation urgency (+5)")

    final_score = min(score, 100)
    return {
        "calculated_score": final_score,
        "criteria_breakdown": reasons
    }

@mcp.tool()
def record_lead_to_crm(lead_data: dict, status: str, score: int) -> dict:
    """Mock CRM sync tool for routing qualified lead records."""
    return {
        "status": "RECORDED",
        "crm_lead_id": f"CRM-LEAD-{hash(str(lead_data)) % 100000:05d}",
        "qualification_status": status,
        "assigned_score": score
    }

if __name__ == "__main__":
    mcp.run()