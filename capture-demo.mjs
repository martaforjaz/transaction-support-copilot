import { spawn } from 'node:child_process';
import { mkdtemp, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

const profile = await mkdtemp(join(tmpdir(), 'copilot-edge-'));
const edge = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const browser = spawn(edge, ['--headless', '--disable-gpu', '--no-first-run',
  '--remote-debugging-port=9617', '--window-size=1000,740', '--user-data-dir=' + profile, 'about:blank'],
  {stdio: 'ignore', windowsHide: true});
let socket;
try {
  let page;
  for (let i = 0; i < 30 && !page; i++) {
    try { page = (await (await fetch('http://127.0.0.1:9617/json/list')).json()).find(item => item.type === 'page'); }
    catch { await delay(200); }
  }
  if (!page) throw Error('Could not connect to Edge.');
  socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, {once:true});
    socket.addEventListener('error', reject, {once:true});
  });
  let sequence = 0;
  const command = (method, params) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const listener = event => {
      const data = JSON.parse(event.data);
      if (data.id !== id) return;
      socket.removeEventListener('message', listener);
      if (data.error) reject(Error(data.error.message)); else resolve(data.result);
    };
    socket.addEventListener('message', listener);
    socket.send(JSON.stringify({id, method, params}));
  });
  const js = expression => command('Runtime.evaluate', {expression, returnByValue:true}).then(x => x.result.value);
  await command('Emulation.setDeviceMetricsOverride', {width:1000,height:740,deviceScaleFactor:1,mobile:false});
  await command('Page.navigate', {url:'http://127.0.0.1:8765/'});
  for (let i = 0; i < 30 && !(await js('Boolean(document.querySelector("form"))')); i++) await delay(200);
  for (const [name, question, expected] of [
    ['decided', 'Why is TX-107 still pending?', 'Decision already recorded'],
    ['pending', 'Why is TX-104 still pending?', 'Pending with no attempts'],
    ['review', 'Why is this transaction still pending?', 'Missing transaction reference'],
  ]) {
    await js(`document.querySelector('#question').value = ${JSON.stringify(question)}; document.querySelector('form').requestSubmit()`);
    let heading;
    for (let i = 0; i < 30 && heading !== expected; i++) {
      await delay(100);
      heading = await js('document.querySelector("#result").hidden ? "" : document.querySelector("#title").textContent');
    }
    if (heading !== expected) throw Error('Unexpected demo result: ' + heading);
    const {data} = await command('Page.captureScreenshot', {format:'png'});
    await writeFile('figures/demo-' + name + '.png', Buffer.from(data, 'base64'));
  }
} finally {
  socket?.close();
  browser.kill();
}
