# WAMP-with-OpenStack-Based-RBAC
Secure Pub/Sub Communication over WAMP Middleware with OpenStack-Based RBAC
# Secure Pub/Sub Communication over WAMP Middleware with OpenStack-Inspired RBAC

## 📌 Project Overview

This project implements a secure IIoT middleware using the WAMP protocol (Crossbar.io and Autobahn|Python) with TLS-secured communication, supporting both publish/subscribe and RPC communication. It features a Role-Based Access Control (RBAC) system inspired by OpenStack Keystone.

---

## 📚 Technologies Used

- [Crossbar.io](https://crossbar.io/) (WAMP router)
- [Autobahn|Python](https://github.com/crossbario/autobahn-python)
- [Flask](https://flask.palletsprojects.com/) for mock Keystone API
- JWT for authentication tokens
- TLS (self-signed certs for development)
- SQLite for lightweight storage
- YAML/JSON for policy definitions

---

## 🧱 System Architecture

- WAMP router (Crossbar.io) handles message routing
- TLS-secured WebSocket transport (`wss://`)
- Clients (sensors, dashboards, edge devices) communicate via pub/sub and RPC
- RBAC middleware enforces role-based permissions
- JWT-based authentication integrated with mock Keystone identity service

---

## 📂 Project Structure

