---
name: add-port
description: Add a port (typing.Protocol) with an in-memory adapter, a real adapter, and a settings-driven factory. Use when a service needs a new external dependency such as storage, a queue, a model, or a third-party API.
---

# Add a port and its adapters

1. Define the port as a `typing.Protocol` next to the other ports. Methods take and return domain types, never vendor types.
2. Write the in-memory adapter first and test the service against it.
3. Write the real adapter. It is the only module that imports the vendor SDK. Test it with the SDK's fake (moto for boto3, `httpx.MockTransport` for HTTP).
4. Add a factory that picks the adapter from settings, cached like `get_settings()`, and a FastAPI dependency that returns it.
5. Add the setting to the settings model with a safe local default (the in-memory or local adapter).
6. Check that no domain or service module imports the vendor package.
