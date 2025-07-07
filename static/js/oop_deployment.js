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
                // Выполним встроенные скрипты из загруженного HTML
                tabContent.querySelectorAll('script').forEach(oldScript => {
                    const newScript = document.createElement('script');
                    if (oldScript.src) {
                        // Избегаем повторного подключения Yandex Maps API
                        if (!oldScript.src.includes('api-maps.yandex')) {
                            newScript.src = oldScript.src;
                        } else {
                            // Уже загружено в base.html
                            return;
                        }
                    } else {
                        newScript.textContent = oldScript.textContent;
                    }
                    document.body.appendChild(newScript);
                    // Удаляем, чтобы избежать повторного выполнения при переключении
                    oldScript.remove();
                });
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
            const rowId = 'row_' + (rowCounter++);
            tr.dataset.rowId = rowId;
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
                const key = tr.dataset.rowId;
                enableAreaSelection(key, this);
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
let selectedAreas = {}; // {rowId: areaGeometry}
window.selectedAreas = selectedAreas;
let rowCounter = 0;
let currentPolygon = null;

function initDeploymentMap(retry = 0) {
    console.log('[Map] Attempt initDeploymentMap, retry:', retry);
    if (!window.ymaps || typeof ymaps.ready !== 'function') {
        if (retry < 10) {
            // Подождём загрузки API и попробуем ещё раз
            setTimeout(() => initDeploymentMap(retry + 1), 500);
        } else {
            console.error('Yandex Maps API не загрузился. Карта не будет инициализирована.');
        }
        return;
    }
    ymaps.ready(function() {
        const mapEl = document.getElementById('deployment-map');
        if (!mapEl) return;
        const map = new ymaps.Map(mapEl, {
            center: [51.672046, 39.184302],
            zoom: 11
        });
        window.deploymentMap = map;
        // Обновляем размеры, если контейнер был скрыт
        setTimeout(() => map.container.fitToViewport(), 300);
    });
}

function enableAreaSelection(areaKey, btnEl) {
    if (!window.deploymentMap || !window.ymaps) return;
    const map = window.deploymentMap;
    
    // Удаляем предыдущий полигон
    if (window.currentPolygon) {
        try {
            map.geoObjects.remove(window.currentPolygon);
        } catch(e) {}
    }
    
    // Создаём новый полигон
    const polygon = new ymaps.Polygon([], {}, {
        editorDrawingCursor: "crosshair",
        fillColor: '#00FF0088',
        strokeWidth: 3
    });
    
    map.geoObjects.add(polygon);
    map.behaviors.disable('drag');
    polygon.editor.startDrawing();
    window.currentPolygon = polygon;
    
    polygon.events.add('editorstatechange', function(e) {
        if (!polygon.editor.state.get('drawing')) {
            // Сохраняем геометрию
            selectedAreas[areaKey] = polygon.geometry.getCoordinates();
            
            // Обновляем интерфейс
            const span = document.createElement('span');
            span.textContent = 'Область выбрана';
            span.classList.add('area-chosen');
            btnEl.replaceWith(span);
            
            // Очищаем карту
            map.geoObjects.remove(polygon);
            map.behaviors.enable('drag');
            window.currentPolygon = null;
        }
    });
}

// --- Обработка кнопки "Рассчитать расстановку" ---
function calculateDeployment() {
    // Проверка наличия строк и персонала

    const tableBody = document.querySelector('#deployment-table tbody');
    const rows = tableBody.querySelectorAll('tr');
    const resultDiv = document.getElementById('deployment-result');
    let deploymentData = [];
    rows.forEach(row => {
        const districtId = row.querySelector('select[name="district"]').value;
        const districtName = row.querySelector('select[name="district"] option:checked').textContent;
        const area = window.selectedAreas ? window.selectedAreas[row.dataset.rowId] : null;
        deploymentData.push({ districtId, districtName, area });
    });
        // Берём данные формы
    const form = document.querySelector('#deployment-form');
    const formData = new FormData(form);
    const date = formData.get('date');
    const personnel = parseInt(formData.get('personnel') || '0', 10);
    if (!personnel || personnel<=0){
        alert('Укажите корректное количество личного состава');
        return;
    }

    // Отправляем на сервер
    if (deploymentData.length===0){
        alert('Добавьте хотя бы одну строку с районом');
        return;
    }

    Promise.all([
        fetch('/api/patrol-calc', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, personnel, rows: deploymentData })
        }).then(r=>r.json()),
        fetch('/api/officers').then(r=>r.json())
    ]).then(([result, officers])=>{
        if(result.error){
            alert('Ошибка сервера: '+result.error);
            return;
        }
        renderDeploymentResult(result, officers);
    });
    
}

function renderDeploymentResult(result, officers) {
    const resultDiv = document.getElementById('deployment-result');
    resultDiv.innerHTML = '';

    // Prepare patrols array regardless of backend shape
    const patrolsArr = Array.isArray(result) ? result : (result.patrols || []);
    if (patrolsArr.length === 0) {
        resultDiv.innerHTML = '<h3>Результаты расчёта</h3><p>Нет данных для отображения.</p>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'deployment-result-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Район</th>
                <th>Пешие / Мобильные патрули</th>
                <th>Корректировка</th>
            </tr>
        </thead>
    `;
    const tbody = document.createElement('tbody');

    // patrolsArr уже определён выше

    // --- Logic for unique officer assignment ---
    const availableOfficers = [...officers].sort(() => 0.5 - Math.random());
    let officerAssign_idx = 0;
    console.log(`[Patrols] Initializing with ${availableOfficers.length} available officers.`);
    
    const totalPatrolSlots = patrolsArr.reduce((total, p) => {
        const footCnt = p.footPatrols ?? p.foot_patrols_count ?? 0;
        const mobileCnt = p.mobilePatrols ?? p.mobile_patrols_count ?? 0;
        const mobilePatrolSize = p.mobile_patrol_size || 3;
        return total + (footCnt * 2) + (mobileCnt * mobilePatrolSize);
    }, 0);

    if (totalPatrolSlots > officers.length) {
        alert(`Внимание: для ${totalPatrolSlots} мест в патрулях доступно только ${officers.length} сотрудников. Некоторые сотрудники будут назначены на несколько маршрутов.`);
    }

    const getNextOfficer = () => {
        if (officerAssign_idx < availableOfficers.length) {
            const officer = availableOfficers[officerAssign_idx];
            officerAssign_idx++;
            console.log(`[Patrols] Assigning officer: ${officer.full_name}. Index: ${officerAssign_idx}`);
            return officer;
        }
        const randomOfficer = officers[Math.floor(Math.random() * officers.length)];
        console.warn(`[Patrols] Not enough unique officers. Assigning random officer: ${randomOfficer.full_name}`);
        return randomOfficer;
    };

    patrolsArr.forEach(p => {
        const row = document.createElement('tr');
        const districtCell = document.createElement('td');
        districtCell.textContent = p.districtName;
        row.appendChild(districtCell);

        const patrolsCell = document.createElement('td');

        const createOfficerSelect = (officersList, preselectedOfficer) => {
            const select = document.createElement('select');
            select.innerHTML = '<option value="">-- Не назначен --</option>';
            officersList.forEach(o => {
                select.innerHTML += `<option value="${o.id}">${o.full_name || o.fio}</option>`;
            });
            if (preselectedOfficer) {
                select.value = preselectedOfficer.id;
            }
            return select;
        };

        // Пешие патрули
        const footCnt = p.footPatrols ?? p.foot_patrols_count ?? 0;
        if (footCnt > 0) {
            const footPatrolsContainer = document.createElement('div');
            footPatrolsContainer.className = 'patrol-type-group';
            for (let i = 0; i < footCnt; i++) {
                const patrolGroupDiv = document.createElement('div');
                patrolGroupDiv.className = 'patrol-group';
                patrolGroupDiv.innerHTML = `<strong>Пеший ${i + 1}</strong>`;
                
                const officersDiv = document.createElement('div');
                officersDiv.className = 'patrol-officers';
                officersDiv.appendChild(createOfficerSelect(officers, getNextOfficer()));
                officersDiv.appendChild(createOfficerSelect(officers, getNextOfficer()));
                
                patrolGroupDiv.appendChild(officersDiv);
                footPatrolsContainer.appendChild(patrolGroupDiv);
            }
            patrolsCell.appendChild(footPatrolsContainer);
        }

        // Мобильные патрули
        const mobileCnt = p.mobilePatrols ?? p.mobile_patrols_count ?? 0;
        if (mobileCnt > 0) {
            const mobilePatrolsContainer = document.createElement('div');
            mobilePatrolsContainer.className = 'patrol-type-group';
            for (let i = 0; i < mobileCnt; i++) {
                const patrolGroupDiv = document.createElement('div');
                patrolGroupDiv.className = 'patrol-group';
                patrolGroupDiv.innerHTML = `<strong>Мобильный ${i + 1}</strong>`;

                const officersDiv = document.createElement('div');
                officersDiv.className = 'patrol-officers';
                const patrolSize = p.mobile_patrol_size || 3;
                for (let j = 0; j < patrolSize; j++) {
                    officersDiv.appendChild(createOfficerSelect(officers, getNextOfficer()));
                }
                
                patrolGroupDiv.appendChild(officersDiv);
                mobilePatrolsContainer.appendChild(patrolGroupDiv);
            }
            patrolsCell.appendChild(mobilePatrolsContainer);
        }
        
        row.appendChild(patrolsCell);

        const actionsCell = document.createElement('td');
        actionsCell.innerHTML = `<div class="action-buttons"><button class="btn-edit" onclick="editPatrol(this)">Изменить</button><button class="btn-delete" onclick="deletePatrol(this)">Удалить</button></div>`;
        row.appendChild(actionsCell);

        tbody.appendChild(row);
    });

    const title = document.createElement('h3');
    title.textContent = 'Результаты расчёта';
    resultDiv.appendChild(title);
    table.appendChild(tbody);
    resultDiv.appendChild(table);
}

function editPatrol(btn) {
    const row = btn.closest('tr');
    alert('Редактирование патруля в строке: ' + (row.rowIndex));
}

function deletePatrol(btn) {
    const row = btn.closest('tr');
    if (row) {
        row.remove();
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
