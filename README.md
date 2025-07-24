# **Secure WAMP Messaging with Dynamic RBAC over TLS**

This project implements a secure and robust messaging infrastructure using the Web Application Messaging Protocol (WAMP), enhanced with Role-Based Access Control (RBAC) and Transport Layer Security (TLS). The system demonstrates how clients can be dynamically authenticated against a simulated OpenStack Keystone service and authorized based on their assigned roles for WAMP Publish & Subscribe (PubSub) and Remote Procedure Call (RPC) operations, all over an encrypted channel.

## **1\. Project Goal**

The core objective is to showcase secure WAMP communication by enforcing authentication and authorization policies using a simulated OpenStack Keystone service, with an added layer of transport security via TLS. Specifically, the system aims to:

* **Authenticate WAMP Clients:** Clients must prove their identity using credentials (username/password) verified by a Mock Keystone server.  
* **Assign Roles:** Upon successful authentication, clients are assigned specific roles (e.g., hmi\_viewer, sensor\_publisher) based on policies defined in the Mock Keystone.  
* **Enforce RBAC:** The Crossbar.io WAMP router enforces authorization rules, ensuring clients can only perform WAMP operations (publish, subscribe, call) permitted by their assigned roles.  
* **Establish a Functional WAMP Ecosystem:** Implement a WAMP Authenticator, Publisher, and Subscriber to showcase the end-to-end secure communication flow.  
* **Secure Communication with TLS:** All WAMP communication between clients and the Crossbar.io router is encrypted using TLS, protecting data in transit from eavesdropping and tampering.

## **2\. Architecture Overview**

The project is structured as a multi-container Docker Compose application, ensuring isolation and easy deployment of each component. The architecture comprises the following key services:

\+-------------------+       \+-------------------+       \+-------------------+  
|   WAMP Publisher  |       | WAMP Authenticator|       |  WAMP Subscriber  |  
|  (Python Client)  |\<--WSS-\> (Python Client)  |\<--WSS-\> (Python Client)   |  
\+-------------------+       \+-------------------+       \+-------------------+  
          ^                         ^                         ^  
          | (WAMP Pub/Sub/RPC over TLS) | (WAMP Auth Procedure over TLS)| (WAMP Pub/Sub/RPC over TLS)  
          V                         V                         V  
\+-------------------------------------------------------------------------+  
|                    Crossbar.io Router                                   |  
| (WAMP Broker, Dynamic Authenticator, RBAC Policy Enforcement, WSS Listener) |  
\+-------------------------------------------------------------------------+  
          ^                                       | (HTTP/REST for Auth)  
          |                                       V  
          \+---------------------------------------+  
          |           Mock Keystone Server        |  
          |           (Flask App)                 |  
          \+---------------------------------------+

* **crossbar\_router**: The central WAMP broker responsible for routing messages and enforcing security policies, now configured for WSS (WebSocket Secure) connections.  
* **mock\_keystone\_server**: A Flask-based web service that simulates OpenStack Keystone. It stores user credentials and their associated roles, providing an authentication endpoint.  
* **mock\_keystone\_wamp\_authenticator**: A Python (Autobahn|Python) WAMP client that acts as a dynamic authenticator. It registers an authentication procedure with Crossbar.io and validates client credentials by querying the Mock Keystone server. It connects via WSS.  
* **wamp\_publisher**: A Python (Autobahn|Python) WAMP client designed to publish sensor data to a specific WAMP topic, requiring authentication and connecting via WSS.  
* **wamp\_subscriber**: A Python (Autobahn|Python) WAMP client designed to subscribe to sensor data topics and call RPCs, also requiring authentication and connecting via WSS.

## **3\. Key Components**

### **3.1. generate\_certs.sh**

This is a shell script responsible for generating the self-signed TLS certificates necessary for secure communication (wss://).

* **Role:** Creates a Certificate Authority (CA) and a server certificate signed by this CA.  
* **Functionality:** Uses openssl commands to generate:  
  * ca.key and ca.crt: The private key and certificate for our self-signed Certificate Authority.  
  * server.key and server.crt: The private key and certificate for the Crossbar.io router, signed by our CA.  
* **TLS Integration:** These generated certificate files are crucial for enabling WSS connections. The server.key and server.crt are used by the Crossbar.io router to encrypt its traffic, while ca.crt is distributed to clients so they can trust the router's certificate.

### **3.2. requirements.txt**

This file lists all Python package dependencies for the mock\_keystone\_server and all WAMP client applications.

* **Role:** Ensures all necessary libraries are installed within the Docker containers.  
* **Key Libraries:**  
  * autobahn\[twisted\]: The official WAMP client library for Python, built on the Twisted asynchronous networking framework, which handles WebSocket communication and WAMP protocol.  
  * Flask: A lightweight Python web framework used to build the mock\_keystone\_server's REST API.  
  * pyjwt: For handling JSON Web Tokens (JWTs) within the mock\_keystone\_server.  
  * requests: Used by the mock\_keystone\_wamp\_authenticator to make HTTP calls to the mock\_keystone\_server.

### **3.3. .crossbar/config.json**

This is the central configuration file for the Crossbar.io WAMP router, defining its behavior, security policies, and TLS settings.

* **Role:** Configures the WAMP realm, defines RBAC roles and permissions, sets up the dynamic authentication mechanism, and enables WSS.  
* **RBAC Policies:**  
  * **realm1**: The primary WAMP realm where clients connect.  
  * **roles**:  
    * hmi\_viewer: Granted subscribe permission for com.iiot.topic.sensor\_data and call permission for com.example.get\_hmi\_status.  
    * sensor\_publisher: Granted publish permission for com.iiot.topic.sensor\_data.  
    * authenticator: A special role for the mock\_keystone\_wamp\_authenticator, granting it permission to register and call the dynamic authentication procedure (com.example.authenticate).  
* **Dynamic Authentication (authenticators section):**  
  * Configures a ticket authenticator. Instead of static user definitions, it points to a factory that uses a WAMP procedure (com.example.authenticate). This means Crossbar.io will call this procedure whenever a client attempts to authenticate using the ticket method.  
  * It also defines a static authid (dynamic\_authenticator) and ticket (authenticator\_secret) for the mock\_keystone\_wamp\_authenticator itself to join the realm.  
* **TLS Integration (transports section):**  
  * The WebSocket transport is configured to use tls, pointing to /app/certs/server.key and /app/certs/server.crt (paths within the Docker container) for encryption.  
  * The url is explicitly set to wss://0.0.0.0:8080/ws to indicate a secure WebSocket connection.

### **3.4. mock\_keystone/app.py**

This Flask application serves as a simplified mock of an OpenStack Keystone identity service.

* **Role:** Manages mock user credentials and their associated roles, and provides an API for authentication and authorization checks.  
* **Functionality:**  
  * **users dictionary:** Stores predefined usernames, passwords, and their corresponding roles (e.g., hmi\_dashboard\_user with hmi\_viewer role, sensor\_device\_1\_user with sensor\_publisher role).  
  * **/authenticate endpoint (used by WAMP Authenticator):** Receives a username and password, verifies them against the users dictionary, and returns whether authentication was successful along with the user's assigned role. This is the primary endpoint used by the mock\_keystone\_wamp\_authenticator.  
  * Other endpoints (/auth/tokens, /auth/verify, /auth/authorize) demonstrate a more complete JWT-based authentication flow but are not directly used by the WAMP clients in this setup.

### **3.5. mock\_keystone/authenticator\_runner.py**

This Python script acts as the crucial bridge between Crossbar.io's dynamic authentication requests and the mock\_keystone\_server.

* **Role:** Registers a WAMP procedure with Crossbar.io that handles authentication requests from other WAMP clients by querying the mock\_keystone\_server.  
* **Functionality:**  
  * Connects to the crossbar\_router via wss:// using its own static authid (dynamic\_authenticator) and ticket (authenticator\_secret), which grants it the authenticator role as per config.json.  
  * Upon successful connection, it **registers the WAMP procedure com.example.authenticate** with Crossbar.io.  
  * The authenticate method: This is the callback function that Crossbar.io invokes when a client attempts to authenticate using the ticket method. It receives the client's authid (username) and ticket (password).  
  * It then makes an **HTTP POST request to http://mock\_keystone\_server:5000/authenticate** to verify these credentials.  
  * Based on Keystone's response, it returns the client's assigned role (e.g., hmi\_viewer, sensor\_publisher) back to Crossbar.io.  
* **TLS Integration:** Connects to Crossbar.io via wss://. For demo purposes, tls\_verify\_hostname=False is used, and urllib3.disable\_warnings is employed for the HTTP request to Keystone, as we are using self-signed certificates. In a production environment, proper CA trust would be configured.

### **3.6. wamp\_clients/base\_client.py**

This Python file defines the SecureWAMPClient class, which serves as a base for all specific WAMP clients (publisher and subscriber).

* **Role:** Provides common WAMP connection, session management, and dynamic authentication logic for all clients.  
* **Functionality:**  
  * **onConnect():** Initiates the WAMP session by attempting to join the specified realm (realm1). It uses the ticket authentication method, passing the client's username as authid and password as authextra\['ticket'\]. This triggers the dynamic authentication flow on Crossbar.io.  
  * **onJoin():** Called upon successful realm joining, confirming the AuthID and AuthRole assigned by Crossbar.io (which comes from the mock\_keystone\_wamp\_authenticator).  
  * **run\_client():** A helper function that sets up and runs the Autobahn ApplicationRunner for any SecureWAMPClient subclass. It passes the username and password as extra configuration.  
* **TLS Integration:** The ApplicationRunner is configured to connect via wss:// and uses tls\_verify\_hostname=False for demo purposes with self-signed certificates.

### **3.7. wamp\_clients/subscriber.py**

This client extends SecureWAMPClient and acts as an HMI dashboard viewer.

* **Role:** Subscribes to sensor data topics and demonstrates RPC calling, adhering to the hmi\_viewer role's permissions.  
* **Functionality:**  
  * Connects to the crossbar\_router via wss://.  
  * Authenticates using the username hmi\_dashboard\_user and its password (hmidashpass).  
  * Upon successful authentication, it attempts to subscribe to the com.iiot.topic.sensor\_data topic. This operation will only succeed if the assigned hmi\_viewer role has the necessary permission in config.json.  
  * It also conceptually attempts to call an RPC procedure (com.example.get\_hmi\_status), which would also be governed by its role's permissions.

### **3.8. wamp\_clients/publisher.py**

This client extends SecureWAMPClient and acts as a sensor device.

* **Role:** Periodically publishes sensor data to a WAMP topic, adhering to the sensor\_publisher role's permissions.  
* **Functionality:**  
  * Connects to the crossbar\_router via wss://.  
  * Authenticates using the username sensor\_device\_1\_user and its password (sensordevicepass).  
  * Upon successful authentication, it periodically publishes events to the com.iiot.topic.sensor\_data topic. This operation will only succeed if the assigned sensor\_publisher role has the necessary permission in config.json.

## **4\. Authentication and Authorization Flow (Step-by-Step with TLS)**

1. **Certificate Generation:** The generate\_certs.sh script runs first (orchestrated by Docker Compose), creating the self-signed CA and server certificates in the ./certs directory.  
2. **Service Startup:**  
   * mock\_keystone\_server starts, exposing its authentication API.  
   * crossbar\_router starts, loading its config.json. It sets up realm1 with defined roles and permissions, and configures its ticket authenticator to use the dynamic WAMP procedure com.example.authenticate. It also initializes its WSS transport using the generated server.key and server.crt.  
   * mock\_keystone\_wamp\_authenticator starts. It connects to crossbar\_router via wss:// using its own static authid (dynamic\_authenticator) and ticket (authenticator\_secret). Crossbar.io authenticates this session and assigns it the authenticator role. Crucially, mock\_keystone\_wamp\_authenticator then **registers the WAMP procedure com.example.authenticate** with Crossbar.io.  
3. **Client Connection (e.g., wamp\_subscriber):**  
   * The wamp\_subscriber initiates a WebSocket Secure (WSS) connection to crossbar\_router:8080.  
   * **TLS Handshake:** A TLS handshake occurs. The client verifies the router's server.crt using the ca.crt (mounted into its container). If successful, an encrypted TLS tunnel is established.  
   * **WAMP HELLO Message:** Over the secure tunnel, the client sends a WAMP HELLO message, specifying realm1, authmethods=\['ticket'\], authid='hmi\_dashboard\_user', and authextra={'ticket': 'hmidashpass'}.  
4. **Router Challenge & Dynamic Authenticator Call:**  
   * Crossbar.io, seeing the ticket authentication method, identifies that it needs to call the com.example.authenticate procedure. It sends a CHALLENGE message to the client.  
   * The client responds with its AUTHENTICATE message (containing its password/ticket).  
   * Crossbar.io then **calls the com.example.authenticate procedure** (registered by mock\_keystone\_wamp\_authenticator), passing the client's authid (hmi\_dashboard\_user) and authextra (the password).  
5. **Keystone Verification:**  
   * The mock\_keystone\_wamp\_authenticator receives this call. It extracts the authid and password.  
   * It then makes an **HTTP POST request to http://mock\_keystone\_server:5000/authenticate** with these credentials.  
   * mock\_keystone\_server validates the credentials and returns the assigned role (e.g., "hmi\_viewer").  
6. **Role Assignment:**  
   * mock\_keystone\_wamp\_authenticator receives the role from Keystone and **returns this role ("hmi\_viewer") back to Crossbar.io**.  
   * Crossbar.io receives the role and successfully establishes the WAMP session for the wamp\_subscriber with the verified authid (hmi\_dashboard\_user) and the assigned authrole (hmi\_viewer).  
   * The wamp\_publisher follows the same authentication flow, receiving the sensor\_publisher role.  
7. **RBAC Enforcement:**  
   * From this point onwards, all WAMP operations (publish, subscribe, call) initiated by the wamp\_subscriber are checked against the permissions defined for the hmi\_viewer role in config.json. For example, its subscribe operation to com.iiot.topic.sensor\_data is allowed.  
   * Similarly, the wamp\_publisher's publish operation to com.iiot.topic.sensor\_data is checked against the sensor\_publisher role's permissions and allowed.  
   * If an operation is not permitted for a client's assigned role, Crossbar.io responds with a wamp.error.not\_authorized error.  
8. **Secure Data Flow:** Data flows securely over the TLS-encrypted WAMP WebSockets, with all interactions governed by the RBAC policies enforced by Crossbar.io in conjunction with the mock Keystone.

## **5\. Implementation Details**

* **Docker Compose:** Used to orchestrate the multiple services, defining their networks, dependencies, and volumes for code sharing, including the certs directory for TLS certificates.  
* **Python:** All WAMP clients and the Mock Keystone server are implemented in Python.  
* **Autobahn|Python:** The chosen WAMP client library for Python, providing the necessary abstractions for WAMP communication, including TLS support.  
* **Flask:** A lightweight Python web framework used for the Mock Keystone server.  
* **Twisted:** The asynchronous networking framework underlying Autobahn|Python, handling event loops and network connections.  
* **pyOpenSSL:** Python binding for OpenSSL, used by Twisted to handle TLS certificate loading and context creation.

## **6\. How to Run the System**

To run this project, you will need Docker and Docker Compose installed on your system.

1. **Clone the Repository (if applicable):**  
   \# Assuming your project is in a directory named WAMP-with-OpenStack-Based-RBAC  
   \# cd WAMP-with-OpenStack-Based-RBAC

2. Generate TLS Certificates:  
   First, ensure you have openssl installed on your host machine. Then, run the certificate generation script:  
   chmod \+x generate\_certs.sh  
   ./generate\_certs.sh

   This will create a certs directory in your project root containing ca.crt, server.key, and server.crt.  
3. Build and Start Docker Containers:  
   Navigate to the root directory of the project (where docker-compose.yml is located) and execute:  
   docker compose build \--no-cache  
   docker compose up \--force-recreate

   * docker compose build \--no-cache: This command builds the Docker images for your services from scratch, ensuring any changes in the Dockerfile or requirements.txt are applied.  
   * docker compose up \--force-recreate: This command starts all the services defined in docker-compose.yml. \--force-recreate ensures that containers are stopped, removed, and recreated, picking up any changes to volumes or configurations.  
4. Monitor Logs (Recommended):  
   Open separate terminal windows to monitor the logs of each service. This is crucial for observing the authentication and data flow:  
   \# Terminal 1: Crossbar.io Router logs  
   docker compose logs crossbar\_router \--follow

   \# Terminal 2: Mock Keystone Server logs  
   docker compose logs mock\_keystone\_server \--follow

   \# Terminal 3: WAMP Authenticator logs  
   docker compose logs wamp\_authenticator \--follow

   \# Terminal 4: WAMP Subscriber logs  
   docker compose logs wamp\_subscriber \--follow

   \# Terminal 5: WAMP Publisher logs  
   docker compose logs wamp\_publisher \--follow

   You should observe the authentication handshake, role assignment, and then the publisher sending messages which are received by the subscriber, all confirmed by the logs.  
5. Stop the System:  
   To stop and remove all containers, networks, and volumes created by Docker Compose:  
   docker compose down \-v

   To clean up Docker build cache and unused images (useful for troubleshooting):  
   docker system prune \-a

## **7\. Current Status and Challenges**

The project successfully establishes the core architectural components and integrates TLS for secure communication.

**Current Status:**

* **Crossbar.io Router:** Starts successfully and is configured for WSS with server certificates. Its roles for dynamic authentication are correctly defined.  
* **Mock Keystone Server:** Starts successfully and can authenticate users based on its predefined policies, returning appropriate roles.  
* **Client Scripts (Authenticator, Publisher, Subscriber):** Are structured to connect to the router via WSS and attempt dynamic authentication using their respective usernames and passwords.

**Key Challenges Faced:**

* **Autobahn|Python Client Configuration:** Historically, ensuring that WAMP clients correctly transmit their authid and ticket/password in the initial WAMP HELLO message has been a significant challenge. This often led to ApplicationError(error=\<wamp.error.not\_authorized\>) due to subtle and version-specific behaviors of Autobahn|Python regarding how authentication details are passed. The current approach relies on passing authid and authextra as direct keyword arguments to ApplicationRunner, which has proven to be the most robust method.  
* **TLS Integration:**  
  * **Certificate Generation and Management:** Ensuring correct generation of CA, server, and client certificates.  
  * **Client Trust Store:** Clients must be configured to trust the CA that signed the server's certificate. For self-signed CAs, clients need to explicitly load the ca.crt.  
  * **Hostname Verification:** Clients must verify that the hostname in the server's certificate matches the hostname they are connecting to (e.g., crossbar\_router).  
  * **pyOpenSSL and Twisted Integration:** Correctly using pyOpenSSL and twisted.internet.ssl.CertificateOptions to create the SSL context for ApplicationRunner. Incorrect configuration can lead to TLS handshake failures or certificate validation errors.  
  * **Docker Volume Mounting:** Ensuring the certs directory is correctly mounted into all relevant Docker containers so that both the Crossbar.io router and the client applications can access their respective certificate files.

## **8\. Future Work / Next Steps**

Given more time, the following improvements would be implemented:

* **Mutual TLS:** Implement client certificate authentication (mutual TLS) for an even stronger security posture, where clients also present their certificates to the router for verification.  
* **Dynamic Certificate Provisioning:** For a production environment, explore solutions for dynamic certificate provisioning and renewal (e.g., using HashiCorp Vault or cert-manager).  
* **Robust Error Handling:** Implement more sophisticated error handling and logging within client applications and the authenticator for better diagnostics, especially for TLS-related issues.  
* **Enhanced RBAC Policies:** Expand the Mock Keystone with more granular RBAC policies and a more complex user/role management system, potentially integrating with a database (e.g., PostgreSQL, MongoDB) for persistent user and role data.  
* **User Interface:** Develop a simple web-based UI for the Publisher and Subscriber clients to provide a visual demonstration of the data flow and authorization.  
* **Real OpenStack Integration:** Replace the Mock Keystone server with actual OpenStack Keystone integration for a production-ready solution.  
* **Advanced WAMP Features:** Explore and implement other WAMP features like RPC registration/calling with arguments, progressive results, and error handling.

## **9\. Conclusion**

This project successfully designed and implemented a WAMP messaging system with OpenStack-based RBAC, significantly enhanced with TLS for secure communication. The architectural components are well-defined, and the core logic for authentication, authorization, and encrypted transport is in place. While persistent challenges with precise Autobahn|Python client configuration for authentication and TLS setup have been encountered, significant progress has been made in understanding the intricacies of WAMP's security features and the specific requirements of the Autobahn library. The lessons learned from debugging these complex interactions are invaluable for future distributed systems development.
