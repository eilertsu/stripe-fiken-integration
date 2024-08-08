import stripe
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Stripe API Key
stripe.api_key = os.getenv("STRIPE_API_KEY")

# Fiken API Token and Company Slug
fiken_api_token = os.getenv("FIKEN_API_TOKEN")
company_slug = os.getenv("COMPANY_SLUG")

def fetch_latest_charge():
    charges = stripe.Charge.list(limit=1)
    if charges['data']:
        charge = charges['data'][0]
        expanded_charge = stripe.Charge.retrieve(
            charge['id'],
            expand=['customer']
        )
        customer = expanded_charge.get('customer')
        customer_name = expanded_charge['billing_details']['name'] if expanded_charge['billing_details'] else None
        customer_email = expanded_charge['billing_details']['email'] if expanded_charge['billing_details'] else None

        # Fallback to customer object if billing details are missing
        if not customer_name and customer:
            customer_name = customer.get('name')
        if not customer_email and customer:
            customer_email = customer.get('email')

        charge_data = {
            'amount': expanded_charge['amount'] / 100,  # Convert amount to major currency unit
            'currency': expanded_charge['currency'].upper(),
            'date': datetime.fromtimestamp(expanded_charge['created']).strftime('%Y-%m-%d'),  # Convert timestamp to human-readable format
            'customer_name': customer_name,
            'customer_email': customer_email,
            'description': expanded_charge['description']
        }
        return charge_data
    return None

def create_customer_in_fiken(name, email):
    url = f"https://api.fiken.no/api/v2/companies/{company_slug}/contacts"
    headers = {
        "Authorization": f"Bearer {fiken_api_token}",
        "Content-Type": "application/json"
    }
    customer_data = {
        "name": name,
        "email": email,
        "address": None,
        "customer": True  # Mark this contact as a customer
    }
    response = requests.post(url, headers=headers, json=customer_data)
    
    print(f"Request URL: {url}")
    print(f"Request Headers: {json.dumps(headers, indent=4)}")
    print(f"Request Body: {json.dumps(customer_data, indent=4)}")
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")

    if response.status_code == 201:
        return response.headers['Location'].split('/')[-1]  # Extract customer ID from the Location header
    else:
        print(f"Failed to create customer: {response.status_code}, Response: {response.text}")
        return None

def format_sale_for_fiken(sale, customer_id):
    fiken_sale = {
        'saleNumber': f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'date': sale['date'],
        'kind': 'external_invoice',
        'totalPaid': sale['amount'],
        'lines': [
            {
                'description': sale['description'],
                'netPrice': sale['amount'],
                'account': 3200,
                'vatType': 'SALG_FRITATT_FOR_MVA_UTENFOR_AVGIFTSOMRmentAccount': "1960:10001",
        'paymentDate': sale['date']
    }
    return fiken_sale

def print_formatted_data_for_fiken(sale):
    print("Formatted data for Fiken:")
    print(json.dumps(sale, indent=4))

def post_sale_to_fiken(sale, api_token, company_slug):
    url = f"https://api.fiken.no/api/v2/companies/{company_slug}/sales"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=sale)
    
    print(f"Request URL: {url}")
    print(f"Request Headers: {json.dumps(headers, indent=4)}")
    print(f"Request Body: {json.dumps(sale, indent=4)}")
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    
    if response.status_code == 201:
        print(f"Successfully posted sale: {sale}")
    else:
        print(f"Failed to post sale: {sale}, Status Code: {response.status_code}, Response: {response.text}")

def save_to_json(data, filename='latest_charge_data.json'):
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)
    print(f"Data saved to {filename}")

def main(test_mode=True):
    latest_charge = fetch_latest_charge()

    if latest_charge:
        customer_name = latest_charge['customer_name']
        customer_email = latest_charge['customer_email']

        if customer_name and customer_email:
            customer_id = create_customer_in_fiken(customer_name, customer_email)

            if customer_id:
                fiken_sale = format_sale_for_fiken(latest_charge, customer_id)

                if test_mode:
                    print_formatted_data_for_fiken(fiken_sale)
                else:
                    print("Posting sale to Fiken...")
                    post_sale_to_fiken(fiken_sale, fiken_api_token, company_slug)

                save_to_json(latest_charge)
            else:
                print("Failed to create customer in Fiken.")
        else:
            print("Customer name or email is missing.")
    else:
        print("No charges found.")

if __name__ == "__main__":
    main(test_mode=False)

