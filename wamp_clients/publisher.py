# Save this content to secure_wamp_project/wamp_clients/publisher.py
import time
import argparse
from twisted.internet.defer import inlineCallbacks
from wamp_clients.base_client import SecureWAMPClient, run_client

class PublisherClient(SecureWAMPClient):
    @inlineCallbacks
    def run_client_logic(self):
        topic = "com.iiot.topic.sensor_data"
        action = f"{topic}.publish"

        if not (yield self._authorize_wamp_action(action)):
            print(f"Publisher '{self.username}': Not authorized to publish to {topic}. Disconnecting.")
            self.disconnect()
            return

        print(f"Publisher '{self.username}': Authorized to publish to {topic}.")
        counter = 0
        while True:
            try:
                data = {"sensor_id": f"sensor_{self.username}", "value": counter, "timestamp": time.time()}
                print(f"Publisher '{self.username}': Publishing event to '{topic}': {data}")
                yield self.publish(topic, data)
                counter += 1
                yield self.sleep(3)
            except Exception as e:
                print(f"Publisher '{self.username}': Error publishing: {e}. Check if connection lost or other WAMP error.")
                break

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WAMP Publisher Client')
    parser.add_argument('--username', required=True, help='Username for authentication (e.g., sensor_a)')
    parser.add_argument('--password', required=True, help='Password for authentication')
    parser.add_argument('--realm', default="realm1", help='WAMP Realm to join (default: realm1)')
    args = parser.parse_args()

    run_client(PublisherClient, args.username, args.password, realm=args.realm)
