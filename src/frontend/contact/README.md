# contact

Personal bio/link page for `contact.giomartins.dev` — name, bio, real GitHub
projects, and contact links, on one screen with no scroll.

React + TypeScript + Vite, no UI framework or CSS library — the design is
bespoke (`src/index.css`), matching an approved artistic prototype exactly.
Fonts (Fraunces, Archivo) are self-hosted under `public/fonts/`, no external
requests.

## Notable pieces

- `src/hooks/useAuroraCanvas.ts` — the generative duotone canvas background
- `src/hooks/useMagneticName.ts` — splits the hero name into letters that
  nudge away from the cursor with spring physics; this is the one deliberate
  "wow" interaction, the rest of the page stays calm
- All project/contact data is hardcoded in `App.tsx` — this is a static
  personal page, not a dashboard; there's no backend and nothing to fetch

## Local development

```bash
npm install
npm run dev       # http://localhost:5173
npm run build
npm run preview
```

## Deploy

Same pipeline as every other frontend in this repo: pushing a change under
`src/frontend/contact/**` triggers `.github/workflows/deploy-frontends.yml`,
which builds `re.giomartins.dev/contact:latest` and redeploys the `contact`
service (`src/infra/utils.yml`, host port `8078`) via Dockhand.

**Not covered by this repo**: pointing the `contact.giomartins.dev` DNS
record / reverse proxy at that container. Every other `*.giomartins.dev`
subdomain is routed by infra that isn't tracked here (no Traefik/Caddy config
found in `src/infra/`) — wire this one up the same way the others are.
