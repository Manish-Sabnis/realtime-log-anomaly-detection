# Log Event Schema


## This document defines the structure of a single log event accepted by the log anomaly detection system. All components of the system assume logs conform to this schema.

### What is a log event?
- A log event represents one atomic observation emitted by a service at a specific point in time. Each log event is processed independently and later aggregated for anomaly detection.

### Log Event Fields (Core of the File)
`timestamp`
- Type: string
- Format: ISO 8601 (UTC)
- Description: Time at which the log event was generated.

`service_name`
- Type: string
- Description: Logical name of the service emitting the log (e.g., auth-service, payment-service).

`host`
- Type: string
- Description: Identifier of the host or container where the log originated.

`log_level`
- Type: string
- Allowed values: DEBUG, INFO, WARN, ERROR
- Description: Severity level of the log event.

`message`
- Type: string
- Description: Human-readable description of the event. This field contains variable information and is the primary input for log parsing and anomaly detection.

### Example Log Event (Non-Negotiable)
`{` <br>
  `"timestamp": "2026-02-07T14:23:11Z",` <br>
  `"service_name": "auth-service",` <br>
  `"host": "localhost",` <br>
  `"log_level": "ERROR",` <br>
  `"message": "Failed login attempt for user_id=12345 from ip=192.168.1.10"` <br>
`}`

### Non-goals
- This schema does not attempt to capture all possible log formats
- Structured fields inside the message are not required.
- Multi-line logs and stack traces are not supported in the initial version.


