# Save this content to secure_wamp_project/wamp_clients/subscriber.py
import argparse
from twisted.internet.defer import inlineCallbacks
from wamp_clients.base_client import SecureWAMPClient, run_client

class SubscriberClient(SecureWAMPClient):
    @inlineCallbacks
    def run_client_logic(self):
        topic = "com.iiot.topic.sensor_data"
        action = f"{topic}.subscribe"

        if not (yield self._authorize_wamp_action(action)):
            print(f"Subscriber '{self.username}': Not authorized to subscribe to {topic}. Disconnecting.")
            self.disconnect()
            return

        print(f"Subscriber '{self.username}': Authorized to subscribe to {topic}.")

        def on_event(data):
            print(f"Subscriber '{self.username}': Received event from '{topic}': {data}")

        try:
            yield self.subscribe(on_event, topic)
            print(f"Subscriber '{self.username}': Subscribed to '{topic}'. Waiting for events...")
            while True:
                yield self.sleep(10)
        except Exception as e:
            print(f"Subscriber '{self.username}': Failed to subscribe to '{topic}': {e}")
            self.disconnect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WAMP Subscriber Client')
    parser.add_argument('--username', required=True, help='Username for authentication')
    parser.add_argument('--password', required=True, help='Password for authentication')
    parser.add_argument('--realm', default="realm1", help='WAMP Realm to join (default: realm1)')
    args = parser.parse_args()

    run_client(SubscriberClient, args.username, args.password, realm=args.realm)
