# Stripe to Fiken Integration
This project provides a script to fetch transaction data from Stripe and format it for integration with Fiken, a popular accounting software in Norway. It aims to simplify the accounting process for businesses, both those registered and not registered in the MVA registry.

## Features
Fetch charges from Stripe within a specified date range.
Retrieve customer details associated with each charge.
Format transactions for Fiken, including VAT calculations where applicable.
Post formatted transactions to Fiken.
Save progress and data locally to avoid processing duplicate transactions.
## Prerequisites
Python 3.6+
Stripe account and API key
Fiken account and API token
Install required Python packages:
pip install stripe requests python-dotenv
## Installation
Clone this repository:
git clone https://github.com/yourusername/stripe-to-fiken.git
cd stripe-to-fiken

Create a .env file in the root directory and add your API keys:
STRIPE_API_KEY=your_stripe_api_key
FIKEN_API_TOKEN=your_fiken_api_token
COMPANY_SLUG=your_company_slug

Run the script:
python main.py # For businesses not registered in the MVA registry
python main_mva.py # For businesses registered in the MVA registry

## Configuration
The script can be customized to fit your specific accounting needs. The main configuration points are:

Transaction Types: Define your transaction types and VAT rates in minor currency units (cents). Adjust the transaction_types dictionary in the script as needed.
VAT Registration Threshold: Set the vat_registration_threshold variable to determine when VAT registration is required.
## Usage
### For Businesses Not Registered in the MVA Registry
Run the main.py script. This script fetches charges from Stripe, retrieves customer details, formats the transactions for Fiken, and posts them to Fiken.

### For Businesses Registered in the MVA Registry
Run the main_mva.py script. This script includes additional VAT calculations and adjustments needed for businesses registered in the MVA registry.

## Notes
Fiken Accounts: The way of determining Fiken accounts in this script is not universal. You may need to refer to the Fiken API documentation to find more information and adjust the script accordingly.
No UI: This script does not include a user interface. It is intended to be run from the command line or integrated into other systems as needed.
## Example Workflow
Fetch charges from Stripe starting from a specified date.
Retrieve and expand customer details for each charge.
Determine the VAT type and account based on the transaction amount and total purchases.
Format the transaction for Fiken, including VAT calculations where applicable.
Post the formatted transaction to Fiken.
Save progress and data locally to avoid duplicate processing in subsequent runs.
Contributing
Feel free to fork this repository and make your own improvements. Pull requests are welcome!

## License
This project is licensed under the MIT License.

## Disclaimer
This script was developed to solve a specific accounting problem. It is provided as-is and may not cover all possible use cases. Users are advised to review and modify the script as needed to fit their specific requirements.
