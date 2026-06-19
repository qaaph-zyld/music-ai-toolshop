let currentTool = null;
let uploadedFile = null;
let tools = [];

const els = {
    toolList: document.getElementById('tool-list'),
    toolPanel: document.getElementById('tool-panel'),
    toolTitle: document.getElementById('tool-title'),
    toolDesc: document.getElementById('tool-desc'),
    toolForm: document.getElementById('tool-form'),
    dropZone: document.getElementById('drop-zone'),
    fileInput: document.getElementById('file-input'),
    fileInfo: document.getElementById('file-info'),
    fileName: document.getElementById('file-name'),
    fileStatus: document.getElementById('file-status'),
    progress: document.getElementById('progress'),
    statusText: document.getElementById('status-text'),
    log: document.getElementById('log'),
    logContent: document.getElementById('log-content'),
    downloads: document.getElementById('downloads'),
    downloadList: document.getElementById('download-list'),
    repoInfo: document.getElementById('repo-info'),
};

async function init() {
    try {
        const health = await fetch('/api/health').then(r => r.json());
        if (health.ok && health.repos) {
            const names = Object.keys(health.repos).join(', ');
            els.repoInfo.textContent = `Repos: ${names}`;
        }
    } catch (e) {
        els.repoInfo.textContent = 'Health check failed.';
    }

    tools = await fetch('/api/tools').then(r => r.json());
    renderToolList();
    setupDropZone();
    document.getElementById('open-browser-btn').addEventListener('click', () => window.open('/'));
}

function renderToolList() {
    els.toolList.innerHTML = '';
    for (const tool of tools) {
        const btn = document.createElement('button');
        btn.className = `tool-btn${tool.external ? ' external' : ''}`;
        btn.innerHTML = `<strong>${tool.name}</strong><span>${tool.description}</span>`;
        btn.addEventListener('click', () => selectTool(tool));
        els.toolList.appendChild(btn);
    }
}

function selectTool(tool) {
    currentTool = tool;
    document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
    const index = tools.indexOf(tool);
    if (index >= 0) els.toolList.children[index].classList.add('active');

    els.toolTitle.textContent = tool.name;
    els.toolDesc.textContent = tool.description;
    els.toolPanel.classList.remove('hidden');
    els.toolForm.innerHTML = '';
    els.dropZone.classList.remove('hidden');

    if (tool.external) {
        els.dropZone.classList.add('hidden');
        const p = document.createElement('p');
        p.textContent = 'This tool runs inside the open_DAW desktop app. Click below to open it.';
        els.toolForm.appendChild(p);
        const btn = document.createElement('button');
        btn.className = 'run-btn';
        btn.textContent = 'Launch open_DAW';
        btn.addEventListener('click', () => {
            fetch('/api/launch-opendaw').then(r => r.json()).then(data => {
                alert(data.message || 'Launch not available.');
            });
        });
        els.toolForm.appendChild(btn);
        return;
    }

    const form = document.createElement('div');
    for (const param of tool.params) {
        const field = document.createElement('div');
        field.className = 'field';
        const label = document.createElement('label');
        label.textContent = param.label || param.name;
        field.appendChild(label);
        let input;
        if (param.type === 'select') {
            input = document.createElement('select');
            for (const opt of param.options) {
                const option = document.createElement('option');
                option.value = opt;
                option.textContent = opt;
                if (opt === param.default) option.selected = true;
                input.appendChild(option);
            }
        } else {
            input = document.createElement('input');
            input.type = param.type === 'number' ? 'number' : 'text';
            input.value = param.default || '';
        }
        input.id = `param-${param.name}`;
        input.dataset.name = param.name;
        field.appendChild(input);
        form.appendChild(field);
    }

    const runBtn = document.createElement('button');
    runBtn.className = 'run-btn';
    runBtn.textContent = 'Run Tool';
    runBtn.disabled = !uploadedFile;
    runBtn.id = 'run-btn';
    runBtn.addEventListener('click', () => runTool(runBtn));
    form.appendChild(runBtn);

    els.toolForm.appendChild(form);
}

function setupDropZone() {
    els.dropZone.addEventListener('click', () => els.fileInput.click());
    els.fileInput.addEventListener('change', () => {
        if (els.fileInput.files[0]) uploadFile(els.fileInput.files[0]);
    });

    els.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        els.dropZone.classList.add('dragover');
    });
    els.dropZone.addEventListener('dragleave', () => els.dropZone.classList.remove('dragover'));
    els.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        els.dropZone.classList.remove('dragover');
        if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
    });
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    els.fileStatus.textContent = 'Uploading...';
    try {
        const resp = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.ok) {
            uploadedFile = data;
            els.fileName.textContent = data.filename;
            els.fileStatus.textContent = 'Ready';
            els.fileInfo.classList.remove('hidden');
            const runBtn = document.getElementById('run-btn');
            if (runBtn) runBtn.disabled = false;
        } else {
            els.fileStatus.textContent = data.error || 'Upload failed';
        }
    } catch (e) {
        els.fileStatus.textContent = 'Upload failed';
    }
}

function runTool(runBtn) {
    if (!currentTool || !uploadedFile) return;
    runBtn.disabled = true;
    els.log.classList.remove('hidden');
    els.progress.classList.remove('hidden');
    els.downloads.classList.add('hidden');
    els.logContent.textContent = '';
    els.statusText.textContent = `Running ${currentTool.name}...`;

    const params = new URLSearchParams();
    params.append('path', uploadedFile.path);
    for (const el of els.toolForm.querySelectorAll('input, select')) {
        params.append(el.dataset.name, el.value);
    }

    const url = `/api/run/${currentTool.id}?${params.toString()}`;
    const evtSource = new EventSource(url);

    evtSource.onmessage = (e) => {
        els.logContent.textContent += e.data + '\n';
        els.logContent.scrollTop = els.logContent.scrollHeight;
    };

    evtSource.addEventListener('done', (e) => {
        evtSource.close();
        runBtn.disabled = false;
        els.progress.classList.add('hidden');
        const data = JSON.parse(e.data);
        if (data.error) {
            els.statusText.textContent = 'Failed';
            els.logContent.textContent += `\n[ERROR] ${data.error}\n`;
        } else {
            els.statusText.textContent = 'Done';
            renderDownloads(data.files || []);
        }
    });

    evtSource.onerror = () => {
        evtSource.close();
        runBtn.disabled = false;
        els.progress.classList.add('hidden');
        els.statusText.textContent = 'Connection error';
    };
}

function renderDownloads(files) {
    els.downloadList.innerHTML = '';
    if (files.length === 0) {
        els.downloads.classList.add('hidden');
        return;
    }
    for (const f of files) {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = f.url;
        a.textContent = `${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
        a.setAttribute('download', '');
        li.appendChild(a);
        els.downloadList.appendChild(li);
    }
    els.downloads.classList.remove('hidden');
}

init();
