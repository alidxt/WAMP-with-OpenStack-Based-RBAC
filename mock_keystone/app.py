# Save this file as secure_wamp_project/mock_keystone/app.py

from flask import Flask, request, jsonify
import jwt
import datetime
import time

app = Flask(__name__)

# Secret key for JWT signing (should be strong and loaded from config in production)
SECRET_KEY = "your_super_secret_key_for_jwt"

# In a real scenario, this would come from a database
users = {
    "hmi_dashboard": {"password": "hmidashpass", "role": "hmi_viewer"},
    "sensor_device_1": {"password": "sensordevicepass", "role": "sensor_publisher"},
    "crossbar_authenticator_client": {"password": "some_secret_ticket_for_authenticator", "role": "authenticator"}
}

# Define RBAC policies (what roles can do what actions)
# This is a simplified representation. In a real system, this would be more granular.
rbac_policies = {
    "hmi_viewer": {
        "com.iiot.topic.sensor_data.subscribe": True,
        "com.example.get_hmi_status.call": True
    },
    "sensor_publisher": {
        "com.iiot.topic.sensor_data.publish": True
    },
    "authenticator": {
        # The authenticator role itself doesn't need WAMP action permissions here,
        # as its role is to authenticate other users. Its WAMP permissions are
        # defined in Crossbar's config.json for registering the auth procedure.
    },
    "admin": {
        "*": True # Admin can do anything
    }
}

@app.route('/authenticate', methods=['POST'])
def authenticate_old():
    """
    Old authentication endpoint, kept for compatibility if needed.
    New clients should use /auth/tokens.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user_info = users.get(username)
    if user_info and user_info["password"] == password:
        print(f"Keystone: Old /authenticate successful for user '{username}'.")
        return jsonify({"authenticated": True, "role": user_info["role"]}), 200
    else:
        print(f"Keystone: Old /authenticate failed for user '{username}'. Invalid credentials.")
        return jsonify({"authenticated": False, "message": "Invalid credentials"}), 401

@app.route('/verify_token', methods=['POST'])
def verify_token_old():
    """
    Old token verification endpoint, kept for compatibility if needed.
    New clients should use /auth/verify.
    """
    data = request.get_json()
    token = data.get('token')

    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if decoded_token['exp'] < time.time():
            return jsonify({"valid": False, "message": "Token expired"}), 401
        print(f"Keystone: Old /verify_token successful for token.")
        return jsonify({"valid": True, "user": decoded_token['username'], "role": decoded_token['role']}), 200
    except jwt.ExpiredSignatureError:
        print("Keystone: Old /verify_token failed: Token expired.")
        return jsonify({"valid": False, "message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        print("Keystone: Old /verify_token failed: Invalid token.")
        return jsonify({"valid": False, "message": "Invalid token"}), 401
    except Exception as e:
        print(f"Keystone: Old /verify_token failed with unexpected error: {e}")
        return jsonify({"valid": False, "message": str(e)}), 500

# --- NEW KEYSTONE ENDPOINTS FOR JWT-BASED AUTHENTICATION FLOW ---

@app.route('/auth/tokens', methods=['POST'])
def authenticate_and_get_token():
    """
    Authenticates a user and issues a JWT token.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user_info = users.get(username)
    if not user_info or user_info["password"] != password:
        print(f"Keystone: /auth/tokens failed for user '{username}'. Invalid credentials.")
        return jsonify({"message": "Invalid credentials"}), 401

    # Generate JWT token
    # Token valid for 1 hour
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    payload = {
        "username": username,
        "role": user_info["role"],
        "exp": expiration_time.timestamp(),
        "iat": datetime.datetime.utcnow().timestamp()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    
    print(f"Keystone: /auth/tokens successful for user '{username}'. Token issued.")
    return jsonify({"token": token, "expires_at": expiration_time.isoformat()}), 200

@app.route('/auth/verify', methods=['POST'])
def verify_token():
    """
    Verifies a JWT token.
    """
    data = request.get_json()
    token = data.get('token')

    if not token:
        return jsonify({"message": "Token missing"}), 400

    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if decoded_token['exp'] < time.time():
            print("Keystone: /auth/verify failed: Token expired.")
            return jsonify({"valid": False, "message": "Token expired"}), 401
        
        print(f"Keystone: /auth/verify successful for user '{decoded_token['username']}'.")
        return jsonify({
            "valid": True,
            "username": decoded_token['username'],
            "role": decoded_token['role']
        }), 200
    except jwt.ExpiredSignatureError:
        print("Keystone: /auth/verify failed: Token expired.")
        return jsonify({"valid": False, "message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        print("Keystone: /auth/verify failed: Invalid token.")
        return jsonify({"valid": False, "message": "Invalid token"}), 401
    except Exception as e:
        print(f"Keystone: /auth/verify failed with unexpected error: {e}")
        return jsonify({"valid": False, "message": str(e)}), 500

@app.route('/auth/authorize', methods=['POST'])
def authorize_action():
    """
    Authorizes a specific action for a user based on their token and RBAC policies.
    """
    data = request.get_json()
    token = data.get('token')
    action_uri = data.get('action_uri')

    if not token or not action_uri:
        return jsonify({"message": "Token or action_uri missing"}), 400

    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if decoded_token['exp'] < time.time():
            print("Keystone: /auth/authorize failed: Token expired.")
            return jsonify({"authorized": False, "reason": "Token expired"}), 401

        user_role = decoded_token.get('role')
        if not user_role:
            print(f"Keystone: /auth/authorize failed: No role found in token for user '{decoded_token.get('username')}'.")
            return jsonify({"authorized": False, "reason": "No role assigned"}), 403

        # Check if the role has permission for the action
        role_policies = rbac_policies.get(user_role, {})
        
        # Check for specific action or wildcard permission
        if role_policies.get(action_uri) or role_policies.get("*"):
            print(f"Keystone: /auth/authorize GRANTED for user '{decoded_token.get('username')}' (Role: '{user_role}') for action '{action_uri}'.")
            return jsonify({"authorized": True}), 200
        else:
            print(f"Keystone: /auth/authorize DENIED for user '{decoded_token.get('username')}' (Role: '{user_role}') for action '{action_uri}'.")
            return jsonify({"authorized": False, "reason": "Not authorized by policy"}), 403

    except jwt.ExpiredSignatureError:
        print("Keystone: /auth/authorize failed: Token expired.")
        return jsonify({"authorized": False, "reason": "Token expired"}), 401
    except jwt.InvalidTokenError:
        print("Keystone: /auth/authorize failed: Invalid token.")
        return jsonify({"authorized": False, "reason": "Invalid token"}), 401
    except Exception as e:
        print(f"Keystone: /auth/authorize failed with unexpected error: {e}")
        return jsonify({"authorized": False, "reason": str(e)}), 500

if __name__ == '__main__':
    print("RBAC policies loaded successfully.")
    print("Starting Flask app...")
    app.run(host='0.0.0.0', port=5000, debug=True)

