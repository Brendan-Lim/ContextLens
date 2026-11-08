import {pathToFileURL} from 'node:url';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
export async function launchBrowser() {
  const module = process.env.PLAYWRIGHT_MODULE ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : 'playwright';
  const {chromium} = await import(module);
  const options = {headless: true};
  if (process.env.CHROMIUM_EXECUTABLE) options.executablePath = process.env.CHROMIUM_EXECUTABLE;
  return chromium.launch(options);
}
export async function serve(root) {
  const server = createServer(async (req, res) => {
    try {
      const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
      const target = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
      if (!target.startsWith(path.resolve(root) + path.sep)) throw Error('Path outside fixture');
      const type = {'.html':'text/html','.css':'text/css','.js':'text/javascript'}[path.extname(target)] || 'application/octet-stream';
      const bytes = await readFile(target); res.writeHead(200, {'Content-Type': type}); res.end(bytes);
    } catch { res.writeHead(404); res.end('Not found'); }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  return {url: `http://127.0.0.1:${server.address().port}`, close: () => new Promise(resolve => server.close(resolve))};
}
