import stripe
import json
import requests
from datetime import datetime
import time
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Stripe API Key
stripe.api_key = os.getenv("STRIPE_API_KEY")

# Fiken API Token and Company Slug
fiken_api_token = os.getenv("FIKEN_API_TOKEN")
company_slug = os.getenv("COMPANY_SLUG")

# Track total amount of purchases to determine VAT registration
total_purchases = 0
vat_registration_threshold = 0  # Minor currency unit (cents)

# Define the transaction types in minor currency units (cents)
transaction_types = {
    39400: (3000, 'HIGH'),
    41400: (3100, 'EXEMPT'),
    43400: (3100, 'EXEMPT'),
    23800: (3000, 'HIGH'),
    25800: (3100, 'EXEMPT'),
    27800: (3100, 'EXEMPT'),
    43700: (3000, 'HIGH'),
    45700: (3100, 'EXEMPT'),
    48700: (3100, 'EXEMPT'),
    63600: (3000, 'HIGH'),
}

def fetch_charges_from_date(start_date):
    start_date_timestamp = int(start_date.timestamp())
    now_timestamp = int(datetime.now().timestamp())

    charges = stripe.Charge.list(
        created={
            'gte': start_date_timestamp,
            'lte': now_timestamp,
        },
        limit=1000  # Adjust the limit as necessary
    )

    charges_list = list(charges.auto_paging_iter())
    charges_list.sort(key=lambda x: x['created'])

    return charges_list

def fetch_customer_details_from_charge(charge):
    try:
        expanded_charge = stripe.Charge.retrieve(
            charge['id'],
            expand=['customer'],
        )
    except Exception as e:
        print(f"Error retrieving charge {charge['id']}: {e}")
        return None

    customer = expanded_charge.get('customer')
    customer_name = expanded_charge['billing_details']['name'] if expanded_charge['billing_details'] else None
    customer_email = expanded_charge['billing_details']['email'] if expanded_charge['billing_details'] else None
    
    if not customer_name and customer:
        customer_name = customer.get('name')
    if not customer_email and customer:
        customer_email = customer.get('email')

    if not customer_name or not customer_email:
        print(f"Missing customer name or email for charge {charge['id']}")
        return None

    customer_details = {
        'customer_name': customer_name,
        'customer_email': customer_email,
        'amount': expanded_charge['amount'],
        'currency': expanded_charge['currency'].upper(),
        'date': datetime.fromtimestamp(expanded_charge['created']).strftime('%Y-%m-%d'),
        'description': expanded_charge['description']
    }
    return customer_details

def determine_vat_type_and_account(amount, total_purchases):
    if total_purchases + amount <= vat_registration_threshold:
        vat_type = 'OUTSIDE'
        account_type = None
    else:
        if amount in transaction_types:
            account_type, vat_type = transaction_types[amount]
        else:
            vat_type = 'HIGH'
            account_type = 3200
    return vat_type, account_type

def calculate_vat(gross_price, vat_rate):
    net_price = int(gross_price / (1 + vat_rate))
    vat_amount = gross_price - net_price
    return net_price, vat_amount

def format_sale_for_fiken(sale, customer_id, total_purchases, vat_registration_threshold):
    vat_type, account_type = determine_vat_type_and_account(sale['amount'], total_purchases)

    if vat_type == 'HIGH' and account_type == 3000:
        net_price, vat_amount = calculate_vat(sale['amount'], 0.25)
        line_item = {
            'description': sale['description'],
            'netPrice': net_price,
            'vatType': vat_type,
            'vat': vat_amount,
            'account': account_type
        }
    else:
        line_item = {
            'description': sale['description'],
            'netPrice': sale['amount'],
            'vatType': vat_type,
            'vat': None,
            'account': account_type
        }

    total_paid = sale['amount']  # The gross price including VAT if applicable

    fiken_sale = {
        'saleNumber': f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'date': sale['date'],
        'kind': 'external_invoice',
        'totalPaid': total_paid,  # The total amount paid
        'lines': [line_item],
        'currency': sale['currency'],
        'customerId': customer_id,
        'paymentAccount': "1960:10001",
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

    for attempt in range(3):
        response = requests.post(url, headers=headers, json=sale)
        
        if response.status_code == 201:
            print(f"Successfully posted sale: {sale}")
            return True
        else:
            print(f"Failed to post sale: {sale}, Status Code: {response.status_code}, Response: {response.text}")
            time.sleep(3)
    
    print(f"Failed to post sale after 3 attempts: {sale}")
    return False

def create_customer_in_fiken(name, email):
    url = f"https://api.fiken.no/api/v2/companies/{company_slug}/contacts"
    headers = {
        "Authorization": f"Bearer {fiken_api_token}",
        "Content-Type": "application/json"
    }
    customer_data = {
        "name": name,
        "email": email,
        "customer": True
    }
    response = requests.post(url, headers=headers, json=customer_data)
    
    if response.status_code == 201:
        print(f"Customer created in Fiken: {name}")
        return response.headers['Location'].split('/')[-1]
    else:
        print(f"Failed to create customer: {response.status_code}, Response: {response.text}")
        return None

def find_customer_in_fiken(email):
    url = f"https://api.fiken.no/api/v2/companies/{company_slug}/contacts"
    headers = {
        "Authorization": f"Bearer {fiken_api_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        contacts = response.json()
        for contact in contacts:
            if contact.get('email') == email:
                return contact.get('id')
    return None

def save_to_json(data, filename='latest_charge_data.json'):
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)
    print(f"Data saved to {filename}")

def save_progress(processed_ids, filename='processed_ids.json'):
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(processed_ids, json_file, indent=4, ensure_ascii=False)
    print(f"Processed IDs saved to {filename}")

def load_progress(filename='processed_ids.json'):
    try:
        with open(filename, 'r', encoding='utf-8') as json_file:
            processed_ids = json.load(json_file)
        return processed_ids
    except FileNotFoundError:
        return []

def main(test_mode=True):
    global total_purchases
    start_date = datetime.strptime("2024-06-20", "%Y-%m-%d")
    charges = fetch_charges_from_date(start_date)
    processed_ids = load_progress()

    for charge in charges:
        if charge['id'] in processed_ids:
            continue

        customer_details = fetch_customer_details_from_charge(charge)
        if not customer_details:
            continue

        customer_name = customer_details['customer_name']
        customer_email = customer_details['customer_email']

        customer_id = find_customer_in_fiken(customer_email)
        if not customer_id:
            customer_id = create_customer_in_fiken(customer_name, customer_email)
            if not customer_id:
                continue

        fiken_sale = format_sale_for_fiken(customer_details, customer_id, total_purchases, vat_registration_threshold)

        if test_mode:
            print_formatted_data_for_fiken(fiken_sale)
            success = True
        else:
            print("Posting sale to Fiken...")
            success = post_sale_to_fiken(fiken_sale, fiken_api_token, company_slug)

        if success:
            save_to_json(customer_details, filename=f"{charge['id']}_data.json")
            processed_ids.append(charge['id'])
            save_progress(processed_ids)

            total_purchases += customer_details['amount']

if __name__ == "__main__":
    main(test_mode=False)

