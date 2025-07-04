// oop_deployment.js
// Логика для вкладок и динамического контента ООП

document.addEventListener('DOMContentLoaded', function() {
    const tabForecast = document.getElementById('tab-forecast');
    const tabDeployment = document.getElementById('tab-deployment');
    const tabContent = document.getElementById('oop-tab-content');

    function loadForecast() {
        fetch('/patrol-forecast')
            .then(res => res.text())
            .then(html => {
                tabContent.innerHTML = html;
                // Если потребуется, можно инициализировать обработчики для прогноза патрулей
            });
    }

    function loadDeployment() {
        fetch('/oop/deployment')
            .then(res => res.text())
            .then(html => {
                tabContent.innerHTML = html;
                initDeploymentTab();
            });
    }

    tabForecast.addEventListener('click', function(e) {
        e.preventDefault();
        tabForecast.classList.add('active');
        tabDeployment.classList.remove('active');
        loadForecast();
    });
    tabDeployment.addEventListener('click', function(e) {
        e.preventDefault();
        tabDeployment.classList.add('active');
        tabForecast.classList.remove('active');
        loadDeployment();
    });

    // По умолчанию открыта вторая вкладка (deployment)
    tabDeployment.classList.add('active');
    tabForecast.classList.remove('active');
    loadDeployment();
});

// Логика для вкладки "Расстановка сил"
function initDeploymentTab() {
    const tableBody = document.querySelector('#deployment-table tbody');
    const addRowBtn = document.getElementById('add-row');
    const calculateBtn = document.getElementById('calculate');
    const exportBtn = document.getElementById('export-xlsx');
    let districts = [];

    // Получить районы из API
    fetch('/api/districts')
        .then(res => res.json())
        .then(data => {
            districts = data;
        });

    if (addRowBtn) {
        addRowBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const tr = document.createElement('tr');
            // Столбец 1: select район
            const tdDistrict = document.createElement('td');
            const select = document.createElement('select');
            select.name = 'district';
            districts.forEach(d => {
                const option = document.createElement('option');
                option.value = d.id;
                option.textContent = d.name;
                select.appendChild(option);
            });
            tdDistrict.appendChild(select);
            // Столбец 2: кнопка "выбрать область"
            const tdArea = document.createElement('td');
            const areaBtn = document.createElement('button');
            areaBtn.type = 'button';
            areaBtn.textContent = 'Выбрать область';
            areaBtn.onclick = function() {
                const districtId = select.value;
                enableAreaSelection(districtId);
            };
            tdArea.appendChild(areaBtn);
            tr.appendChild(tdDistrict);
            tr.appendChild(tdArea);
            tableBody.appendChild(tr);
        });
    }

    if (calculateBtn) {
        calculateBtn.addEventListener('click', function(e) {
            e.preventDefault();
            calculateDeployment();
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportDeploymentToXLSX();
        });
    }

    // Инициализация карты, если есть контейнер
    if (document.getElementById('deployment-map')) {
        initDeploymentMap();
    }
}

// --- Карта и выбор области для района ---
let selectedAreas = {}; // {districtId: areaGeometry}

function initDeploymentMap() {
    if (!window.ymaps) return;
    ymaps.ready(function() {
        const map = new ymaps.Map('deployment-map', {
            center: [51.672046, 39.184302],
            zoom: 11
        });
        window.deploymentMap = map;
    });
}

function enableAreaSelection(districtId) {
    if (!window.deploymentMap || !window.ymaps) return;
    const map = window.deploymentMap;
    // Удаляем предыдущий редактор
    if (window.areaEditor) {
        window.areaEditor.stopDrawing();
        window.areaEditor = null;
    }
    // Создаём новый полигон
    const polygon = new ymaps.Polygon([], {}, {
        editorDrawingCursor: "crosshair",
        fillColor: '#00FF0088',
        strokeWidth: 3
    });
    map.geoObjects.add(polygon);
    polygon.editor.startDrawing();
    window.areaEditor = polygon.editor;
    polygon.events.add('editorstatechange', function(e) {
        if (!polygon.editor.state.get('drawing')) {
            // Сохраняем геометрию
            selectedAreas[districtId] = polygon.geometry.getCoordinates();
            alert('Область выбрана для района!');
            polygon.editor.stopDrawing();
            window.areaEditor = null;
        }
    });
}

// --- Обработка кнопки "Рассчитать расстановку" ---
function calculateDeployment() {
    const tableBody = document.querySelector('#deployment-table tbody');
    const rows = tableBody.querySelectorAll('tr');
    const resultDiv = document.getElementById('deployment-result');
    let deploymentData = [];
    rows.forEach(row => {
        const districtId = row.querySelector('select[name="district"]').value;
        const districtName = row.querySelector('select[name="district"] option:checked').textContent;
        const area = window.selectedAreas ? window.selectedAreas[districtId] : null;
        deploymentData.push({ districtId, districtName, area });
    });
    // Пример простой логики: для каждого района 2 пеших и 2 мобильных патруля
    let html = '<h3>Результаты расчёта</h3>';
    html += '<table class="deployment-result-table"><thead><tr><th>Район</th><th>Патрули</th><th>Корректировка</th></tr></thead><tbody>';
    deploymentData.forEach((item, idx) => {
        html += `<tr><td>${item.districtName}</td><td>2 пеших, 2 мобильных</td><td><button type='button' onclick='editPatrol(${idx})'>Изменить</button> <button type='button' onclick='deletePatrol(${idx})'>Удалить</button></td></tr>`;
    });
    html += '</tbody></table>';
    resultDiv.innerHTML = html;
}

function editPatrol(idx) {
    alert('Редактирование патруля №' + (idx+1));
    // Здесь можно реализовать выбор сотрудников из базы и корректировку
}
function deletePatrol(idx) {
    const table = document.querySelector('.deployment-result-table tbody');
    if (table && table.rows[idx]) {
        table.deleteRow(idx);
    }
}

// --- Экспорт в XLSX ---
function exportDeploymentToXLSX() {
    // Собираем данные из таблицы результатов
    const table = document.querySelector('.deployment-result-table');
    if (!table) {
        alert('Сначала рассчитайте расстановку!');
        return;
    }
    let rows = [];
    for (let tr of table.rows) {
        let row = [];
        for (let td of tr.cells) {
            row.push(td.innerText);
        }
        rows.push(row);
    }
    // Отправляем данные на сервер для генерации xlsx
    fetch('/oop/export_xlsx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows })
    })
    .then(res => res.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'deployment.xlsx';
        document.body.appendChild(a);
        a.click();
        a.remove();
    });
}
