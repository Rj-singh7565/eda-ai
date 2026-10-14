const path = require('path');
const { startServer } = require('next/dist/server/lib/start-server');

const dir = path.resolve(__dirname);
const port = parseInt(process.env.PORT || '3000', 10);
const hostname = process.env.HOSTNAME || 'localhost';

startServer({
  dir,
  port,
  allowRetry: false,
  isDev: true,
  hostname,
}).then(() => {
  console.log(`[Frontend] Next.js dev server ready on http://${hostname}:${port}`);
}).catch((err) => {
  console.error('[Frontend] Failed to start Next.js dev server:', err);
  process.exit(1);
});
