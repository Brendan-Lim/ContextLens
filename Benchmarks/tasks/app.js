const id = new URLSearchParams(location.search).get('task') || '01';
const app = document.querySelector('#app');
const heading = '<header><div><small>LENSBOARD / WORKSPACE</small><h1>Project overview</h1></div><span>Local fixture</span></header>';
const views = {
 '01': '<section class="dialog"><h2>Publish changes?</h2><p>Your team will see the latest version.</p><div class="actions"><button id="confirm">Confirm</button></div></section>',
 '02': '<div class="cards"><div class="card">Activity</div><div class="card">Members</div><div class="card">Storage</div></div>',
 '03': '<aside class="sidebar">Lensboard<br><br>Overview<br><br>Projects</aside><main class="content"><h2>Workspace content</h2><p>Content should remain fully readable beside the sidebar.</p></main>',
 '04': '<button id="toggle">Filter projects</button><div class="dropdown" hidden><label>Search<input id="search" placeholder="Project name"></label></div>',
 '05': '<nav class="mobile-nav"><a href="#home">Home</a><a href="#projects">Projects</a><a href="#members">Members</a><a href="#settings">Settings</a></nav>',
 '06': '<div role="tablist"><button class="tab active" id="overview">Overview</button> <button class="tab" id="activity">Activity</button></div><p id="tab-content">Overview panel</p>',
 '07': '<button class="focus-target" id="keyboard-action">Create project</button>',
 '08': '<form><label>Email<input id="email" type="text"></label><button id="submit">Save</button><p class="error" role="alert">Enter a valid email address.</p></form>',
 '09': '<section class="dialog scroll-dialog"><h2>Terms preview</h2><div class="long-copy">Long preview content</div><button id="accept">Accept</button></section>',
 '10': '<p>Team members</p><div class="count" id="count">0</div><button id="increment">Add member</button>'
};
app.innerHTML = `<div class="shell">${heading}${views[id] || views['01']}</div>`;
if(id === '04') {
 const dropdown = document.querySelector('.dropdown');
 document.querySelector('#toggle').onclick = e => { e.stopPropagation(); dropdown.hidden = !dropdown.hidden; };
 document.addEventListener('click', () => dropdown.hidden = true);
}
if(id === '06') document.querySelectorAll('.tab').forEach(b => b.onclick = () => {
 document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
 b.classList.add('active'); document.querySelector('#tab-content').textContent = b.textContent + ' panel';
});
if(id === '08') document.querySelector('form').onsubmit = e => { e.preventDefault(); const invalid = !document.querySelector('#email').value.includes('@'); document.querySelector('.error').style.display = invalid ? 'none' : 'none'; };
if(id === '10') { let count = 0; document.querySelector('#increment').onclick = () => { count += 1; }; }
