import argparse
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task 
from wamp_clients.base_client import SecureWAMPClient, run_client
import time

class SubscriberClient(SecureWAMPClient):
    @inlineCallbacks
    def run_client_logic(self):
        topic = "com.iiot.topic.sensor_data"
        action = f"{topic}.subscribe"

        if not self._authorize_wamp_action(action): 
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
                yield task.deferLater(reactor, 10, lambda: None) 
        except Exception as e:
            print(f"Subscriber '{self.username}': Failed to subscribe to '{topic}': {e}")
            self.disconnect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WAMP Subscriber Client')
    parser.add_argument('--username', default="hmi_dashboard_viewer", help='Username for logging')
    parser.add_argument('--authid', default="hmi_viewer_client", help='WAMP AuthID for authentication') 
    parser.add_argument('--ticket', default="hmi_viewer_secret", help='WAMP Ticket for authentication') 
    parser.add_argument('--realm', default="realm1", help='WAMP Realm to join (default: realm1)')
    args = parser.parse_args()

    print(f"Subscriber client script started for {args.username}.")
    time.sleep(5) 

    WAMP_ROUTER_URL = "ws://crossbar_router:8080/ws" 

    run_client(SubscriberClient, WAMP_ROUTER_URL, realm=args.realm, username=args.username, authid=args.authid, ticket=args.ticket)
