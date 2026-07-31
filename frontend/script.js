// Leer parámetros de URL para backend y admin key
const urlParams = new URLSearchParams(window.location.search);
const BACKEND_URL = "https://powerlifting-app-7xws.onrender.com"
const API_URL = `${BACKEND_URL}/api`;
const ADMIN_KEY = urlParams.get('admin_key') || null;

// Estado global
let allConcursantes = [];
let allLevantamientos = [];
let currentRankingFilter = 'all';
let currentCompetitionFilter = 'all';
let currentSort = 'ipf';
let pendingCompetitionEntries = [];
// (BACKEND_URL, API_URL y ADMIN_KEY ya inicializados arriba)

// ==================== FUNCIONES DE INICIALIZACIÓN ====================

document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
    setInterval(loadAllData, 30000); // Actualizar cada 30 segundos
    enforceAdminUI();
});

function enforceAdminUI() {
    // Oculta elementos marcados como admin-only si no hay ADMIN_KEY
    if (!ADMIN_KEY) {
        document.querySelectorAll('[data-admin-only]').forEach(el => el.style.display = 'none');
    } else {
        // si admin_key está presente, mostrar elementos ocultos
        document.querySelectorAll('[data-admin-only]').forEach(el => el.style.display = '');
    }
}

// Ejecutar control UI inmediatamente
enforceAdminUI();

async function loadAllData() {
    await loadConcursantes();
    await loadLevantamientos();
    await loadStats();
    await loadTopPerformers();
    await loadCompetitions();
    await loadResults();
    await loadRecords();
    await loadTeams();
}

// ==================== CARGA DE DATOS ====================

async function loadConcursantes() {
    try {
        const response = await fetch(`${API_URL}/concursantes`);
        if (!response.ok) throw new Error('Error al cargar concursantes');
        allConcursantes = await response.json();
        populateLevantamientoConcursanteSelect();
        populateCompetitionEntryConcursanteSelect();
        displayConcursantes();
    } catch (error) {
        console.error('Error:', error);
        showToast('Error al cargar concursantes', 'error');
    }
}

async function loadLevantamientos() {
    try {
        const response = await fetch(`${API_URL}/levantamientos`);
        if (!response.ok) throw new Error('Error al cargar levantamientos');
        allLevantamientos = await response.json();
    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/estadisticas`);
        if (!response.ok) throw new Error('Error al cargar estadísticas');
        const stats = await response.json();
        
        document.getElementById('stat-concursantes').textContent = stats.total_concursantes;
        document.getElementById('stat-competiciones').textContent = stats.total_competiciones;
        document.getElementById('stat-levantamientos').textContent = stats.total_levantamientos;
        document.getElementById('stat-mejor-ipf').textContent = stats.mejor_ipf.toFixed(2);
    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadTopPerformers() {
    try {
        const response = await fetch(`${API_URL}/ranking`);
        if (!response.ok) throw new Error('Error al cargar ranking');
        const ranking = await response.json();
        
        const top5 = ranking.slice(0, 5);
        const tbody = document.querySelector('#top-performers-table tbody');
        tbody.innerHTML = '';
        
        top5.forEach((performer, index) => {
            const row = `
                <tr>
                    <td><strong>${index + 1}</strong></td>
                    <td>${performer.nombre}</td>
                    <td>${performer.categoria_peso} kg (${performer.sexo})</td>
                    <td>${performer.total}</td>
                    <td><span style="color: #e74c3c; font-weight: bold;">${performer.ipf_score.toFixed(2)}</span></td>
                </tr>
            `;
            tbody.innerHTML += row;
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadResults() {
    try {
        const response = await fetch(`${API_URL}/ranking`);
        if (!response.ok) throw new Error('Error al cargar resultados');
        const results = await response.json();
        const tbody = document.querySelector('#results-table tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        results.slice(0, 10).forEach((item, index) => {
            const row = `
                <tr>
                    <td>${index + 1}</td>
                    <td>${item.nombre}</td>
                    <td>${item.categoria_peso} kg</td>
                    <td>${item.sentadilla}</td>
                    <td>${item.press_banca}</td>
                    <td>${item.peso_muerto}</td>
                    <td><strong>${item.total}</strong></td>
                    <td>${item.ipf_score.toFixed(2)}</td>
                </tr>
            `;
            tbody.innerHTML += row;
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// ==================== DISPLAY FUNCTIONS ====================

function displayConcursantes() {
    const grid = document.getElementById('concursantes-grid');
    grid.innerHTML = '';
    
    allConcursantes.forEach(concursante => {
        const levantamientos = allLevantamientos.filter(l => l.concursante_id === concursante.id);
        const mejorIPF = levantamientos.length > 0 
            ? Math.max(...levantamientos.map(l => l.ipf_score))
            : 0;
        const photoSrc = concursante.photo_url ? (BACKEND_URL + concursante.photo_url) : '';
        
        const card = `
            <div id="concursante-card-${concursante.id}" class="concursante-card clickable-participations" onclick="viewCompetitionsByConcursante(${concursante.id})" title="Clic para ver participaciones">
                <h3>${concursante.nombre}</h3>
                ${photoSrc ? `<img src="${photoSrc}" alt="foto" style="width:80px;height:100px;object-fit:cover;border-radius:6px;margin-bottom:10px;">` : ''}
                <div class="concursante-info">
                    <p><strong>Edad:</strong> ${concursante.edad} años</p>
                    <p><strong>Peso:</strong> ${concursante.peso_corporal} kg</p>
                    <p><strong>Sexo:</strong> ${concursante.sexo === 'M' ? 'Masculino' : 'Femenino'}</p>
                    <p><strong>Categoría:</strong> ${concursante.categoria_peso} kg</p>
                    <p><strong>Club:</strong> ${concursante.club || 'N/A'}</p>
                    <p><strong>Ciudad:</strong> ${concursante.ciudad || 'N/A'}</p>
                    <p><strong>Desde:</strong> ${concursante.ano_inicio || 'N/A'}</p>
                    <p><strong>Levantamientos:</strong> ${levantamientos.length}</p>
                    ${mejorIPF > 0 ? `<span class="concursante-badge">Mejor IPF: ${mejorIPF.toFixed(2)}</span>` : ''}
                </div>
            </div>
        `;
        grid.innerHTML += card;
    });
}

async function viewCompetitionsByConcursante(concursanteId) {
    try {
        const resp = await fetch(`${API_URL}/levantamientos/concursante/${concursanteId}`);
        if (!resp.ok) throw new Error('No se pudieron cargar los levantamientos del concursante');
        const lifts = await resp.json();
        const compIds = [...new Set(lifts.map(l => l.competicion_id).filter(Boolean))];
        if (compIds.length === 0) {
            showToast('Este atleta no tiene participaciones registradas en competiciones.', 'info');
            return;
        }

        // Obtener datos de cada competición
        const competitions = [];
        for (const id of compIds) {
            try {
                const r = await fetch(`${API_URL}/competiciones/${id}`);
                if (!r.ok) continue;
                const c = await r.json();
                competitions.push(c);
            } catch (e) { console.warn('Error cargando competencia', id, e); }
        }

        // Mostrar en la pestaña competencias
        switchTab('competencias');
        const list = document.getElementById('competitions-list');
        const summary = document.getElementById('competition-history-summary');
        if (summary) summary.innerHTML = `
            <div class="history-pill">
                <span>Participaciones encontradas</span>
                <strong>${competitions.length}</strong>
            </div>
            <div class="history-pill">
                <span>Atleta</span>
                <strong>${allConcursantes.find(a=>a.id===concursanteId)?.nombre || 'N/A'}</strong>
            </div>
        `;
        if (list) {
            list.innerHTML = '';
            competitions.forEach(c => {
                const card = document.createElement('article');
                card.className = 'info-card highlighted-competition';
                const competitionDate = c.fecha ? new Date(c.fecha) : null;
                const year = competitionDate ? competitionDate.getFullYear() : 'N/A';
                card.innerHTML = `
                    <span class="competition-year">${year}</span>
                    <h3>${c.nombre}</h3>
                    <p><strong>Fecha:</strong> ${competitionDate ? competitionDate.toLocaleDateString() : 'Sin fecha'}</p>
                    <p><strong>Ubicación:</strong> ${c.ubicacion}</p>
                    <p>${c.descripcion || ''}</p>
                    <button class="btn-submit soft competition-detail-btn" type="button" onclick="loadCompetitionDetail(${c.id})">Ver detalle</button>
                `;
                list.appendChild(card);
            });
        }
    } catch (err) {
        console.error(err);
        showToast('Error al obtener participaciones', 'error');
    }
}

// ==================== NAVEGACIÓN ====================

function switchTab(tabName) {
    // Ocultar todos los tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remover active de botones
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Mostrar tab activo
    document.getElementById(tabName).classList.add('active');
    
    // Marcar botón como activo (si fue llamado desde un evento)
    try {
        if (typeof event !== 'undefined' && event.target) event.target.classList.add('active');
    } catch (e) { /* noop */ }
    
    // Cargar datos específicos según el tab
    if (tabName === 'ranking') {
        loadRanking('all');
    } else if (tabName === 'records') {
        loadRecords();
    } else if (tabName === 'resultados') {
        loadResults();
    } else if (tabName === 'competencias') {
        loadCompetitions();
    }
}

function viewConcursanteFromCompetition(id) {
    const atleta = allConcursantes.find(c => c.id === id);
    if (!atleta) {
        showToast('Atleta no encontrado', 'error');
        return;
    }
    switchTab('atletas');
    setTimeout(() => {
        const search = document.getElementById('search-input');
        if (search) {
            search.value = atleta.nombre;
            filterConcursantes();
        }
        const card = document.getElementById(`concursante-card-${id}`);
        if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            card.style.transition = 'background-color 0.3s';
            card.style.backgroundColor = '#fff8c4';
            setTimeout(() => { card.style.backgroundColor = 'transparent'; }, 1200);
        }
    }, 200);
}

// ==================== RANKING ====================

function filterRanking(category) {
    currentRankingFilter = category;
    
    // Actualizar botones activos
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    loadRanking(category);
}

async function loadRanking(category) {
    try {
        let url = `${API_URL}/ranking`;
        if (category !== 'all') {
            url += `/${category}`;
        }
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Error al cargar ranking');
        const ranking = await response.json();
        
        const tbody = document.querySelector('#ranking-table tbody');
        tbody.innerHTML = '';
        
        ranking.forEach((item, index) => {
            const row = `
                <tr>
                    <td>${index + 1}</td>
                    <td>${item.nombre}</td>
                    <td>${item.sexo === 'M' ? 'Masculino' : 'Femenino'}</td>
                    <td>${item.categoria_peso} kg</td>
                    <td>${item.sentadilla}</td>
                    <td>${item.press_banca}</td>
                    <td>${item.peso_muerto}</td>
                    <td><strong>${item.total}</strong></td>
                    <td><span style="color: #e74c3c; font-weight: bold;">${item.ipf_score.toFixed(2)}</span></td>
                </tr>
            `;
            tbody.innerHTML += row;
        });
    } catch (error) {
        console.error('Error:', error);
        showToast('Error al cargar ranking', 'error');
    }
}

// ==================== AGREGAR CONCURSANTE ====================

async function addConcursante(event) {
    event.preventDefault();
    
    const concursante = {
        nombre: document.getElementById('nombre').value,
        edad: parseInt(document.getElementById('edad').value),
        peso_corporal: parseFloat(document.getElementById('peso_corporal').value),
        sexo: document.getElementById('sexo').value,
        categoria_peso: document.getElementById('categoria_peso').value,
        club: document.getElementById('club').value || '',
        ciudad: document.getElementById('ciudad').value || '',
        ano_inicio: parseInt(document.getElementById('ano_inicio').value) || new Date().getFullYear()
    };
    
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (ADMIN_KEY) headers['x-admin-key'] = ADMIN_KEY;
        const response = await fetch(`${API_URL}/concursantes`, {
            method: 'POST',
            headers,
            body: JSON.stringify(concursante)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al agregar concursante');
        }
        
        showToast('¡Concursante registrado exitosamente!', 'success');
        document.getElementById('form-concursante').reset();
        const created = await response.json();
        // Si se subió foto, enviarla
        const photoInput = document.getElementById('photo');
        if (photoInput && photoInput.files && photoInput.files.length > 0) {
            const form = new FormData();
            form.append('file', photoInput.files[0]);
            try {
                const photoHeaders = {};
                if (ADMIN_KEY) photoHeaders['x-admin-key'] = ADMIN_KEY;
                await fetch(`${API_URL.replace('/api','')}/api/concursantes/${created.id}/photo`, {
                    method: 'POST',
                    headers: photoHeaders,
                    body: form
                });
            } catch (err) { console.error('Error subiendo foto', err); }
        }
        await loadAllData();
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Error al registrar concursante', 'error');
    }
}

async function loadCompetitions() {
    try {
        const response = await fetch(`${API_URL}/competiciones?desde=2024`);
        if (!response.ok) return;
        const comps = await response.json();
        const sel = document.getElementById('competition-filter');
        const levantamientoCompetitionSelect = document.getElementById('levantamiento_competicion_id');
        const list = document.getElementById('competitions-list');
        const summary = document.getElementById('competition-history-summary');
        const detail = document.getElementById('competition-detail');
        if (sel) sel.innerHTML = '<option value="all">Todas</option>';
        if (levantamientoCompetitionSelect) levantamientoCompetitionSelect.innerHTML = '';
        if (list) list.innerHTML = '';
        if (detail) detail.innerHTML = '<article class="info-card competition-detail-empty"><h3>Selecciona una competencia</h3><p>Haz clic en ver detalle para revisar atletas, levantamientos y mejor IPF.</p></article>';
        if (summary) {
            const years = [...new Set(comps
                .map(c => c.fecha ? new Date(c.fecha).getFullYear() : null)
                )];
                const latest = comps[0]?.fecha ? new Date(comps[0].fecha).toLocaleDateString() : 'Sin registros';
            summary.innerHTML = `
                <div class="history-pill">
                    <span>Total desde 2024</span>
                    <strong>${comps.length}</strong>
                </div>
                <div class="history-pill">
                    <span>Última competencia</span>
                    <strong>${latest}</strong>
                </div>
                <div class="history-pill">
                    <span>Años registrados</span>
                    <strong>${years.join(', ') || 'N/A'}</strong>
                </div>
            `;
        }

        if (list && comps.length === 0) {
            list.innerHTML = '<article class="info-card"><h3>Sin competiciones registradas</h3><p>Cuando agregues eventos desde 2024, aparecerán aquí en orden cronológico.</p></article>';
            return;
        }

        comps.forEach(c => {
            if (sel) {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = `${c.nombre} (${new Date(c.fecha).toLocaleDateString()})`;
                sel.appendChild(opt);
            }
            if (levantamientoCompetitionSelect) {
                const option = document.createElement('option');
                option.value = c.id;
                option.textContent = c.nombre;
                levantamientoCompetitionSelect.appendChild(option);
            }
            if (list) {
                const card = document.createElement('article');
                card.className = 'info-card';
                const competitionDate = c.fecha ? new Date(c.fecha) : null;
                const year = competitionDate ? competitionDate.getFullYear() : 'N/A';
                card.innerHTML = `
                    <span class="competition-year">${year}</span>
                    <h3>${c.nombre}</h3>
                    <p><strong>Fecha:</strong> ${competitionDate ? competitionDate.toLocaleDateString() : 'Sin fecha'}</p>
                    <p><strong>Ubicación:</strong> ${c.ubicacion}</p>
                    <p>${c.descripcion || 'Competencia oficial registrada en la plataforma.'}</p>
                    <button class="btn-submit soft competition-detail-btn" type="button" onclick="loadCompetitionDetail(${c.id})">Ver detalle</button>
                `;
                list.appendChild(card);
            }
        });

        if (comps.length > 0) {
            loadCompetitionDetail(comps[0].id);
        }
    } catch (err) {
        console.error(err);
    }
}

function populateLevantamientoConcursanteSelect() {
    const select = document.getElementById('levantamiento_concursante_id');
    if (!select) return;

    const currentValue = select.value;
    select.innerHTML = '';

    allConcursantes.forEach(concursante => {
        const option = document.createElement('option');
        option.value = concursante.id;
        option.textContent = concursante.nombre;
        select.appendChild(option);
    });

    if (currentValue) {
        select.value = currentValue;
    }
}

function populateCompetitionEntryConcursanteSelect() {
    const select = document.getElementById('entry_concursante_id');
    if (!select) return;

    const currentValue = select.value;
    select.innerHTML = '<option value="">Selecciona atleta</option>';

    allConcursantes.forEach(concursante => {
        const option = document.createElement('option');
        option.value = concursante.id;
        option.textContent = `${concursante.nombre} (${concursante.categoria_peso} kg)`;
        select.appendChild(option);
    });

    if (currentValue) select.value = currentValue;
}

function toggleCompetitionEntriesSection() {
    const section = document.getElementById('competition-entries-section');
    if (!section) return;
    section.classList.toggle('hidden');
}

function addCompetitionEntry(event) {
    event.preventDefault();

    const concursanteId = parseInt(document.getElementById('entry_concursante_id').value);
    const sentadilla = parseFloat(document.getElementById('entry_sentadilla').value);
    const pressBanca = parseFloat(document.getElementById('entry_press_banca').value);
    const pesoMuerto = parseFloat(document.getElementById('entry_peso_muerto').value);

    if (!concursanteId || [sentadilla, pressBanca, pesoMuerto].some(Number.isNaN)) {
        showToast('Completa los datos del atleta y levantamientos.', 'error');
        return;
    }

    const atleta = allConcursantes.find(c => c.id === concursanteId);
    if (!atleta) {
        showToast('Atleta no encontrado.', 'error');
        return;
    }

    const existingIndex = pendingCompetitionEntries.findIndex(e => e.concursante_id === concursanteId);
    const entry = {
        concursante_id: concursanteId,
        nombre: atleta.nombre,
        categoria_peso: atleta.categoria_peso,
        sentadilla,
        press_banca: pressBanca,
        peso_muerto: pesoMuerto,
        total: sentadilla + pressBanca + pesoMuerto
    };

    if (existingIndex >= 0) {
        pendingCompetitionEntries[existingIndex] = entry;
        showToast('Levantamientos del atleta actualizados.', 'success');
    } else {
        pendingCompetitionEntries.push(entry);
        showToast('Atleta agregado a la competencia.', 'success');
    }

    document.getElementById('form-competition-entry').reset();
    renderPendingCompetitionEntries();
}

function removeCompetitionEntry(index) {
    pendingCompetitionEntries.splice(index, 1);
    renderPendingCompetitionEntries();
}

function renderPendingCompetitionEntries() {
    const tbody = document.querySelector('#competition-entries-table tbody');
    if (!tbody) return;

    tbody.innerHTML = '';
    pendingCompetitionEntries.forEach((entry, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${entry.nombre}</td>
            <td>${entry.sentadilla}</td>
            <td>${entry.press_banca}</td>
            <td>${entry.peso_muerto}</td>
            <td><strong>${entry.total.toFixed(1)}</strong></td>
            <td><button type="button" class="filter-btn" onclick="removeCompetitionEntry(${index})">Quitar</button></td>
        `;
        tbody.appendChild(row);
    });

    if (pendingCompetitionEntries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No hay atletas agregados.</td></tr>';
    }
}

function detectRecordImprovements(oldRecords, newRecords) {
    const changes = [];
    newRecords.forEach(record => {
        const previous = oldRecords.find(r => r.categoria === record.categoria);
        if (!previous) {
            changes.push(`Nueva categoría ${record.categoria} kg con ${record.concursante}`);
            return;
        }

        const improvedFields = [];
        if (record.sentadilla > previous.sentadilla) improvedFields.push(`sentadilla ${record.sentadilla}`);
        if (record.press_banca > previous.press_banca) improvedFields.push(`press banca ${record.press_banca}`);
        if (record.peso_muerto > previous.peso_muerto) improvedFields.push(`peso muerto ${record.peso_muerto}`);
        if (record.total > previous.total) improvedFields.push(`total ${record.total}`);
        if (record.ipf_score > previous.ipf_score) improvedFields.push(`IPF ${record.ipf_score.toFixed(2)}`);

        if (improvedFields.length > 0) {
            changes.push(`${record.categoria} kg · ${record.concursante}: ${improvedFields.join(', ')}`);
        }
    });
    return changes;
}

async function loadCompetitionDetail(compId) {
    try {
        const response = await fetch(`${API_URL}/competiciones/${compId}`);
        if (!response.ok) throw new Error('Error al cargar detalle de competencia');
        const competition = await response.json();
        const detail = document.getElementById('competition-detail');
        if (!detail) return;

        const dateLabel = competition.fecha ? new Date(competition.fecha).toLocaleDateString() : 'Sin fecha';
        const athletesHtml = (competition.atletas || []).map(atleta => `
            <article class="detail-row-card">
                <div>
                    <h4 class="link-like" onclick="viewConcursanteFromCompetition(${atleta.id})">${atleta.nombre}</h4>
                    <p>${atleta.categoria_peso} kg · ${atleta.sexo === 'M' ? 'Masculino' : 'Femenino'}</p>
                </div>
                <div>
                    <strong>${atleta.mejor_ipf.toFixed(2)}</strong>
                    <span>Mejor IPF</span>
                </div>
                <div>
                    <strong>${atleta.levantamientos.length}</strong>
                    <span>Intentos</span>
                </div>
            </article>
        `).join('');

        const topLiftsHtml = (competition.top_levantamientos || []).map((lift, index) => `
            <tr>
                <td>${index + 1}</td>
                <td>${lift.concursante.nombre}</td>
                <td>${lift.sentadilla}</td>
                <td>${lift.press_banca}</td>
                <td>${lift.peso_muerto}</td>
                <td><strong>${lift.total}</strong></td>
                <td>${lift.ipf_score.toFixed(2)}</td>
            </tr>
        `).join('');

        const podium = (competition.top_levantamientos || []).slice(0, 3);
        const podiumHtml = podium.map((lift, index) => `
            <article class="podium-card place-${index + 1}">
                <span class="podium-rank">#${index + 1}</span>
                <h5>${lift.concursante.nombre}</h5>
                <p>Total: <strong>${lift.total}</strong> kg</p>
                <p>IPF: <strong>${lift.ipf_score.toFixed(2)}</strong></p>
            </article>
        `).join('');

        const records = await fetch(`${API_URL}/records`);
        const recordsData = records.ok ? await records.json() : [];
        const recordsHtml = recordsData.slice(0, 5).map(record => `
            <div class="record-chip">
                <strong>${record.categoria} kg</strong>
                <span>${record.concursante}</span>
            </div>
        `).join('');

        detail.innerHTML = `
            <article class="competition-detail-card">
                <div class="competition-detail-header">
                    <div>
                        <span class="competition-year">${dateLabel}</span>
                        <h3>${competition.nombre}</h3>
                        <p>${competition.ubicacion}</p>
                    </div>
                    <div class="competition-metrics">
                        <div><strong>${competition.total_atletas}</strong><span>Atletas</span></div>
                        <div><strong>${(competition.mejor_ipf || 0).toFixed(2)}</strong><span>Mejor IPF</span></div>
                    </div>
                </div>

                <div class="competition-detail-section">
                    <h4>Atletas</h4>
                    <div class="detail-list">${athletesHtml || '<p>No hay atletas registrados en esta competencia.</p>'}</div>
                </div>

                <div class="competition-detail-section">
                    <h4>Podio de la competencia</h4>
                    <div class="podium-grid">${podiumHtml || '<p>No hay levantamientos suficientes para definir podio.</p>'}</div>
                </div>

                <div class="competition-detail-section">
                    <h4>Top levantamientos</h4>
                    <table class="ranking-table detail-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Atleta</th>
                                <th>Sentadilla</th>
                                <th>Press Banca</th>
                                <th>Peso Muerto</th>
                                <th>Total</th>
                                <th>IPF</th>
                            </tr>
                        </thead>
                        <tbody>${topLiftsHtml || '<tr><td colspan="7">Sin levantamientos registrados.</td></tr>'}</tbody>
                    </table>
                </div>

                <div class="competition-detail-section">
                    <h4>Records nacionales vigentes</h4>
                    <div class="records-chip-grid">${recordsHtml || '<p>No hay records cargados.</p>'}</div>
                </div>
            </article>
        `;
    } catch (err) {
        console.error(err);
        showToast('Error al cargar detalle de competencia', 'error');
    }
}

async function addLevantamientoCompetencia(event) {
    event.preventDefault();

    const competicionId = parseInt(document.getElementById('levantamiento_competicion_id').value);
    const concursanteId = parseInt(document.getElementById('levantamiento_concursante_id').value);
    const levantamiento = {
        competicion_id: competicionId,
        concursante_id: concursanteId,
        sentadilla: parseFloat(document.getElementById('levantamiento_sentadilla').value),
        press_banca: parseFloat(document.getElementById('levantamiento_press_banca').value),
        peso_muerto: parseFloat(document.getElementById('levantamiento_peso_muerto').value)
    };

    try {
        const levHeaders = { 'Content-Type': 'application/json' };
        if (ADMIN_KEY) levHeaders['x-admin-key'] = ADMIN_KEY;
        const response = await fetch(`${API_URL}/levantamientos`, {
            method: 'POST',
            headers: levHeaders,
            body: JSON.stringify(levantamiento)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al registrar levantamiento');
        }

        showToast('¡Levantamiento registrado exitosamente!', 'success');
        document.getElementById('form-levantamiento-competencia').reset();
        await loadAllData();
        loadCompetitionDetail(competicionId);
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Error al registrar levantamiento', 'error');
    }
}

async function addCompeticion(event) {
    event.preventDefault();

    const fecha = document.getElementById('competicion_fecha').value;
    const competicion = {
        nombre: document.getElementById('competicion_nombre').value,
        fecha,
        ubicacion: document.getElementById('competicion_ubicacion').value,
        descripcion: document.getElementById('competicion_descripcion').value || ''
    };

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (ADMIN_KEY) headers['x-admin-key'] = ADMIN_KEY;
        const response = await fetch(`${API_URL}/competiciones`, {
            method: 'POST',
            headers,
            body: JSON.stringify(competicion)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al registrar competencia');
        }

        showToast('¡Competencia registrada exitosamente!', 'success');
        document.getElementById('form-competicion').reset();
        await loadAllData();
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Error al registrar competencia', 'error');
    }
}

async function submitCompetitionWithEntries(event) {
    if (event) event.preventDefault();
    const resultBox = document.getElementById('competition-builder-result');
    const nombre = document.getElementById('competicion_nombre').value.trim();
    const fecha = document.getElementById('competicion_fecha').value;
    const ubicacion = document.getElementById('competicion_ubicacion').value.trim();
    const descripcion = document.getElementById('competicion_descripcion').value.trim();

    if (!nombre || !fecha || !ubicacion) {
        showToast('Completa los datos de la competencia.', 'error');
        return;
    }

    if (pendingCompetitionEntries.length === 0) {
        showToast('Agrega al menos un atleta con sus levantamientos.', 'error');
        return;
    }

    try {
        const recordsBeforeResp = await fetch(`${API_URL}/records`);
        const recordsBefore = recordsBeforeResp.ok ? await recordsBeforeResp.json() : [];

        const compHeaders = { 'Content-Type': 'application/json' };
        if (ADMIN_KEY) compHeaders['x-admin-key'] = ADMIN_KEY;
        const compResp = await fetch(`${API_URL}/competiciones`, {
            method: 'POST',
            headers: compHeaders,
            body: JSON.stringify({ nombre, fecha, ubicacion, descripcion })
        });
        if (!compResp.ok) {
            const error = await compResp.json();
            throw new Error(error.detail || 'No se pudo crear la competencia');
        }

        const competition = await compResp.json();

        for (const entry of pendingCompetitionEntries) {
            const levHeaders = { 'Content-Type': 'application/json' };
            if (ADMIN_KEY) levHeaders['x-admin-key'] = ADMIN_KEY;
            const levResp = await fetch(`${API_URL}/levantamientos`, {
                method: 'POST',
                headers: levHeaders,
                body: JSON.stringify({
                    competicion_id: competition.id,
                    concursante_id: entry.concursante_id,
                    sentadilla: entry.sentadilla,
                    press_banca: entry.press_banca,
                    peso_muerto: entry.peso_muerto
                })
            });
            if (!levResp.ok) {
                const levError = await levResp.json();
                throw new Error(levError.detail || `Error registrando levantamiento de ${entry.nombre}`);
            }
        }

        const detailResp = await fetch(`${API_URL}/competiciones/${competition.id}`);
        const detail = detailResp.ok ? await detailResp.json() : null;
        const top3 = (detail?.top_levantamientos || []).slice(0, 3);
        const podiumItems = top3.length > 0
            ? top3.map((lift, idx) => `<li>#${idx + 1} ${lift.concursante.nombre} · Total ${lift.total} kg · IPF ${lift.ipf_score.toFixed(2)}</li>`).join('')
            : '<li>No hay datos suficientes para podio.</li>';

        const recordsAfterResp = await fetch(`${API_URL}/records`);
        const recordsAfter = recordsAfterResp.ok ? await recordsAfterResp.json() : [];
        const recordChanges = detectRecordImprovements(recordsBefore, recordsAfter);

        if (resultBox) {
            resultBox.innerHTML = `
                <article class="info-card highlighted-competition">
                    <h3>Resultados calculados</h3>
                    <p><strong>Top 3:</strong></p>
                    <ul class="rule-list">${podiumItems}</ul>
                    <p><strong>Records nacionales:</strong></p>
                    <ul class="rule-list">
                        ${(recordChanges.length > 0 ? recordChanges.map(change => `<li>${change}</li>`).join('') : '<li>No hubo nuevos records nacionales.</li>')}
                    </ul>
                </article>
            `;
        }

        showToast('Competencia y levantamientos guardados correctamente.', 'success');
        pendingCompetitionEntries = [];
        renderPendingCompetitionEntries();
        await loadAllData();
        loadCompetitionDetail(competition.id);
    } catch (error) {
        console.error(error);
        showToast(error.message || 'Error al guardar competencia completa', 'error');
    }
}

// ==================== EQUIPOS ====================

async function loadTeams() {
    try {
        const resp = await fetch(`${API_URL}/equipos`);
        if (!resp.ok) return;
        const equipos = await resp.json();
        const container = document.getElementById('teams-container');
        if (!container) return;
        container.innerHTML = '';

        equipos.forEach(e => {
            const card = document.createElement('article');
            card.className = 'info-card clickable';
            card.innerHTML = `
                <h3>${e.nombre}</h3>
                <p>${e.descripcion || ''}</p>
                <p><small>Miembros: ${e.miembros_count || 0}</small></p>
                <button class="btn-submit soft" onclick="viewTeam(${e.id})">Ver integrantes</button>
            `;
            container.appendChild(card);
        });

        // Mostrar admin form si tiene ADMIN_KEY
        if (ADMIN_KEY) {
            const adminBox = document.getElementById('team-admin');
            if (adminBox) adminBox.style.display = 'block';
        }
    } catch (err) { console.error('Error cargando equipos', err); }
}

async function viewTeam(equipoId) {
    try {
        const resp = await fetch(`${API_URL}/equipos/${equipoId}`);
        if (!resp.ok) throw new Error('Equipo no encontrado');
        const equipo = await resp.json();
        const detail = document.getElementById('team-detail');
        if (!detail) return;
        const membersHtml = (equipo.miembros || []).map(m => `
            <article class="detail-row-card">
                <div>
                    <h4 class="link-like" onclick="viewConcursanteFromCompetition(${m.id})">${m.nombre}</h4>
                    <p>${m.categoria_peso} kg · ${m.sexo === 'M' ? 'Masculino' : 'Femenino'}</p>
                </div>
            </article>
        `).join('');

        detail.innerHTML = `
            <article class="competition-detail-card">
                <div class="competition-detail-header">
                    <div>
                        <h3>${equipo.nombre}</h3>
                        <p>${equipo.descripcion || ''}</p>
                    </div>
                </div>
                <div class="competition-detail-section">
                    <h4>Integrantes</h4>
                    <div class="detail-list">${membersHtml || '<p>No hay atletas asignados a este equipo.</p>'}</div>
                </div>
            </article>
        `;
        switchTab('equipos');
    } catch (err) { console.error(err); showToast('Error cargando equipo', 'error'); }
}

async function addEquipo(event) {
    event.preventDefault();
    const nombre = document.getElementById('equipo_nombre').value.trim();
    const descripcion = document.getElementById('equipo_descripcion').value.trim();
    if (!nombre) { showToast('Nombre requerido', 'error'); return; }

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (ADMIN_KEY) headers['x-admin-key'] = ADMIN_KEY;
        const resp = await fetch(`${API_URL}/equipos`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ nombre, descripcion })
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Error creando equipo');
        }
        showToast('Equipo creado', 'success');
        document.getElementById('form-equipo').reset();
        await loadTeams();
    } catch (err) { console.error(err); showToast(err.message || 'Error', 'error'); }
}

function filterByCompetition() {
    const val = document.getElementById('competition-filter').value;
    currentCompetitionFilter = val;
    if (val === 'all') {
        loadRanking(currentRankingFilter);
        return;
    }
    loadRankingByCompetition(val);
}

async function loadRankingByCompetition(compId) {
    try {
        const response = await fetch(`${API_URL}/competiciones/${compId}`);
        if (!response.ok) throw new Error('Error al cargar competición');
        const comp = await response.json();
        const levs = comp.levantamientos || [];
        renderRankingTable(levs.map(l => ({
            nombre: l.concursante.nombre,
            sexo: l.concursante.sexo,
            categoria_peso: l.concursante.categoria_peso,
            sentadilla: l.sentadilla,
            press_banca: l.press_banca,
            peso_muerto: l.peso_muerto,
            total: l.sentadilla + l.press_banca + l.peso_muerto,
            ipf_score: l.ipf_score
        })));
    } catch (err) { console.error(err); showToast('Error al cargar competición', 'error'); }
}

function applySort() {
    currentSort = document.getElementById('sort-filter').value;
    if (currentCompetitionFilter === 'all') {
        loadRanking(currentRankingFilter);
    } else {
        loadRankingByCompetition(currentCompetitionFilter);
    }
}

function renderRankingTable(items) {
    const tbody = document.querySelector('#ranking-table tbody');
    tbody.innerHTML = '';
    // ordenar
    items.sort((a,b) => (currentSort === 'ipf' ? b.ipf_score - a.ipf_score : (b.total || 0) - (a.total || 0)));
    items.forEach((item, index) => {
        const row = `
            <tr>
                <td>${index + 1}</td>
                <td>${item.nombre}</td>
                <td>${item.sexo === 'M' ? 'Masculino' : 'Femenino'}</td>
                <td>${item.categoria_peso} kg</td>
                <td>${item.sentadilla}</td>
                <td>${item.press_banca}</td>
                <td>${item.peso_muerto}</td>
                <td><strong>${item.total}</strong></td>
                <td><span style="color: #e74c3c; font-weight: bold;">${item.ipf_score.toFixed(2)}</span></td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

async function loadRecords() {
    try {
        const response = await fetch(`${API_URL}/records`);
        if (!response.ok) throw new Error('Error al cargar records');
        const records = await response.json();
        const tbody = document.querySelector('#records-table tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        records.forEach(record => {
            const row = `
                <tr>
                    <td>${record.categoria} kg</td>
                    <td>${record.concursante}</td>
                    <td>${record.sentadilla}</td>
                    <td>${record.press_banca}</td>
                    <td>${record.peso_muerto}</td>
                    <td><strong>${record.total}</strong></td>
                    <td>${record.ipf_score.toFixed(2)}</td>
                </tr>
            `;
            tbody.innerHTML += row;
        });
    } catch (err) { console.error(err); showToast('Error al cargar records', 'error'); }
}

// ==================== FILTRO DE BÚSQUEDA ====================

function filterConcursantes() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const cards = document.querySelectorAll('.concursante-card');
    
    cards.forEach(card => {
        const nombre = card.querySelector('h3').textContent.toLowerCase();
        if (nombre.includes(searchTerm)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// ==================== NOTIFICACIONES ====================

function showToast(message, type = 'success') {
    // Crear elemento toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: ${type === 'success' ? '#cfe7d9' : '#f7d6d6'};
        color: #4a5a66;
        padding: 15px 20px;
        border-radius: 5px;
        font-weight: bold;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    // Remover después de 3 segundos
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Agregar estilos de animación
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(24px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(24px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
