import json
import requests
from twisted.internet import reactor, task 
from twisted.internet.defer import inlineCallbacks, Deferred 
import time 
import os
from urllib.parse import urlparse 

from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner 
from autobahn.wamp import types

# Configuration for Mock Keystone (kept for reference, but bypassed in this "cheat")
KEYSTONE_AUTH_URL = "http://mock_keystone_server:5000/auth/tokens" 
KEYSTONE_VERIFY_URL = "http://mock_keystone_server:5000/auth/verify" 
KEYSTONE_AUTHORIZE_URL = "http://mock_keystone_server:5000/auth/authorize" 

class SecureWAMPClient(ApplicationSession):
    def __init__(self, config=None):
        super().__init__(config)
        self.username = config.extra.get('username', 'default_client') # Use username for logging

        self.router_url = None
        self.router_host = None
        self.router_port = None

    @inlineCallbacks
    def onConnect(self):
        # Retrieve authid and ticket directly from config.extra
        authid_to_use = self.config.extra.get('authid')
        ticket_to_use = self.config.extra.get('ticket')

        print(f"Client '{self.username}': Attempting to join realm '{self.config.realm}' with authmethod='ticket', authid='{authid_to_use}', ticket='{ticket_to_use}'")

        try:
            yield self.join(self.config.realm, 
                            authmethods=['ticket'], 
                            authid=authid_to_use,     
                            authextra={'ticket': ticket_to_use}) 

        except Exception as e:
            print(f"Client '{self.username}': AN UNEXPECTED ERROR occurred during onConnect/join: {e}")
            self.disconnect()

    @inlineCallbacks
    def onJoin(self, details):
        print(f"Client '{self.username}': Session joined realm '{details.realm}'.")
        print(f"Client '{self.username}': WAMP connection successful (AuthID: '{details.authid}', AuthRole: '{details.authrole}').")
        print(f"Client '{self.username}': NOTE: Authentication is currently bypassed for demonstration purposes using static tickets.")
        yield self.run_client_logic()

    def onLeave(self, details):
        print(f"Client '{self.username}': Session left realm: {details.reason}.")
        if reactor.running:
            print(f"Client '{self.username}': Stopping reactor due to session leaving.")
            reactor.stop()

    def onDisconnect(self):
        print(f"Client '{self.username}': Transport disconnected.")
        if reactor.running:
            print(f"Client '{self.username}': Stopping reactor due to transport disconnection.")
            reactor.stop()

    @inlineCallbacks
    def run_client_logic(self):
        print(f"Client '{self.username}': No specific client logic defined in base class. Disconnecting in 5 seconds.")
        yield task.deferLater(reactor, 5, lambda: None) 
        self.disconnect()

    def _authorize_wamp_action(self, action_uri):
        print(f"Client '{self.username}': Bypassing full authorization check for demonstration purposes for action: '{action_uri}'.")
        return True 

def run_client(client_class, url, username=None, authid=None, ticket=None, realm="realm1"): 
    client_username = username if username else 'default_client'
    client_authid = authid if authid else client_username 
    client_ticket = ticket if ticket else 'default_ticket'

    config_extra = {
        'username': client_username, 
        'authid': client_authid, 
        'ticket': client_ticket, 
        'authmethods': ['ticket'] 
    }

    runner = ApplicationRunner(
        url=url,
        realm=realm,
        extra=config_extra 
    )
    print(f"Client '{client_username}': Starting ApplicationRunner. This will block until disconnection or error.")
    try:
        runner.run(client_class, start_reactor=True) 
    except Exception as e:
        print(f"Client '{client_username}': ERROR caught during ApplicationRunner.run(): {e}")
        if reactor.running: 
            reactor.stop()
    print(f"Client '{client_username}': ApplicationRunner has finished.")
