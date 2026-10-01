# End-to-end tests

Cross-component browser journeys belong here. The first Playwright journey should
prove the required vertical slice:

1. the user explicitly starts collection;
2. the extension captures an eligible page;
3. FastAPI persists it;
4. the dashboard displays it after reload.

The current API and WebSocket journeys remain in `scripts/` because they are Python
verification utilities rather than browser tests.
