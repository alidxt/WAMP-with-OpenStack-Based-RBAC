# Save this content to secure_wamp_project/wamp_clients/publisher.py
import argparse
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task 
from wamp_clients.base_client import SecureWAMPClient, run_client
import time

class PublisherClient(SecureWAMPClient):
    @inlineCallbacks
    def run_client_logic(self):
        topic = "com.iiot.topic.sensor_data"
        action = f"{topic}.publish"

        if not self._authorize_wamp_action(action): 
            print(f"Publisher '{self.username}': Not authorized to publish to {topic}. Disconnecting.")
            self.disconnect()
            return

        print(f"Publisher '{self.username}': Authorized to publish to {topic}.")

        counter = 0
        while True:
            data = {"value": counter, "timestamp": time.time()}
            try:
                yield self.publish(topic, data) 
                print(f"Publisher '{self.username}': Publishing event to '{topic}': {data}")
                counter += 1
            except Exception as e:
                print(f"Publisher '{self.username}': Failed to publish to '{topic}': {e}")
                self.disconnect()
                break 
            yield task.deferLater(reactor, 2, lambda: None) 

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WAMP Publisher Client')
    parser.add_argument('--username', default="sensor_device_1_publisher", help='Username for logging')
    parser.add_argument('--authid', default="sensor_publisher_client", help='WAMP AuthID for authentication') 
    parser.add_argument('--ticket', default="sensor_publisher_secret", help='WAMP Ticket for authentication') 
    parser.add_argument('--realm', default="realm1", help='WAMP Realm to join (default: realm1)')
    args = parser.parse_args()

    print(f"Publisher client script started for {args.username}.")
    time.sleep(5) 

    WAMP_ROUTER_URL = "ws://crossbar_router:8080/ws" 

    run_client(PublisherClient, WAMP_ROUTER_URL, realm=args.realm, username=args.username, authid=args.authid, ticket=args.ticket)
