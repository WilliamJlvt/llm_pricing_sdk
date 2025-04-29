import requests
import re

def fetch_ts_file(url):
    response = requests.get(url)

    if response.status_code == 200:
        return response.text  # Retourner le contenu du fichier sous forme de texte
    else:
        raise Exception(
            f"Cannot fetch the file, status code: {response.status_code}")

# Helper function to parse context window string
def parse_context_window(context_str):
    if not context_str:
        return None

    context_str = context_str.strip().upper()

    # Handle formats like '128K/16K' or '8K/2K' - prioritize the first value
    if '/' in context_str:
        context_str = context_str.split('/')[0].strip()

    # Use regex to extract number and potential suffix (K or M)
    # Allows for potential decimal points before K/M, like '1.5M'
    match = re.match(r'^(\d+(?:\.\d+)?)([KM]?)$', context_str)
    if not match:
        # Attempt to parse simple integers if the K/M regex fails
        try:
            return int(context_str)
        except ValueError:
            print(f"Warning: Could not parse context window '{context_str}'")
            return None

    value_str, suffix = match.groups()
    value = float(value_str)

    if suffix == 'K':
        value *= 1000
    elif suffix == 'M':
        value *= 1000000

    return int(value)