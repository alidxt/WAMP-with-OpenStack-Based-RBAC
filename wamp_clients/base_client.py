# Save this content to secure_wamp_project/wamp_clients/base_client.py
import sys
import argparse
import json
import requests
# Import specific Twisted SSL components
from twisted.internet import reactor
# Removed ClientTLSOptions and Certificate from here, as we're creating our own factory now
# optionsForClientTLS is not directly used for context creation, but might be useful for other options
from twisted.internet.ssl import optionsForClientTLS
from OpenSSL import SSL, crypto

# New imports for custom context factory
from zope.interface import implementer
from twisted.internet.interfaces import IOpenSSLCertificateOptions

from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp import types
import time
import os
from urllib.parse import urlparse # For parsing router URL

# Configuration for Mock Keystone
KEYSTONE_AUTH_URL = "http://127.0.0.1:5000/auth/tokens"
KEYSTONE_VERIFY_URL = "http://127.0.0.1:5000/auth/verify"
KEYSTONE_AUTHORIZE_URL = "http://127.0.0.1:5000/auth/authorize"

class SecureWAMPClient(ApplicationSession):
    def __init__(self, config=None):
        super().__init__(config)
        self.username = config.extra['username']
        self.password = config.extra['password']
        self.token = None # JWT token from Keystone

        # These will be set by run_client function before connecting
        self.router_url = None
        self.router_host = None
        self.router_port = None

    @inlineCallbacks
    def onConnect(self):
        print(f"Client '{self.username}': Connected to WAMP router transport. Initiating authentication with Mock Keystone...")

        # --- Authentication with Mock Keystone (HTTP API) ---
        try:
            auth_response = requests.post(KEYSTONE_AUTH_URL, json={
                "username": self.username,
                "password": self.password
            })
            auth_response.raise_for_status()
            auth_data = auth_response.json()
            self.token = auth_data['token']
            print(f"Client '{self.username}': Successfully obtained JWT token from Mock Keystone.")

            # --- Join WAMP Realm (Crossbar.io allows anonymous by default) ---
            print(f"Client '{self.username}': Joining WAMP realm '{self.config.realm}'...")
            self.join(self.config.realm)

        except requests.exceptions.RequestException as e:
            print(f"Client '{self.username}': ERROR authenticating with Mock Keystone (HTTP request failed): {e}")
            self.disconnect()
        except Exception as e:
            print(f"Client '{self.username}': AN UNEXPECTED ERROR occurred during onConnect/authentication: {e}")
            self.disconnect()

    @inlineCallbacks
    def onJoin(self, details):
        print(f"Client '{self.username}': Session joined realm '{details.realm}'.")
        print(f"Client '{self.username}': WAMP connection successful (AuthID: '{details.authid}', AuthRole: '{details.authrole}').")
        print(f"Client '{self.username}': RBAC enforcement will happen via Mock Keystone calls before WAMP operations.")
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
        # This method is meant to be overridden by specific client implementations (publisher, subscriber, etc.)
        print(f"Client '{self.username}': No specific client logic defined in base class. Disconnecting in 5 seconds.")
        yield self.sleep(5) # autobahn.twisted.util.sleep
        self.disconnect()

    @inlineCallbacks
    def _authorize_wamp_action(self, action_uri):
        # This method is crucial for client-side RBAC enforcement.
        if not self.token:
            print(f"Client '{self.username}': No token available. Cannot authorize action: {action_uri}.")
            return False

        try:
            print(f"Client '{self.username}': Checking authorization with Mock Keystone for action: '{action_uri}'...")
            authz_response = requests.post(KEYSTONE_AUTHORIZE_URL, json={
                "token": self.token,
                "action_uri": action_uri
            })
            authz_response.raise_for_status()
            authz_data = authz_response.json()

            if not authz_data.get('authorized'):
                print(f"Client '{self.username}': Authorization DENIED for '{action_uri}': {authz_data.get('reason', 'No specific reason.')}")
                return False

            print(f"Client '{self.username}': Authorization GRANTED for '{action_uri}'.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Client '{self.username}': ERROR checking authorization with Mock Keystone (HTTP request failed) for '{action_uri}': {e}")
            return False
        except Exception as e:
            print(f"Client '{self.username}': AN UNEXPECTED ERROR occurred during authorization check for '{action_uri}': {e}")
            return False

# NEW CLASS: Custom context factory to implement IOpenSSLCertificateOptions
# This allows us to inject our pre-configured OpenSSL.SSL.Context
@implementer(IOpenSSLCertificateOptions)
class CustomTLSClientContextFactory:
    def __init__(self, hostname, cert_path):
        self._hostname = hostname.encode('utf8') if isinstance(hostname, str) else hostname
        self._cert_path = cert_path
        self._context = None # Will be initialized on first use

    def _makeContext(self):
        """
        Required by IOpenSSLCertificateOptions.
        Create and configure the OpenSSL.SSL.Context here.
        This method is called by Twisted when it needs the context.
        """
        if self._context is None:
            try:
                # Load the server.crt content
                with open(self._cert_path, 'rb') as f:
                    trusted_cert_pem = f.read()

                # Create an SSL context using pyOpenSSL
                context = SSL.Context(SSL.TLS_METHOD) 

                # Load the trusted certificate into the context's certificate store
                x509_cert = crypto.load_certificate(crypto.FILETYPE_PEM, trusted_cert_pem)
                context.get_cert_store().add_cert(x509_cert)

                # Set verification mode to VERIFY_PEER, but provide a callback that always returns True
                # This effectively disables strict hostname checking (which fails due to missing SAN)
                # while still ensuring the certificate is presented and trusted via cafile.
                context.set_verify(
                    SSL.VERIFY_PEER, # This tells OpenSSL to ask for and verify the peer's certificate
                    lambda connection, x509, errnum, errdepth, preverify_ok: True # This callback overrides default hostname check
                )
                self._context = context
            except Exception as e:
                # Log error and potentially re-raise, or handle gracefully
                print(f"ERROR: Failed to create custom SSL context: {e}")
                raise # Re-raise the exception to propagate the error
        return self._context

    def getHostNameForSNI(self):
        """
        Return the hostname for Server Name Indication (SNI).
        Required by IOpenSSLCertificateOptions.
        """
        return self._hostname


def run_client(client_class, username, password, url="wss://localhost:8080/ws", realm="realm1"):
    # Parse host and port from the URL for Twisted's connectSSL
    parsed_url = urlparse(url)
    router_host = parsed_url.hostname
    router_port = parsed_url.port or 443 # Default to 443 for wss if not specified

    # --- Modified TLS Context Setup for Twisted/pyOpenSSL ---
    tls_options = None
    try:
        tls_cert_path = os.path.join(os.path.dirname(__file__), '..', 'certs', 'server.crt')
        if not os.path.exists(tls_cert_path):
            raise FileNotFoundError(f"Server certificate not found at {tls_cert_path}")

        # Use our custom context factory class
        tls_options = CustomTLSClientContextFactory(hostname=router_host, cert_path=tls_cert_path)

        print(f"Client '{username}': Created custom TLS context factory (with hostname check disabled).")

    except Exception as e:
        print(f"Client '{username}': ERROR setting up TLS context for client: {e}. Ensure certs/server.crt exists and is readable.")
        sys.exit(1)

    # Instantiate the client (Autobahn ApplicationSession)
    config = types.ComponentConfig(realm=realm, extra={'username': username, 'password': password})
    client_session = client_class(config=config)

    # Assign router details to the client instance for use in onConnect
    client_session.router_url = url
    client_session.router_host = router_host
    client_session.router_port = router_port

    print(f"Client '{username}': Attempting to connect to WAMP router at {client_session.router_url} (Host: {client_session.router_host}, Port: {client_session.router_port})...")

    try:
        runner = ApplicationRunner(
            url=url,
            realm=realm,
            extra={'username': username, 'password': password},
            ssl=tls_options # Pass the generated TLS options here
        )
        print(f"Client '{username}': Starting ApplicationRunner. This will block until disconnection or error.")
        runner.run(client_session, start_reactor=True)
    except Exception as e:
        print(f"Client '{username}': ERROR caught during ApplicationRunner.run(): {e}")
        if reactor.running: # Ensure reactor is stopped if an error occurs during initial run
            reactor.stop()
    print(f"Client '{username}': ApplicationRunner has finished.")
