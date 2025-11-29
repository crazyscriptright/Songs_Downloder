# Vite Frontend

## Development

```bash
npm install
npm run dev
```

Opens at `http://localhost:3000` with hot reload

## Production Build

```bash
npm run build
```

Creates `dist/` folder ready for deployment

## Deploy to Vercel

```bash
vercel
```

## Deploy to Netlify

```bash
netlify deploy --prod --dir=dist
```

## Environment Variables

- Development: Uses `.env.development`
- Production: Uses `.env.production` or set `VITE_API_URL` in hosting platform
