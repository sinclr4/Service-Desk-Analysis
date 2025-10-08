import os
import openai
import azure.functions as func
import json

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
OPENAI_DEPLOYMENT = os.getenv("OPENAI_DEPLOYMENT")

openai.api_type = "azure"
openai.api_key = OPENAI_API_KEY
openai.api_base = OPENAI_ENDPOINT
openai.api_version = "2023-05-15"

def classify_ticket(ticket):
    response = openai.ChatCompletion.create(
        engine=OPENAI_DEPLOYMENT,
        messages=[{"role": "system", "content": "Classify the following ticket."},
                  {"role": "user", "content": ticket}],
        max_tokens=10
    )
    return response.choices[0].message["content"]

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        method = req_body.get("method")
        if method == "classify_single":
            ticket = req_body.get("ticket")
            result = classify_ticket(ticket)
            return func.HttpResponse(json.dumps({"classification": result}), mimetype="application/json")
        elif method == "classify_tickets":
            tickets = req_body.get("tickets", [])
            results = [classify_ticket(t) for t in tickets]
            return func.HttpResponse(json.dumps({"classifications": results}), mimetype="application/json")
        else:
            return func.HttpResponse("Invalid method.", status_code=400)
    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
