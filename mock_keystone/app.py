import json
import os
import sqlite3
import jwt
import datetime
import yaml
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your_super_secret_jwt_key_here_please_change_this_in_production')

def init_db():
    conn = sqlite3.connect('mock_keystone/users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            project_id TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            username TEXT,
            role TEXT,
            PRIMARY KEY (username, role),
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    ''')
    initial_users = {
        "user1": {"password": "password1", "roles": ["member"], "project_id": "project_alpha"},
        "user_admin": {"password": "adminpassword", "roles": ["admin"], "project_id": "project_alpha"},
        "sensor_a": {"password": "sensorpass", "roles": ["sensor_publisher"], "project_id": "project_bravo"},
        "hmi_dashboard": {"password": "hmidashpass", "roles": ["hmi_viewer"], "project_id": "project_alpha"},
        "engineer_bob": {"password": "engineerpass", "roles": ["engineer", "member"], "project_id": "project_charlie"},
    }
    for username, data in initial_users.items():
        cursor.execute("INSERT OR IGNORE INTO users (username, password, project_id) VALUES (?, ?, ?)",
                       (username, data['password'], data['project_id']))
        for role in data['roles']:
            cursor.execute("INSERT OR IGNORE INTO user_roles (username, role) VALUES (?, ?)",
                           (username, role))
    conn.commit()
    conn.close()

policies = {}
try:
    with open('mock_keystone/policies.yaml', 'r') as f:
        policies = yaml.safe_load(f)
    print("RBAC policies loaded successfully.")
except FileNotFoundError:
    print("Warning: policies.yaml not found. RBAC will be disabled or behave unexpectedly.")
except yaml.YAMLError as e:
    print(f"Error loading policies.yaml: {e}")
    policies = {}

def get_user_from_db(username):
    conn = sqlite3.connect('mock_keystone/users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password, project_id FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    if user_data:
        cursor.execute("SELECT role FROM user_roles WHERE username = ?", (username,))
        roles = [row[0] for row in cursor.fetchall()]
        conn.close()
        return {"password": user_data[0], "project_id": user_data[1], "roles": roles}
    conn.close()
    return None

def generate_token(username, roles, project_id):
    payload = {
        'sub': username,
        'roles': roles,
        'project_id': project_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        'iat': datetime.datetime.utcnow(),
        'iss': 'mock-keystone',
        'aud': 'wamp-app'
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'], audience='wamp-app', issuer='mock-keystone')
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired."}
    except jwt.InvalidAudienceError:
        return {"error": "Invalid token audience."}
    except jwt.InvalidIssuerError:
        return {"error": "Invalid token issuer."}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token."}
    except Exception as e:
        return {"error": f"Token verification failed: {e}"}

def evaluate_rule(rule_string, user_roles, user_project_id):
    if not rule_string:
        return True
    if rule_string == "!":
        return False
    if " or " in rule_string:
        for part in rule_string.split(" or "):
            if evaluate_rule(part.strip(), user_roles, user_project_id):
                return True
        return False
    
    if rule_string.startswith("role:"):
        required_role = rule_string.split("role:")[1]
        return required_role in user_roles
    return False

def authorize_action(token_payload, action_uri):
    if not policies:
        print("No policies loaded in mock_keystone. Authorization will grant all access by default.")
        return True

    user_roles = token_payload.get('roles', [])
    user_project_id = token_payload.get('project_id')
    username = token_payload.get('sub')

    policy_rule = policies.get(action_uri)

    if policy_rule is not None:
        if evaluate_rule(policy_rule, user_roles, user_project_id):
            print(f"Authorization GRANTED for user '{username}' (roles: {user_roles}) for action '{action_uri}' by specific policy.")
            return True
        else:
            print(f"Authorization DENIED for user '{username}' (roles: {user_roles}) for action '{action_uri}' by specific policy '{policy_rule}'.")
            return False
    
    print(f"Authorization DENIED for user '{username}' (roles: {user_roles}) for action '{action_uri}'. No specific policy found.")
    return False


@app.route('/auth/tokens', methods=['POST'])
def authenticate():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = get_user_from_db(username)

    if user and user['password'] == password:
        token = generate_token(username, user['roles'], user['project_id'])
        return jsonify({"token": token, "user": {"username": username, "roles": user['roles'], "project_id": user['project_id']}}), 200
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/auth/verify', methods=['POST'])
def verify():
    data = request.json
    token = data.get('token')
    payload = verify_token(token)
    if "error" in payload:
        return jsonify(payload), 401
    return jsonify({"valid": True, "payload": payload}), 200

@app.route('/auth/authorize', methods=['POST'])
def authorize():
    data = request.json
    token = data.get('token')
    action_uri = data.get('action_uri')

    payload = verify_token(token)
    if "error" in payload:
        return jsonify({"authorized": False, "reason": payload["error"]}), 401

    if authorize_action(payload, action_uri):
        return jsonify({"authorized": True}), 200
    return jsonify({"authorized": False, "reason": "Not authorized by policy"}), 403

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5000, debug=True)
