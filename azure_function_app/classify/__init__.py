import os
import openai
import azure.functions as func
import json
import logging
import io
import csv
import time

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
OPENAI_DEPLOYMENT = os.getenv("OPENAI_DEPLOYMENT")

openai.api_type = "azure"
openai.api_key = OPENAI_API_KEY
openai.api_base = OPENAI_ENDPOINT
openai.api_version = "2023-05-15"

# Define categories for classification
CATEGORIES = [
    "NHSUK Spam/Marketing",
    "NHSUK Profiles",
    "NHSuk Unsupported Service",
    "NHSUK Content Management Service",
    "NHSUK Data Services - Directories",
    "NHSUK Ratings & Reviews",
    "NHSuk Generic Service",
    "NHSUK Data Services - GDoS",
    "NHSUK Personal Medical Query",
    "NHSUK Find A Service",
    "NHSUK Syndication",
    "NHSUK Health Assessment Tools",
    "NHSUK Internal Tech Request",
    "NHSUK Find Your NHS Number",
    "Z_Retired P0 & P5 Web Service",
    "NBS Q-Flow Acct Mgmt",
    "NSD Unsupported Service",
    "NBS Patient Journey",
    "NHSUK Give Us Feedback Form",
    "NHSUK Campaigns",
    "Patient Facing",
    "Profile manager (GP Reg)",
    "NHS App National Services",
    "GeneralPracticeAnnualSelfDeclaration-eDec",
    "NHSUK Authenticated Website",
    "Post event message to GP",
    "CSF – Junk NSD"
]

def classify_ticket(ticket):
    prompt = f"""
Classify the following service desk ticket into one of these categories:
{', '.join(CATEGORIES)}

Ticket Description:
{ticket}

Category:
"""
    response = openai.ChatCompletion.create(
        engine=OPENAI_DEPLOYMENT,
        messages=[{"role": "system", "content": "You are a helpful assistant that classifies service desk tickets."},
                  {"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0
    )
    return response.choices[0].message["content"].strip()

def process_csv(req: func.HttpRequest) -> func.HttpResponse:
    """Process a CSV file and classify the Description column."""
    try:
        logging.info("Start of process_csv function")
        # Get the CSV content from the request body
        csv_content = req.get_body().decode('utf-8')
        
        # Set up input and output streams
        input_stream = io.StringIO(csv_content)
        output_stream = io.StringIO()
        logging.info("Start of process_csv function", extra={"csv_content": csv_content})
        # Read and parse the CSV
        reader = csv.DictReader(input_stream)
        fieldnames = reader.fieldnames + ['Category']
        writer = csv.DictWriter(output_stream, fieldnames=fieldnames)
        writer.writeheader()
        
        # Get optional limit parameter
        limit = req.params.get('limit')
        limit = int(limit) if limit else None
        
        count = 0
        for row in reader:
            # Check if we've reached the limit
            if limit and count >= limit:
                break
                
            description = row.get('Description', '')
            if description:
                # Classify the ticket description
                category = classify_ticket(description)
                # Add a small delay to avoid rate limits
                time.sleep(0.5)
            else:
                category = "No Description"
                
            row['Category'] = category
            writer.writerow(row)
            count += 1
        
        # Return the processed CSV
        return func.HttpResponse(
            output_stream.getvalue(),
            mimetype="text/csv",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(
            f"Error processing CSV: {str(e)}",
            status_code=500
        )

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Check if the request is a CSV file based on content type
        content_type = req.headers.get('content-type', '')
        if content_type.startswith('text/csv') or content_type.startswith('application/csv'):
            return process_csv(req)
        logging.info("Return from process_csv function")    
        # Process JSON requests
        req_body = req.get_json()
        method = req_body.get("method")
        if method == "classify_single":
            ticket = req_body.get("ticket")
            result = classify_ticket(ticket)
            return func.HttpResponse(json.dumps({"classification": result}), mimetype="application/csv")
        elif method == "classify_tickets":
            tickets = req_body.get("tickets", [])
            results = [classify_ticket(t) for t in tickets]
            return func.HttpResponse(json.dumps({"classifications": results}), mimetype="application/csv")
        else:
            return func.HttpResponse("Invalid method.", status_code=400)
    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
