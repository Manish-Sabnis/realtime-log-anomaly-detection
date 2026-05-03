# SaaS Web Application

This module represents a real-world, user-facing SaaS product built on
top of a microservice-based backend.

The purpose of this application is to simulate normal user behavior in
a production system, which in turn generates realistic service logs
used for monitoring and anomaly detection.

---

## Scope

- End-user interaction (login, actions, transactions)
- Business workflows that trigger backend microservices
- No direct exposure to logs, monitoring, or ML systems

---

## Architecture

The SaaS application is internally backed by the following services:

- auth-service  
- api-gateway  
- payment-service  
- notification-service  

User actions flow through these services, and logs are generated
automatically as part of normal operations.

---

## Tech Stack

### Frontend
- React
- TypeScript
- Tailwind CSS

### Backend
- Java Spring Boot
- REST APIs

---

## Design Principle

This application intentionally hides all observability and anomaly
detection mechanisms from end users to reflect real-world SaaS behavior.
