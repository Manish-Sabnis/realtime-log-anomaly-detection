# External Web Applications

This directory contains all externally facing web applications for the
Real-Time Log Anomaly Detection system.

The external layer is responsible for:
- User interaction
- Visualization of logs and system behavior
- Displaying ML-based anomaly detection results

---

## Overview

The system consists of two independent web applications:

### 1. **SaaS Web Application**

- Represents a real-world cloud-based product
- Users interact with the system normally (login, actions, transactions)
- Internally backed by multiple microservices:
  - auth-service
  - api-gateway
  - payment-service
  - notification-service
- Service logs are generated automatically as part of normal operations
- Users are not exposed to logging or anomaly detection internals

### 2. **Logs & Anomaly Dashboard**

- Used by internal or administrative users
- Displays raw logs from all services
- Displays ML model responses (anomaly flags, scores)
- Provides filtering, monitoring, and analysis capabilities

Both applications communicate with backend services via REST APIs.

---

## High-Level Workflow

1. Microservices generate logs (auth, payment, notification, api-gateway)
2. Logs are sent to the backend through REST APIs
3. Backend stores logs in the database
4. Backend forwards logs to an ML inference service
5. ML service returns anomaly prediction and score
6. Backend stores ML response linked to the corresponding log
7. Frontend dashboards fetch and display logs and predictions

---

## Tech Stack

### Frontend
- React
- TypeScript
- Tailwind CSS

### Backend
- Java 17
- Spring Boot
- Spring Web (REST APIs)
- Spring Data JPA
- PostgreSQL

### ML Integration


### Deployment
- Docker
- Render
- Cloud-compatible microservice architecture

---

## Anomaly Injection Overview

To evaluate the effectiveness of the anomaly detection system,
controlled abnormal scenarios are introduced during testing.
These anomalies simulate real-world failure and performance issues
and are primarily analyzed using the logs and monitoring dashboard.