# Save this content to secure_wamp_project/wamp_clients/rpc_caller.py
import argparse
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor
from autobahn.wamp.exception import ApplicationError
from wamp_clients.base_client import SecureWAMPClient, run_client

class RPCCallerClient(SecureWAMPClient):
    @inlineCallbacks
    def run_client_logic(self):
        procedure = "com.iiot.rpc.control_pump"
        action = f"{procedure}.call"

        if not (yield self._authorize_wamp_action(action)):
            print(f"RPC Caller '{self.username}': Not authorized to call procedure '{procedure}'. Disconnecting.")
            self.disconnect()
            return

        print(f"RPC Caller '{self.username}': Authorized to call procedure '{procedure}'.")

        try:
            print(f"RPC Caller '{self.username}': Calling RPC '{procedure}' for Pump ID='Pump1', Status='on'...")
            result_on = yield self.call(procedure, "Pump1", "on")
            print(f"RPC Caller '{self.username}': RPC result (on): {result_on}")
            yield self.sleep(2)

            print(f"RPC Caller '{self.username}': Calling RPC '{procedure}' for Pump ID='Pump1', Status='off'...")
            result_off = yield self.call(procedure, "Pump1", "off")
            print(f"RPC Caller '{self.username}': RPC result (off): {result_off}")
            yield self.sleep(2)

            print(f"RPC Caller '{self.username}': Attempting invalid call to '{procedure}' (invalid status)...")
            result_invalid = yield self.call(procedure, "Pump2", "invalid_status")
            print(f"RPC Caller '{self.username}': RPC result (invalid, should not reach here): {result_invalid}")

        except ApplicationError as e:
            print(f"RPC Caller '{self.username}': RPC call failed with ApplicationError: {e.error} - {e.args[0] if e.args else 'No details'}")
        except Exception as e:
            print(f"RPC Caller '{self.username}': An unexpected error occurred during RPC call to '{procedure}': {e}")
        finally:
            print(f"RPC Caller '{self.username}': RPC calls completed. Disconnecting.")
            self.disconnect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WAMP RPC Caller Client')
    parser.add_argument('--username', required=True, help='Username for authentication (e.g., user_admin or engineer_bob)')
    parser.add_argument('--password', required=True, help='Password for authentication')
    parser.add_argument('--realm', default="realm1", help='WAMP Realm to join (default: realm1)')
    args = parser.parse_args()

    run_client(RPCCallerClient, args.username, args.password, realm=args.realm)
