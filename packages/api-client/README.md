# `@mindloom/api-client`

This directory is the boundary for the TypeScript API client generated from the
FastAPI OpenAPI document.

Do not hand-maintain copies of backend request or response models here. Until an
OpenAPI generation command is added, the dashboard's existing API adapter remains
the active client. When generation is introduced, both the dashboard and extension
should consume the generated package from this directory.
