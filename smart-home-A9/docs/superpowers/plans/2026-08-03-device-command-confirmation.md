# Device Command Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all 17 simulators register capabilities, acknowledge commands, and persist only device-confirmed states.

**Architecture:** Add a small command ledger and device-connection metadata to SQLite. The backend emits commands with UUIDs and reconciles ACK messages; simulators inherit protocol handling from BaseDevice and each controller declares its valid capabilities.

**Tech Stack:** Python 3.11, FastAPI, SQLite, Paho MQTT, pytest.

---

### Task 1: Database and command-ledger contract

**Files:**
- Modify: `cloud/backend/app/database/init_db.py`
- Modify: `cloud/backend/tests/test_devices.py`

- [ ] Write failing tests for schema migration, pending command persistence, ACK reconciliation, and timeout handling.
- [ ] Implement additive schema migration and command ledger helpers.
- [ ] Run the focused backend tests.

### Task 2: Backend MQTT registration and acknowledgement

**Files:**
- Create: `cloud/backend/app/services/device_protocol.py`
- Modify: `cloud/backend/app/main.py`
- Modify: `cloud/backend/app/services/device_command.py`
- Modify: `cloud/backend/app/services/device_view.py`
- Modify: `cloud/backend/tests/test_mqtt.py`
- Modify: `cloud/backend/tests/test_devices.py`

- [ ] Write failing tests for hello, heartbeat, ACK success, ACK failure, and confirmed-only status updates.
- [ ] Implement protocol parsing, capability validation, command UUID generation, and ACK reconciliation.
- [ ] Run focused tests and the backend suite.

### Task 3: Shared simulator protocol

**Files:**
- Modify: `cloud/simulators/base_device.py`
- Create: `cloud/simulators/tests/test_device_protocol.py`

- [ ] Write failing tests for hello, heartbeat, command ID propagation, success ACK, and rejected command ACK.
- [ ] Implement reusable device identity, capabilities, heartbeat, and acknowledgement helpers.
- [ ] Run simulator tests.

### Task 4: Complete the 17 device behaviours

**Files:**
- Modify: `cloud/simulators/temperature_sensor.py`
- Modify: `cloud/simulators/humidity_sensor.py`
- Modify: `cloud/simulators/pir_sensor.py`
- Modify: `cloud/simulators/light_controller.py`
- Modify: `cloud/simulators/ac_controller.py`
- Modify: `cloud/simulators/door_lock.py`
- Modify: `cloud/simulators/curtain_controller.py`
- Modify: `cloud/simulators/humidifier_controller.py`
- Modify: `cloud/simulators/simulator_manager.py`
- Modify: `cloud/simulators/tests/test_device_protocol.py`

- [ ] Add failing per-device tests for every declared action and invalid-command rejection.
- [ ] Add sensor configuration controls, actuator validation, curtain movement state, and humidifier water level.
- [ ] Run simulator tests.

### Task 5: Integration verification

**Files:**
- Modify: `cloud/backend/tests/test_integration.py`
- Modify: `cloud/backend/tests/test_scenes.py`

- [ ] Write failing end-to-end tests proving commands stay pending before ACK and become acknowledged after ACK.
- [ ] Verify scenes and rules create the same command records.
- [ ] Run backend tests, simulator tests, Docker compose smoke test, and document results.
