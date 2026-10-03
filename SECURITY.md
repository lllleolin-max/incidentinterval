# Security and sensitive incident data

The CLI reads a caller-supplied local JSON file and prints a report. It never fetches source references or executes interventions. The SDK does not mutate input, invoke subprocesses or use the network. Bounds restrict input cardinality, bytes and exact branch enumeration; they are not an OS sandbox. Run untrusted models in a process with your own time/memory quota.

Source URLs, labels, conditions, event IDs and constraint evidence may disclose incident details. The tool does **not** redact data; supply sanitized references and avoid credentials/customer payloads. Do not publish reports containing production secrets. JSON source references are untrusted, opaque data; no HTML is rendered or remote location accessed by this package.

Certificate validity means consistency with supplied inequalities/equations. It does not authenticate logs, verify source identities, establish a true cause or approve an operational action. Missing sources and resource-limited results must be reviewed by a human. Model-based prevention is conditional on the AND gating/removal assumptions.

Report vulnerabilities privately through the repository owner's GitHub profile contact or GitHub private vulnerability reporting when available. If no private channel is available, open a minimal issue without sensitive incident material and request a private contact method. Include package/Python version and a synthetic reproducer. No security-response SLA is promised. Disclosure should wait for coordination on an exploitable defect rather than include real customer traces.
