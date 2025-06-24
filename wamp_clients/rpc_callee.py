# Save this content to secure_wamp_project/wamp_clients/rpc_callee.py
import argparse
from twisted.internet.defer import inlineCallbacks
from wamp_clients.base_client import SecureWAMPClient, run_client

class RPCCalleeClient(SecureWAMPClient):
    @inlineCallbacks
    def run_client_logic(self):
        procedure = "com.iiot.rpc.control_pump"
        action = f"{procedure}.register"

        if not (yield self._authorize_wamp_action(action)):
            print(f"RPC Callee '{self.username}': Not authorized to register procedure '{procedure}'. Disconnecting.")
            self.disconnect()
            return

        print(f"RPC Callee '{self.username}': Authorized to register procedure '{procedure}'.")

        def control_pump(pump_id, status):
            print(f"RPC Callee '{self.username}': Received RPC call to control_pump: Pump ID='{pump_id}', New Status='{status}'")
            if status not in ["on", "off"]:
                raise Exception("Invalid pump status. Must be 'on' or 'off'.")
            
            print(f"RPC Callee '{self.username}': Simulating setting Pump '{pump_id}' to '{status}'.")
            
            return {"pump_id": pump_id, "status": status, "message": f"Pump '{pump_id}' successfully set to '{status}'"}

        try:
            yield self.register(control_pump, procedure)
            print(f"RPC Callee '{self.username}': Registered procedure '{procedure}'. Waiting for calls...")
            while True:
                yield self.sleep(10)
        except Exception as e:
            print(f"RPC Callee '{self.username}': Failed to register procedure '{procedure}': {e}")
            self.disconnect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WAMP RPC Callee Client')
    parser.add_argument('--username', required=True, help='Username for authentication (e.g., user_admin or engineer_bob)')
    parser.add_argument('--password', required=True, help='Password for authentication')
    parser.add_argument('--realm', default="realm1", help='WAMP Realm to join (default: realm1)')
    args = parser.parse_args()

    run_client(RPCCalleeClient, args.username, args.password, realm=args.realm)
