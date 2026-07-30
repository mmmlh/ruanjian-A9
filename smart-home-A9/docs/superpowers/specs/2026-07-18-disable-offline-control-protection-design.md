# Disable Offline Control Protection

## Goal

Allow commands to be dispatched for devices reported as offline while retaining
the offline status shown throughout the app.

## Scope

- In `DeviceRemotePage.ets`, control buttons remain disabled only while a
  command is already in progress. Offline status does not disable them.
- The remote page continues to show whether the device is online or offline.
- In `device_command.py`, remove the freshness-based `device_offline` command
  rejection. All existing entity validation, action validation, command
  decoding, state updates, and MQTT dispatch behavior remain unchanged.

## Non-goals

- Do not alter how online status is derived or displayed.
- Do not remove MQTT dispatch failure handling.
- Do not modify unrelated dashboard or device-management behavior.

## Verification

- Update the remote-page regression test to require busy-state protection only
  and to reject the old offline-control warning.
- Add a backend regression test proving an otherwise valid command is accepted
  for an offline device.
- Run the targeted tests, then the repository test suite.
