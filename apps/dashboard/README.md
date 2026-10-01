# Mindloom dashboard

The dashboard now uses the FastAPI service and the Chrome extension instead of fixture data.

## Dashboard-only fixture mode

To design the dashboard without PostgreSQL, FastAPI, or the Chrome extension, create
`.env.local` in this directory with:

```env
VITE_USE_FIXTURES=true
```

Then run `pnpm dev:dashboard` from the repository root. Fixture mode supplies local
sample workspaces, saved pages, and collection errors. Restart Vite after changing
the environment file. Tracking still requires the Chrome extension.

1. Copy `.env.example` to `.env.local`.
2. Load `apps/extension` as an unpacked Chrome extension.
3. Put the locally assigned extension ID in `VITE_EXTENSION_ID`.
4. Start the API at `http://127.0.0.1:8000` and run `pnpm dev` here.

The first successful API connection creates `My Research` when no workspace exists. **Start Tracking** is the explicit collection action: it connects to the extension, requests content from eligible open tabs, and sends each successful extraction to the active workspace.

## Development

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
