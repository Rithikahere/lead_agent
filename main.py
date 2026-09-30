from fastapi import FastAPI, HTTPException, status
from schemas import InboundEnquiry, LeadQualificationResponse
from agent import run_lead_workflow

app = FastAPI(
    title="AI Lead Qualification Agent API",
    description="LLM-driven lead parsing, scoring, and routing pipeline using Groq & FastMCP",
    version="1.0.0"
)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "lead-qualification-agent"}

@app.post(
    "/api/v1/qualify-lead",
    response_model=LeadQualificationResponse,
    status_code=status.HTTP_200_OK,
    tags=["Lead Qualification"]
)
async def qualify_lead(enquiry: InboundEnquiry):
    """
    Accepts an inbound customer message, extracts lead entities,
    computes qualification metrics, and returns the routing decision.
    """
    if not enquiry.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inbound message cannot be empty."
        )
    try:
        result = run_lead_workflow(enquiry)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)