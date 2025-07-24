import os
import sys
import time
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task 
from twisted.internet.error import ConnectionRefusedError

sys.path.insert(0, '/app') 

from autobahn.twisted.wamp import ApplicationRunner, ApplicationSession
from autobahn.wamp.exception import ApplicationError 
import requests 


class AuthenticatorClientSession(ApplicationSession):
    def __init__(self, config=None):
        super().__init__(config)
        print(f"Authenticator Runner: Initializing AuthenticatorClientSession for realm '{config.realm}'.")


    @inlineCallbacks
    def onConnect(self):
        print(f"Authenticator Runner: Connected to WAMP router transport. Joining realm '{self.config.realm}'...")
        
        try:
            yield self.join(self.config.realm, authmethods=['anonymous'])
        except Exception as e:
            print(f"Authenticator Runner: ERROR joining realm: {e}")
            self.disconnect()


    @inlineCallbacks
    def onJoin(self, details):
        print(f"Authenticator Runner: Joined realm '{details.realm}'. Session ID: {details.session}")
        print(f"Authenticator Runner: Authenticated via 'anonymous' with role 'anonymous'.") 

        try:
            yield self.register(self.authenticate, 'com.example.authenticate')
            print("Authenticator Runner: Dynamic authenticator 'com.example.authenticate' registered successfully.")
        except Exception as e:
            print(f"Authenticator Runner: Could not register authenticator: {e}")
            self.leave()
            return
        
        yield None 

    def onLeave(self, details):
        print(f"Authenticator Runner: Session left realm: {details.reason}.")
        if reactor.running:
            reactor.stop()

    def onDisconnect(self):
        print(f"Authenticator Runner: Transport disconnected.")
        if reactor.running:
            reactor.stop()

    @inlineCallbacks
    def authenticate(self, realm, authid, details):
        print(f"Authenticator Runner: Received authentication request for authid='{authid}' on realm='{realm}'")
        
        password = details.get('ticket') or details.get('authextra', {}).get('ticket')
        
        if not password: 
            print("Authenticator Runner: Authentication failed: No ticket provided in authentication details.")
            raise ApplicationError("com.example.error.no_ticket_provided", "No ticket provided.")

        try:
            keystone_url = "http://mock_keystone_server:5000/authenticate" 
            payload = {"username": authid, "password": password} 
            print(f"Authenticator Runner: Sending authentication request to Keystone: {payload}")
            response = requests.post(keystone_url, json=payload)
            response.raise_for_status() 
            
            result = response.json()
            
            if result.get("authenticated"):
                authrole = result.get("role")
                print(f"Authenticator Runner: Authentication successful for '{authid}'. Assigned role: '{authrole}'")
                return authrole
            else:
                print(f"Authenticator Runner: Authentication failed for '{authid}'.")
                raise ApplicationError("com.example.error.authentication_failed", "Authentication failed.")

        except requests.exceptions.RequestException as e:
            print(f"Authenticator Runner: Error communicating with Keystone server: {e}")
            raise ApplicationError("com.example.error.keystone_unavailable", "Keystone server unavailable.")
        except Exception as e:
            print(f"Authenticator Runner: Unexpected error during authentication: {e}")
            raise ApplicationError("com.example.error.internal_error", "Internal authentication error.")


print("Authenticator Runner: Python script started.")

time.sleep(15) 

try:
    runner = ApplicationRunner(
        url="ws://crossbar_router:8080/ws", 
        realm="realm1",
        extra={ 
            "authid": "crossbar_authenticator_client", 
            "ticket": "some_secret_ticket_for_authenticator", 
            "authmethods": ['anonymous'] 
        }
    )
    print("Authenticator Runner: ApplicationRunner instantiated. Running...")
    runner.run(AuthenticatorClientSession, start_reactor=True)
    print("Authenticator Runner: WAMP Authenticator finished.")
except ConnectionRefusedError:
    print(f"Authenticator Runner: Connection refused. Ensure Crossbar.io is running and accessible on {runner.url}.")
    if reactor.running:
        reactor.stop()
except Exception as e:
    print(f"Authenticator Runner: ERROR during ApplicationRunner setup or run: {e}")
    if reactor.running:
        reactor.stop()
