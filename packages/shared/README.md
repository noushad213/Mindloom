# `@mindloom/shared`

This directory is reserved for browser-safe TypeScript code genuinely shared by
the dashboard and extension, such as protocol constants or small pure utilities.

Backend data contracts do not belong here; those must be generated from FastAPI's
OpenAPI schema into `packages/api-client`.
