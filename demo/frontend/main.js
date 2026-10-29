const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const testImageSelect = document.getElementById('test-image-select');
const apiForm = document.getElementById('api-form');
const apiUrlInput = document.getElementById('api-url');
const connectionStatus = document.getElementById('connection-status');
const connectionText = document.getElementById('connection-text');
const sampleNote = document.getElementById('sample-note');
const resultsPanel = document.querySelector('.results-panel');
const resultsDiv = document.getElementById('results');
const emptyState = document.getElementById('empty-state');
const spinner = document.getElementById('spinner');
const errorMessage = document.getElementById('error-message');
const apiUrlKey = 'neuroscan-api-url';

const imageElements = {
    real: document.getElementById('real-img'),
    mask: document.getElementById('mask-img'),
    overlay: document.getElementById('overlay-img'),
    mask_gt: document.getElementById('mask-gt-img'),
    overlay_gt: document.getElementById('overlay-gt-img')
};

const imageCards = {
    real: document.getElementById('real-card'),
    mask: document.getElementById('mask-card'),
    overlay: document.getElementById('overlay-card'),
    mask_gt: document.getElementById('mask-gt-card'),
    overlay_gt: document.getElementById('overlay-gt-card')
};

function getApiBaseUrl() {
    const savedUrl = localStorage.getItem(apiUrlKey);
    const configuredUrl = window.APP_CONFIG && window.APP_CONFIG.apiBaseUrl;
    return (savedUrl || configuredUrl || window.location.origin).replace(/\/+$/, '');
}

function setConnectionStatus(state, message) {
    connectionStatus.dataset.state = state;
    connectionText.textContent = message;
}

async function loadSampleImages() {
    testImageSelect.disabled = true;
    testImageSelect.replaceChildren(new Option('Đang tải danh sách ảnh mẫu…', ''));

    try {
        const response = await fetch(`${getApiBaseUrl()}/test-images`);
        if (!response.ok) {
            throw new Error('Không tải được danh sách ảnh mẫu.');
        }

        const files = await response.json();
        testImageSelect.replaceChildren(new Option(
            files.length ? 'Chọn một ảnh mẫu…' : 'Chưa có ảnh mẫu',
            ''
        ));

        for (const filename of files) {
            testImageSelect.add(new Option(filename, filename));
        }

        testImageSelect.disabled = files.length === 0;
        sampleNote.textContent = files.length
            ? `${files.length} ảnh mẫu sẵn sàng để thử nghiệm.`
            : 'Máy chủ chưa có ảnh mẫu.';
    } catch (error) {
        testImageSelect.replaceChildren(new Option('Ảnh mẫu chưa khả dụng', ''));
        sampleNote.textContent = 'Ảnh mẫu sẽ hiển thị khi máy chủ AI đã kết nối.';
    }
}

async function checkApiConnection() {
    setConnectionStatus('checking', 'Đang kiểm tra kết nối…');

    try {
        const response = await fetch(`${getApiBaseUrl()}/health`);
        if (!response.ok) {
            throw new Error('Máy chủ AI chưa phản hồi.');
        }

        const health = await response.json();
        if (health.model_loaded === false) {
            setConnectionStatus('error', 'Máy chủ chưa tải được mô hình');
            return;
        }

        setConnectionStatus('connected', 'Máy chủ AI sẵn sàng');
    } catch (error) {
        setConnectionStatus('error', 'Chưa kết nối máy chủ AI');
    }
}

function clearResults() {
    for (const [key, image] of Object.entries(imageElements)) {
        image.src = '';
        imageCards[key].hidden = true;
    }

    resultsDiv.hidden = true;
    emptyState.hidden = false;
    errorMessage.hidden = true;
    errorMessage.textContent = '';
}

function setLoading(isLoading) {
    resultsPanel.classList.toggle('is-loading', isLoading);
    spinner.setAttribute('aria-hidden', String(!isLoading));
}

function displayResults(data) {
    for (const key of ['real', 'mask', 'overlay']) {
        if (!data[key]) {
            throw new Error('Máy chủ trả về kết quả chưa đầy đủ. Vui lòng thử lại.');
        }
    }

    for (const [key, image] of Object.entries(imageElements)) {
        const source = data[key];
        imageCards[key].hidden = !source;
        image.src = source || '';
    }

    emptyState.hidden = true;
    resultsDiv.hidden = false;
    resultsDiv.style.display = 'grid';
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = false;
    emptyState.hidden = true;
    resultsDiv.hidden = true;
}

async function predict(formData) {
    clearResults();
    setLoading(true);

    try {
        const response = await fetch(`${getApiBaseUrl()}/predict`, {
            method: 'POST',
            body: formData
        });

        if (!(response.headers.get('content-type') || '').includes('application/json')) {
            throw new Error('URL hiện tại không phải backend AI. Hãy kiểm tra URL trong phần cài đặt kết nối.');
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Không thể phân tích ảnh. Vui lòng thử lại.');
        }

        displayResults(data);
    } catch (error) {
        const message = error instanceof TypeError
            ? 'Không thể kết nối máy chủ AI. Hãy kiểm tra URL backend trong phần cài đặt kết nối.'
            : error.message;
        showError(message);
    } finally {
        setLoading(false);
    }
}

function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) {
        showError('Vui lòng chọn một tệp ảnh hợp lệ.');
        return;
    }

    const formData = new FormData();
    formData.append('image', file);
    predict(formData);
}

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        fileInput.click();
    }
});

dropZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    dropZone.classList.remove('dragover');
    handleFile(event.dataTransfer.files[0]);
});

fileInput.addEventListener('change', () => {
    handleFile(fileInput.files[0]);
    fileInput.value = '';
});

testImageSelect.addEventListener('change', () => {
    if (!testImageSelect.value) {
        return;
    }

    const formData = new FormData();
    formData.append('test_image', testImageSelect.value);
    predict(formData);
});

apiForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const value = apiUrlInput.value.trim();

    if (!value) {
        localStorage.removeItem(apiUrlKey);
    } else {
        try {
            const url = new URL(value);
            if (!['http:', 'https:'].includes(url.protocol)) {
                throw new Error('URL không hợp lệ.');
            }
            localStorage.setItem(apiUrlKey, url.origin);
        } catch (error) {
            setConnectionStatus('error', 'URL backend không hợp lệ');
            return;
        }
    }

    apiUrlInput.value = getApiBaseUrl();
    checkApiConnection();
    loadSampleImages();
});

apiUrlInput.value = getApiBaseUrl();
checkApiConnection();
loadSampleImages();
