from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from datetime import datetime
from typing import Dict, List
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]}})

def load_json_data(filename: str) -> Dict:
    file_path = f'data/{filename}'
    print(f"Attempting to load file: {file_path}")
    print(f"File exists: {os.path.exists(file_path)}")
    
    try:
        with open(file_path) as f:
            data = json.load(f)
            if isinstance(data, dict):
                print(f"Loaded data is a dictionary with keys: {data.keys()}")
                data = [data]
            print(f"Successfully loaded {len(data)} records from {filename}")
            if data:
                print(f"Sample record from {filename}:", json.dumps(data[0], indent=2)[:200] + "...")
            return data
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {e}")
        return []

def format_date(timestamp):
    if not timestamp:
        return ""
    # Handle both timestamp formats (milliseconds since epoch and date string)
    try:
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp/1000.0).strftime('%Y-%m-%d')
        return datetime.strptime(timestamp.split()[0], '%m/%d/%Y').strftime('%Y-%m-%d')
    except:
        return timestamp

def merge_user_data():
    print("\nStarting merge_user_data function")
    revenuecat_data = load_json_data('revenuecat.json')
    onesignal_data = load_json_data('onesignal.json')
    
    print(f"\nLoaded {len(revenuecat_data)} RevenueCat records")
    print(f"Loaded {len(onesignal_data)} OneSignal records")
    
    # Create lookup for OneSignal data by external_id
    onesignal_lookup = {
        user.get('external_id'): user
        for user in onesignal_data
        if user.get('external_id')
    }
    print(f"Created lookup with {len(onesignal_lookup)} OneSignal external_ids")
    
    merged_data = {}
    
    # Process RevenueCat data
    for user in revenuecat_data:
        app_user_id = user.get('app_user_id')
        
        # Print some sample data to debug
        if len(merged_data) < 2:
            print(f"\nSample RevenueCat user:")
            print(f"app_user_id: {app_user_id}")
            print(f"status: {user.get('status')}")
        
        if app_user_id:
            subscription_status = user.get('status', '').lower()
            if subscription_status == 'free_trial':
                subscription_status = 'trial'
            elif subscription_status in ['active', 'trial', 'expired']:
                subscription_status = subscription_status
            else:
                subscription_status = 'unknown'
            
            merged_data[app_user_id] = {
                'user_id': app_user_id,
                'email': user.get('email', ''),
                'subscription': subscription_status,
                'trial_start': format_date(user.get('trial_start_at_DT')),
                'last_seen': format_date(user.get('last_seen_at_DT')),
                'tags': {},
                'platform': user.get('last_seen_platform', ''),
                'country': user.get('last_seen_ip_country', ''),
                'latest_product': user.get('latest_product', ''),
                'total_spent': user.get('total_spent', 0)
            }
    
    print(f"\nProcessed {len(merged_data)} RevenueCat users")
    
    # Debug OneSignal data
    print("\nSample OneSignal lookup keys:", list(onesignal_lookup.keys())[:2])
    
    # Merge OneSignal data
    onesignal_merged = 0
    onesignal_only = 0
    for external_id, onesignal_user in onesignal_lookup.items():
        if external_id in merged_data:
            merged_data[external_id]['tags'] = onesignal_user.get('tags', {})
            merged_data[external_id]['email'] = onesignal_user.get('email', merged_data[external_id]['email'])
            onesignal_last_seen = format_date(onesignal_user.get('last_active'))
            if onesignal_last_seen > merged_data[external_id]['last_seen']:
                merged_data[external_id]['last_seen'] = onesignal_last_seen
            onesignal_merged += 1
        else:
            merged_data[external_id] = {
                'user_id': external_id,
                'email': onesignal_user.get('email', ''),
                'subscription': 'unknown',
                'trial_start': '',
                'last_seen': format_date(onesignal_user.get('last_active')),
                'tags': onesignal_user.get('tags', {}),
                'platform': '',
                'country': '',
                'latest_product': '',
                'total_spent': 0
            }
            onesignal_only += 1
    
    result = list(merged_data.values())
    
    # Debug sample of final results
    if result:
        print("\nSample of final merged data:")
        print(json.dumps(result[0], indent=2))
    
    print(f"\nMerge summary:")
    print(f"- OneSignal users merged with RevenueCat: {onesignal_merged}")
    print(f"- Users only in OneSignal: {onesignal_only}")
    print(f"- Total unique users: {len(result)}")
    return result

@app.route('/api/users', methods=['GET'])
def get_users():
    print("\nReceived request for /api/users")
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    subscription_status = request.args.get('subscription_status')
    tag_filter = request.args.get('tag_filter')
    
    print(f"Filter parameters: start_date={start_date}, end_date={end_date}, "
          f"subscription_status={subscription_status}, tag_filter={tag_filter}")
    
    users = merge_user_data()
    filtered_users = users
    
    # Debug before filtering
    print(f"\nBefore filtering: {len(filtered_users)} users")
    
    # Apply filters
    if start_date and end_date:
        filtered_users = [
            user for user in filtered_users
            if user.get('last_seen') and start_date <= user.get('last_seen').split()[0] <= end_date
        ]
        print(f"After date filter: {len(filtered_users)} users")
    
    if subscription_status:
        filtered_users = [
            user for user in filtered_users
            if user.get('subscription', '').lower() == subscription_status.lower()
        ]
        print(f"After subscription filter: {len(filtered_users)} users")
    
    if tag_filter:
        try:
            tag_key, tag_value = tag_filter.split(':')
            filtered_users = [
                user for user in filtered_users
                if any(
                    tag_key.lower() in k.lower() and str(v).lower() == tag_value.lower()
                    for k, v in user.get('tags', {}).items()
                )
            ]
            # Debug tag filtering
            if not filtered_users:
                print("\nTag filtering debug:")
                print(f"Looking for tag key containing '{tag_key}' with value '{tag_value}'")
                sample_users = users[:5]
                for user in sample_users:
                    print(f"User {user['email']} tags:", user.get('tags', {}))
        except ValueError:
            print(f"Invalid tag filter format: {tag_filter}")
    
    print(f"\nReturning {len(filtered_users)} users after all filters")
    return jsonify(filtered_users)

@app.route('/test', methods=['GET'])
def test():
    print("Test endpoint was called!")
    response = {"message": "Server is working!"}
    print(f"Sending response: {response}")
    return jsonify(response)

@app.route('/', methods=['GET'])
def home():
    return "Hello, World!"

if __name__ == '__main__':
    app.run(debug=True, port=5001) 