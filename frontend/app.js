// URL base del API Gateway
const API_URL = 'http://localhost:5000';

// Token de autenticación
let authToken = localStorage.getItem('token');
let currentUser = null;
let userRole = null;

// ==================== AUTENTICACIÓN ====================

async function login(event) {
    event.preventDefault();
    
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al iniciar sesión');
        }
        
        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('token', authToken);
        
        // Obtener información del usuario
        await getCurrentUser();
        
        // Mostrar aplicación
        document.getElementById('login-screen').style.display = 'none';
        document.getElementById('app-screen').style.display = 'block';
        
        // Actualizar UI según el rol
        updateUIByRole();
        
        // Cargar datos iniciales según el rol
        loadInitialDataByRole();
        
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function getCurrentUser() {
    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Error al obtener información del usuario');
        }
        
        currentUser = await response.json();
        userRole = currentUser.rol;
        
        // Mostrar información del usuario
        document.getElementById('user-info').innerHTML = `
            <span class="user-name">${currentUser.nombre}</span>
            <span class="user-role">(${userRole})</span>
        `;
        
    } catch (error) {
        console.error('Error al obtener usuario:', error);
        logout();
    }
}

function updateUIByRole() {
    // Ocultar todos los elementos específicos de rol
    document.querySelectorAll('[data-role]').forEach(el => {
        el.style.display = 'none';
    });
    
    // Mostrar elementos según el rol
    // Los elementos pueden tener múltiples roles separados por coma: data-role="admin,docente"
    document.querySelectorAll('[data-role]').forEach(el => {
        const roles = el.getAttribute('data-role').split(',').map(r => r.trim());
        if (roles.includes(userRole)) {
            el.style.display = 'block';
        }
    });
    
    // Actualizar navegación
    updateNavigation();
}

function updateNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');

    navButtons.forEach(btn => {
        const section = btn.getAttribute('onclick').match(/showSection\('(.+)'\)/)?.[1];

        if (userRole === 'admin') {
            // Admin: ve Estudiantes, Asignaturas, Evaluaciones, Notas, Reportes y Usuarios
            if (['mis-estudiantes'].includes(section)) {
                btn.style.display = 'none';
            } else {
                btn.style.display = 'inline-block';
            }
        } else if (userRole === 'docente') {
            // Docente ve: estudiantes (de sus asignaturas), asignaturas (suyas), evaluaciones, notas, reportes
            if (['estudiantes', 'asignaturas', 'evaluaciones', 'notas', 'reportes'].includes(section)) {
                btn.style.display = 'inline-block';
            } else {
                btn.style.display = 'none';
            }
        } else if (userRole === 'acudiente') {
            // Acudiente solo ve: mis estudiantes
            if (['mis-estudiantes'].includes(section)) {
                btn.style.display = 'inline-block';
            } else {
                btn.style.display = 'none';
            }
        }
    });
}

function loadInitialDataByRole() {
    if (userRole === 'admin') {
        showSection('estudiantes');
    } else if (userRole === 'docente') {
        showSection('asignaturas');
    } else if (userRole === 'acudiente') {
        showSection('mis-estudiantes');
    }
}

function logout() {
    authToken = null;
    localStorage.removeItem('token');
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('app-screen').style.display = 'none';
}

function checkAuth() {
    if (!authToken) {
        document.getElementById('login-screen').style.display = 'flex';
        document.getElementById('app-screen').style.display = 'none';
        return false;
    }
    return true;
}

// ==================== UTILIDADES ====================

async function apiRequest(endpoint, method = 'GET', data = null) {
    if (!checkAuth()) {
        return;
    }
    
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_URL}${endpoint}`, options);
        if (!response.ok) {
            if (response.status === 401) {
                logout();
                throw new Error('Sesión expirada. Por favor, inicie sesión nuevamente.');
            }
            const error = await response.json();
            throw new Error(error.detail || 'Error en la petición');
        }
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        alert(`Error: ${error.message}`);
        throw error;
    }
}

function showSection(sectionId) {
    // Ocultar todas las secciones
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Mostrar la sección seleccionada
    document.getElementById(sectionId).classList.add('active');
    
    // Actualizar botones de navegación
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Encontrar y activar el botón correspondiente
    const activeBtn = document.querySelector(`.nav-btn[onclick*="showSection('${sectionId}')"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // Cargar datos de la sección
    switch(sectionId) {
        case 'estudiantes':
            cargarEstudiantes();
            cargarAcudientesSelect('estudiante-acudiente');
            break;
        case 'asignaturas':
            cargarAsignaturas();
            if (userRole === 'admin') {
                cargarDocentesSelect();
            }
            break;
        case 'evaluaciones':
            cargarEvaluaciones();
            cargarAsignaturasSelect('evaluacion-asignatura');
            break;
        case 'notas':
            cargarNotas();
            if (userRole !== 'acudiente') {
                cargarEstudiantesSelect('nota-estudiante');
            }
            cargarEvaluacionesSelect('nota-evaluacion');
            break;
        case 'reportes':
            if (userRole !== 'acudiente') {
                cargarEstudiantesSelect('reporte-estudiante');
            }
            cargarAsignaturasSelect('reporte-asignatura');
            break;
        case 'mis-estudiantes':
            cargarMisEstudiantes();
            break;
        case 'usuarios':
            cargarUsuarios();
            break;
    }
}

// ==================== ESTUDIANTES ====================

async function cargarEstudiantes() {
    let estudiantes;
    
    // Filtrar según el rol
    if (userRole === 'admin') {
        estudiantes = await apiRequest('/estudiantes');
    } else if (userRole === 'docente') {
        // Docente ve solo sus estudiantes (matriculados en sus asignaturas)
        estudiantes = await apiRequest('/estudiantes/mis-estudiantes');
    } else if (userRole === 'acudiente') {
        // Acudiente ve solo sus estudiantes
        estudiantes = await apiRequest('/estudiantes/mis-hijos');
    } else {
        estudiantes = [];
    }
    
    const tbody = document.querySelector('#tabla-estudiantes tbody');
    tbody.innerHTML = '';
    
    estudiantes.forEach(est => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${est.id}</td>
            <td>${est.nombre}</td>
            <td>${est.apellido}</td>
            <td>${est.codigo}</td>
            <td>${est.email}</td>
            <td>
                ${userRole === 'admin' || userRole === 'docente' ? `
                    <button class="btn-edit" onclick="editarEstudiante(${est.id})">Editar</button>
                    <button class="btn-delete" onclick="eliminarEstudiante(${est.id})">Eliminar</button>
                ` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function guardarEstudiante(event) {
    event.preventDefault();
    
    const id = document.getElementById('estudiante-id').value;
    const acudienteSelect = document.getElementById('estudiante-acudiente');
    const acudienteId = acudienteSelect ? acudienteSelect.value : null;
    
    const estudiante = {
        nombre: document.getElementById('estudiante-nombre').value,
        apellido: document.getElementById('estudiante-apellido').value,
        codigo: document.getElementById('estudiante-codigo').value,
        email: document.getElementById('estudiante-email').value || null,
        acudiente_id: acudienteId ? parseInt(acudienteId) : null
    };
    
    try {
        if (id) {
            await apiRequest(`/estudiantes/${id}`, 'PUT', estudiante);
            alert('Estudiante actualizado correctamente');
        } else {
            await apiRequest('/estudiantes', 'POST', estudiante);
            alert('Estudiante creado correctamente');
        }
        limpiarFormEstudiante();
        cargarEstudiantes();
    } catch (error) {
        console.error('Error al guardar estudiante:', error);
    }
}

async function editarEstudiante(id) {
    const estudiante = await apiRequest(`/estudiantes/${id}`);
    document.getElementById('estudiante-id').value = estudiante.id;
    document.getElementById('estudiante-nombre').value = estudiante.nombre;
    document.getElementById('estudiante-apellido').value = estudiante.apellido;
    document.getElementById('estudiante-codigo').value = estudiante.codigo;
    document.getElementById('estudiante-email').value = estudiante.email || '';
    
    // Cargar acudientes y seleccionar el actual si existe
    await cargarAcudientesSelect('estudiante-acudiente');
    
    // Obtener el acudiente actual del estudiante
    try {
        const acudientes = await apiRequest(`/estudiantes/acudiente/${id}`);
        if (acudientes && acudientes.length > 0) {
            document.getElementById('estudiante-acudiente').value = acudientes[0].usuario_id;
        }
    } catch (error) {
        console.log('Estudiante sin acudiente asignado');
    }
}

async function eliminarEstudiante(id) {
    if (confirm('¿Está seguro de eliminar este estudiante?')) {
        await apiRequest(`/estudiantes/${id}`, 'DELETE');
        alert('Estudiante eliminado correctamente');
        cargarEstudiantes();
    }
}

function limpiarFormEstudiante() {
    document.getElementById('form-estudiante').reset();
    document.getElementById('estudiante-id').value = '';
    cargarAcudientesSelect('estudiante-acudiente');
}

// ==================== ACUDIENTES ====================

async function cargarAcudientesSelect(selectId) {
    try {
        const usuarios = await apiRequest('/usuarios/acudientes');
        const select = document.getElementById(selectId);
        select.innerHTML = '<option value="">Sin acudiente</option>';
        
        usuarios.forEach(usuario => {
            const option = document.createElement('option');
            option.value = usuario.id;
            option.textContent = `${usuario.nombre} (${usuario.username})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error al cargar acudientes:', error);
    }
}

// ==================== DOCENTES ====================

async function cargarDocentesSelect() {
    try {
        const usuarios = await apiRequest('/usuarios');
        const docentes = usuarios.filter(u => u.rol === 'docente');
        
        const select = document.getElementById('asignatura-docente');
        if (!select) return;
        
        select.innerHTML = '<option value="">Seleccione un docente</option>';
        docentes.forEach(docente => {
            const option = document.createElement('option');
            option.value = docente.id;
            option.textContent = `${docente.nombre} (${docente.username})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error al cargar docentes:', error);
    }
}

// ==================== ASIGNATURAS ====================

async function cargarAsignaturas() {
    let asignaturas;
    
    // Filtrar según el rol
    if (userRole === 'admin') {
        asignaturas = await apiRequest('/asignaturas');
    } else if (userRole === 'docente') {
        // Docente ve solo sus asignaturas
        asignaturas = await apiRequest('/asignaturas/mias');
    } else {
        asignaturas = [];
    }
    
    const tbody = document.querySelector('#tabla-asignaturas tbody');
    tbody.innerHTML = '';
    
    asignaturas.forEach(asig => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${asig.id}</td>
            <td>${asig.nombre}</td>
            <td>${asig.codigo}</td>
            <td>${asig.descripcion || '-'}</td>
            <td>
                ${userRole === 'admin' || userRole === 'docente' ? `
                    <button class="btn-edit" onclick="editarAsignatura(${asig.id})">Editar</button>
                    <button class="btn-delete" onclick="eliminarAsignatura(${asig.id})">Eliminar</button>
                ` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function guardarAsignatura(event) {
    event.preventDefault();
    
    const id = document.getElementById('asignatura-id').value;
    const asignatura = {
        nombre: document.getElementById('asignatura-nombre').value,
        codigo: document.getElementById('asignatura-codigo').value,
        descripcion: document.getElementById('asignatura-descripcion').value || null
    };
    
    // Si es admin y seleccionó un docente, asignar la asignatura al docente
    const docenteSelect = document.getElementById('asignatura-docente');
    const docenteId = docenteSelect ? docenteSelect.value : null;
    
    try {
        // Crear la asignatura
        let response;
        if (id) {
            response = await apiRequest(`/asignaturas/${id}`, 'PUT', asignatura);
            alert('Asignatura actualizada correctamente');
        } else {
            response = await apiRequest('/asignaturas', 'POST', asignatura);
            alert('Asignatura creada correctamente');
            
            // Si es admin y seleccionó un docente, asignar la asignatura al docente
            if (userRole === 'admin' && docenteId && response && response.id) {
                try {
                    await apiRequest('/admin/asignar-asignaturas', 'POST', {
                        usuario_id: parseInt(docenteId),
                        asignatura_ids: [response.id]
                    });
                    alert('Asignatura asignada al docente correctamente');
                } catch (error) {
                    console.error('Error al asignar asignatura al docente:', error);
                    alert('Asignatura creada pero hubo un error al asignarla al docente');
                }
            }
        }
        limpiarFormAsignatura();
        cargarAsignaturas();
    } catch (error) {
        console.error('Error al guardar asignatura:', error);
    }
}

async function editarAsignatura(id) {
    const asignatura = await apiRequest(`/asignaturas/${id}`);
    document.getElementById('asignatura-id').value = asignatura.id;
    document.getElementById('asignatura-nombre').value = asignatura.nombre;
    document.getElementById('asignatura-codigo').value = asignatura.codigo;
    document.getElementById('asignatura-descripcion').value = asignatura.descripcion || '';
}

async function eliminarAsignatura(id) {
    if (confirm('¿Está seguro de eliminar esta asignatura?')) {
        await apiRequest(`/asignaturas/${id}`, 'DELETE');
        alert('Asignatura eliminada correctamente');
        cargarAsignaturas();
    }
}

function limpiarFormAsignatura() {
    document.getElementById('form-asignatura').reset();
    document.getElementById('asignatura-id').value = '';
}

// ==================== EVALUACIONES ====================

async function cargarEvaluaciones() {
    let evaluaciones;
    
    // Filtrar según el rol
    if (userRole === 'admin') {
        evaluaciones = await apiRequest('/evaluaciones');
    } else if (userRole === 'docente') {
        // Docente ve evaluaciones de sus asignaturas
        evaluaciones = await apiRequest('/evaluaciones/mias');
    } else {
        evaluaciones = [];
    }
    
    // Cargar asignaturas para mostrar nombres
    const asignaturas = await apiRequest('/asignaturas');
    const asignaturasMap = {};
    asignaturas.forEach(a => asignaturasMap[a.id] = a.nombre);
    
    const tbody = document.querySelector('#tabla-evaluaciones tbody');
    tbody.innerHTML = '';
    
    evaluaciones.forEach(ev => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${ev.id}</td>
            <td>${ev.nombre}</td>
            <td>${ev.fecha}</td>
            <td>${ev.ponderacion}%</td>
            <td>${asignaturasMap[ev.asignatura_id] || ev.asignatura_id}</td>
            <td>
                ${userRole === 'admin' || userRole === 'docente' ? `
                    <button class="btn-edit" onclick="editarEvaluacion(${ev.id})">Editar</button>
                    <button class="btn-delete" onclick="eliminarEvaluacion(${ev.id})">Eliminar</button>
                ` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function guardarEvaluacion(event) {
    event.preventDefault();
    
    const id = document.getElementById('evaluacion-id').value;
    const evaluacion = {
        nombre: document.getElementById('evaluacion-nombre').value,
        fecha: document.getElementById('evaluacion-fecha').value,
        ponderacion: parseFloat(document.getElementById('evaluacion-ponderacion').value),
        asignatura_id: parseInt(document.getElementById('evaluacion-asignatura').value)
    };
    
    try {
        if (id) {
            await apiRequest(`/evaluaciones/${id}`, 'PUT', evaluacion);
            alert('Evaluación actualizada correctamente');
        } else {
            await apiRequest('/evaluaciones', 'POST', evaluacion);
            alert('Evaluación creada correctamente');
        }
        limpiarFormEvaluacion();
        cargarEvaluaciones();
    } catch (error) {
        console.error('Error al guardar evaluación:', error);
    }
}

async function editarEvaluacion(id) {
    const evaluacion = await apiRequest(`/evaluaciones/${id}`);
    document.getElementById('evaluacion-id').value = evaluacion.id;
    document.getElementById('evaluacion-nombre').value = evaluacion.nombre;
    document.getElementById('evaluacion-fecha').value = evaluacion.fecha;
    document.getElementById('evaluacion-ponderacion').value = evaluacion.ponderacion;
    document.getElementById('evaluacion-asignatura').value = evaluacion.asignatura_id;
}

async function eliminarEvaluacion(id) {
    if (confirm('¿Está seguro de eliminar esta evaluación?')) {
        await apiRequest(`/evaluaciones/${id}`, 'DELETE');
        alert('Evaluación eliminada correctamente');
        cargarEvaluaciones();
    }
}

function limpiarFormEvaluacion() {
    document.getElementById('form-evaluacion').reset();
    document.getElementById('evaluacion-id').value = '';
}

// ==================== NOTAS ====================

async function cargarNotas() {
    let notas;
    
    // Filtrar según el rol
    if (userRole === 'admin') {
        notas = await apiRequest('/notas');
    } else if (userRole === 'docente') {
        // Docente ve notas de sus estudiantes matriculados
        notas = await apiRequest('/notas/mis-estudiantes');
    } else if (userRole === 'acudiente') {
        // Acudiente ve notas de sus estudiantes
        notas = await apiRequest('/notas/mis-hijos');
    } else {
        notas = [];
    }
    
    // Cargar datos relacionados
    let estudiantes;
    if (userRole === 'admin') {
        estudiantes = await apiRequest('/estudiantes');
    } else if (userRole === 'docente') {
        estudiantes = await apiRequest('/estudiantes/mis-estudiantes');
    } else if (userRole === 'acudiente') {
        estudiantes = await apiRequest('/estudiantes/mis-hijos');
    } else {
        estudiantes = [];
    }
    
    const evaluaciones = await apiRequest('/evaluaciones');
    
    const estudiantesMap = {};
    estudiantes.forEach(e => estudiantesMap[e.id] = `${e.nombre} ${e.apellido}`);
    
    const evaluacionesMap = {};
    evaluaciones.forEach(ev => evaluacionesMap[ev.id] = ev.nombre);
    
    const tbody = document.querySelector('#tabla-notas tbody');
    tbody.innerHTML = '';
    
    notas.forEach(nota => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${nota.id}</td>
            <td>${estudiantesMap[nota.estudiante_id] || nota.estudiante_id}</td>
            <td>${evaluacionesMap[nota.evaluacion_id] || nota.evaluacion_id}</td>
            <td>${nota.valor}</td>
            <td>
                ${userRole === 'admin' || userRole === 'docente' ? `
                    <button class="btn-edit" onclick="editarNota(${nota.id})">Editar</button>
                    <button class="btn-delete" onclick="eliminarNota(${nota.id})">Eliminar</button>
                ` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function guardarNota(event) {
    event.preventDefault();
    
    const id = document.getElementById('nota-id').value;
    const nota = {
        estudiante_id: parseInt(document.getElementById('nota-estudiante').value),
        evaluacion_id: parseInt(document.getElementById('nota-evaluacion').value),
        valor: parseFloat(document.getElementById('nota-valor').value)
    };
    
    try {
        if (id) {
            await apiRequest(`/notas/${id}`, 'PUT', nota);
            alert('Nota actualizada correctamente');
        } else {
            await apiRequest('/notas', 'POST', nota);
            alert('Nota creada correctamente');
        }
        limpiarFormNota();
        cargarNotas();
    } catch (error) {
        console.error('Error al guardar nota:', error);
    }
}

async function editarNota(id) {
    const nota = await apiRequest(`/notas/${id}`);
    document.getElementById('nota-id').value = nota.id;
    document.getElementById('nota-estudiante').value = nota.estudiante_id;
    document.getElementById('nota-evaluacion').value = nota.evaluacion_id;
    document.getElementById('nota-valor').value = nota.valor;
}

async function eliminarNota(id) {
    if (confirm('¿Está seguro de eliminar esta nota?')) {
        await apiRequest(`/notas/${id}`, 'DELETE');
        alert('Nota eliminada correctamente');
        cargarNotas();
    }
}

function limpiarFormNota() {
    document.getElementById('form-nota').reset();
    document.getElementById('nota-id').value = '';
}

// ==================== SELECTORES ====================

async function cargarEstudiantesSelect(selectId) {
    let estudiantes;
    
    // Filtrar según el rol
    if (userRole === 'admin') {
        estudiantes = await apiRequest('/estudiantes');
    } else if (userRole === 'docente') {
        // Docente ve estudiantes de sus asignaturas
        estudiantes = await apiRequest('/estudiantes/mis-estudiantes');
    } else if (userRole === 'acudiente') {
        // Acudiente ve sus estudiantes asignados
        estudiantes = await apiRequest('/estudiantes/mis-hijos');
    } else {
        estudiantes = [];
    }
    
    const select = document.getElementById(selectId);
    select.innerHTML = '<option value="">Seleccione un estudiante</option>';
    
    estudiantes.forEach(est => {
        const option = document.createElement('option');
        option.value = est.id;
        option.textContent = `${est.nombre} ${est.apellido} (${est.codigo})`;
        select.appendChild(option);
    });
}

async function cargarAsignaturasSelect(selectId) {
    let asignaturas;
    
    // Filtrar según el rol
    if (userRole === 'admin') {
        asignaturas = await apiRequest('/asignaturas');
    } else if (userRole === 'docente') {
        // Docente ve solo sus asignaturas
        asignaturas = await apiRequest('/asignaturas/mias');
    } else {
        asignaturas = [];
    }
    
    const select = document.getElementById(selectId);
    select.innerHTML = '<option value="">Seleccione una asignatura</option>';
    
    asignaturas.forEach(asig => {
        const option = document.createElement('option');
        option.value = asig.id;
        option.textContent = `${asig.nombre} (${asig.codigo})`;
        select.appendChild(option);
    });
}

async function cargarEvaluacionesSelect(selectId) {
    let evaluaciones;
    
    // Filtrar según el rol
    if (userRole === 'admin') {
        evaluaciones = await apiRequest('/evaluaciones');
    } else if (userRole === 'docente') {
        // Docente ve solo sus evaluaciones
        evaluaciones = await apiRequest('/evaluaciones/mias');
    } else {
        evaluaciones = [];
    }
    
    const select = document.getElementById(selectId);
    select.innerHTML = '<option value="">Seleccione una evaluación</option>';
    
    evaluaciones.forEach(ev => {
        const option = document.createElement('option');
        option.value = ev.id;
        option.textContent = `${ev.nombre} (${ev.ponderacion}%)`;
        select.appendChild(option);
    });
}

// ==================== REPORTES ====================

async function calcularPromedio() {
    const estudianteId = document.getElementById('reporte-estudiante').value;
    const asignaturaId = document.getElementById('reporte-asignatura').value;
    
    if (!estudianteId || !asignaturaId) {
        alert('Por favor seleccione un estudiante y una asignatura');
        return;
    }
    
    const resultado = await apiRequest(`/notas/promedio/estudiante/${estudianteId}/asignatura/${asignaturaId}`);
    
    const container = document.getElementById('resultado-promedio');
    container.innerHTML = `
        <h4>Promedio del Estudiante</h4>
        <p class="promedio-valor">${resultado.promedio}</p>
        <p><strong>Suma de ponderaciones:</strong> ${resultado.suma_ponderaciones}%</p>
        <h5>Detalle de Notas:</h5>
        ${resultado.notas.map(n => `
            <div class="nota-detalle">
                <strong>${n.evaluacion_nombre}</strong><br>
                Nota: ${n.nota} | Ponderación: ${n.ponderacion}% | Nota Ponderada: ${n.nota_ponderada}
            </div>
        `).join('')}
    `;
}

async function generarReporte() {
    const asignaturaId = document.getElementById('reporte-asignatura').value;
    
    if (!asignaturaId) {
        alert('Por favor seleccione una asignatura');
        return;
    }
    
    const resultado = await apiRequest(`/notas/reporte/asignatura/${asignaturaId}`);
    
    const container = document.getElementById('resultado-reporte');
    container.innerHTML = `
        <h4>Reporte de Asignatura</h4>
        <p><strong>Total de estudiantes:</strong> ${resultado.total_estudiantes}</p>
        <table>
            <thead>
                <tr>
                    <th>Estudiante</th>
                    <th>Notas</th>
                    <th>Promedio</th>
                </tr>
            </thead>
            <tbody>
                ${resultado.reporte.map(r => `
                    <tr>
                        <td>${r.estudiante_nombre}</td>
                        <td>
                            ${r.notas.map(n => `
                                <div class="nota-detalle">
                                    ${n.evaluacion_nombre}: ${n.nota} (${n.ponderacion}%)
                                </div>
                            `).join('')}
                        </td>
                        <td><strong>${r.promedio}</strong></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// ==================== INICIALIZACIÓN ====================

document.addEventListener('DOMContentLoaded', () => {
    // Verificar si hay token guardado
    if (authToken) {
        // Verificar si el token es válido y obtener información del usuario
        getCurrentUser()
            .then(() => {
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('app-screen').style.display = 'block';
                updateUIByRole();
                loadInitialDataByRole();
            })
            .catch(() => {
                logout();
            });
    } else {
        document.getElementById('login-screen').style.display = 'flex';
        document.getElementById('app-screen').style.display = 'none';
    }
});

// ==================== MIS ESTUDIANTES (ACUDIENTE) ====================

async function cargarMisEstudiantes() {
    if (userRole !== 'acudiente') {
        // Limpiar contenido residual por si el DOM quedó con datos de una sesión previa
        const tbody = document.querySelector('#tabla-mis-estudiantes tbody');
        if (tbody) tbody.innerHTML = '';
        return;
    }

    const estudiantes = await apiRequest('/estudiantes/mis-hijos');
    const tbody = document.querySelector('#tabla-mis-estudiantes tbody');
    tbody.innerHTML = '';
    
    for (const est of estudiantes) {
        // Obtener promedio general del estudiante
        let promedioGeneral = '-';
        try {
            const promedioData = await apiRequest(`/notas/promedio-general/estudiante/${est.id}`);
            promedioGeneral = promedioData.promedio_general || '-';
        } catch (error) {
            console.error(`Error obteniendo promedio del estudiante ${est.id}:`, error);
        }
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${est.id}</td>
            <td>${est.nombre}</td>
            <td>${est.apellido}</td>
            <td>${est.codigo}</td>
            <td>${est.email}</td>
            <td><strong>${promedioGeneral}</strong></td>
            <td>
                <button class="btn-view" onclick="verNotasEstudiante(${est.id}, '${est.nombre} ${est.apellido}')">Ver Notas</button>
            </td>
        `;
        tbody.appendChild(tr);
    }
}

async function verNotasEstudiante(estudianteId, nombreEstudiante) {
    try {
        // Obtener promedio general y asignaturas
        const promedioData = await apiRequest(`/notas/promedio-general/estudiante/${estudianteId}`);
        
        // Actualizar título del modal
        document.getElementById('modal-titulo-notas').textContent = `Notas de ${nombreEstudiante}`;
        
        // Construir contenido del modal
        let contenido = `
            <div class="nota-final">
                <div>Promedio General</div>
                <div class="nota-valor">${promedioData.promedio_general || 'N/A'}</div>
            </div>
        `;
        
        if (promedioData.asignaturas && promedioData.asignaturas.length > 0) {
            contenido += `
                <table>
                    <thead>
                        <tr>
                            <th>Asignatura</th>
                            <th>Promedio</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            for (const asig of promedioData.asignaturas) {
                contenido += `
                    <tr>
                        <td>${asig.asignatura_nombre}</td>
                        <td><strong>${asig.promedio}</strong></td>
                        <td>
                            <button class="btn-view" onclick="verDetalleAsignatura(${estudianteId}, ${asig.asignatura_id}, '${asig.asignatura_nombre}')">Ver Detalle</button>
                        </td>
                    </tr>
                `;
            }
            
            contenido += `
                    </tbody>
                </table>
            `;
        } else {
            contenido += '<p>No hay asignaturas matriculadas</p>';
        }
        
        document.getElementById('notas-estudiante-contenido').innerHTML = contenido;
        document.getElementById('modal-notas-estudiante').style.display = 'flex';
        
    } catch (error) {
        console.error('Error al obtener notas del estudiante:', error);
        alert('Error al cargar las notas del estudiante');
    }
}

async function verDetalleAsignatura(estudianteId, asignaturaId, nombreAsignatura) {
    try {
        // Obtener notas detalladas del estudiante
        const notasData = await apiRequest(`/notas/estudiante/${estudianteId}`);

        // Filtrar notas de esta asignatura
        const notasAsignatura = notasData.filter(nota => Number(nota.asignatura_id) === Number(asignaturaId));

        // Actualizar título del modal
        document.getElementById('modal-titulo-notas').textContent = `Detalle de ${nombreAsignatura}`;

        // Construir contenido del modal
        let contenido = `
            <table>
                <thead>
                    <tr>
                        <th>Evaluación</th>
                        <th>Nota</th>
                        <th>Ponderación</th>
                    </tr>
                </thead>
                <tbody>
        `;

        if (notasAsignatura.length > 0) {
            for (const nota of notasAsignatura) {
                const pond = nota.ponderacion !== undefined && nota.ponderacion !== null
                    ? `${nota.ponderacion}%`
                    : '-';
                contenido += `
                    <tr>
                        <td>${nota.evaluacion_nombre}</td>
                        <td><strong>${nota.valor}</strong></td>
                        <td>${pond}</td>
                    </tr>
                `;
            }
        } else {
            contenido += '<tr><td colspan="3">No hay notas registradas para esta asignatura</td></tr>';
        }

        contenido += `
                </tbody>
            </table>
            <div style="margin-top: 20px;">
                <button class="btn-secondary" onclick="cerrarModalNotas()">Cerrar</button>
            </div>
        `;

        document.getElementById('notas-estudiante-contenido').innerHTML = contenido;

        // Mostrar el modal (faltaba esta línea: por eso se veía en blanco)
        document.getElementById('modal-notas-estudiante').style.display = 'flex';

    } catch (error) {
        console.error('Error al obtener detalle de asignatura:', error);
        alert('Error al cargar el detalle de la asignatura');
    }
}

function cerrarModalNotas() {
    document.getElementById('modal-notas-estudiante').style.display = 'none';
}

// ==================== USUARIOS (ADMIN) ====================

async function cargarUsuarios() {
    if (userRole !== 'admin') {
        return;
    }
    
    const usuarios = await apiRequest('/usuarios');
    const tbody = document.querySelector('#tabla-usuarios tbody');
    tbody.innerHTML = '';
    
    usuarios.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td>${user.nombre}</td>
            <td>${user.email || '-'}</td>
            <td>${user.rol}</td>
            <td>${user.activo ? 'Activo' : 'Inactivo'}</td>
            <td>
                <button class="btn-edit" onclick="editarUsuario(${user.id})">Editar</button>
                <button class="btn-delete" onclick="eliminarUsuario(${user.id})">Eliminar</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function guardarUsuario(event) {
    event.preventDefault();
    
    const id = document.getElementById('usuario-id').value;
    const password = document.getElementById('usuario-password').value;
    const usuario = {
        username: document.getElementById('usuario-username').value,
        nombre: document.getElementById('usuario-nombre').value,
        email: document.getElementById('usuario-email').value,
        rol: document.getElementById('usuario-rol').value
    };
    
    // Validar contraseña al crear (id vacío = nuevo usuario)
    if (!id) {
        if (!password || password.trim() === '') {
            alert('La contraseña es obligatoria para crear un nuevo usuario');
            return;
        }
        usuario.password = password;
    } else if (password && password.trim() !== '') {
        // En edición, solo enviar contraseña si se proporcionó una nueva
        usuario.password = password;
    }
    
    try {
        if (id) {
            await apiRequest(`/usuarios/${id}`, 'PUT', usuario);
            alert('Usuario actualizado correctamente');
        } else {
            await apiRequest('/auth/register', 'POST', usuario);
            alert('Usuario creado correctamente');
        }
        limpiarFormUsuario();
        cargarUsuarios();
    } catch (error) {
        console.error('Error al guardar usuario:', error);
    }
}

async function editarUsuario(id) {
    const usuario = await apiRequest(`/usuarios/${id}`);
    document.getElementById('usuario-id').value = usuario.id;
    document.getElementById('usuario-username').value = usuario.username;
    document.getElementById('usuario-nombre').value = usuario.nombre;
    document.getElementById('usuario-email').value = usuario.email || '';
    document.getElementById('usuario-rol').value = usuario.rol;
    document.getElementById('usuario-password').value = '';
}

async function eliminarUsuario(id) {
    if (confirm('¿Está seguro de eliminar este usuario?')) {
        await apiRequest(`/usuarios/${id}`, 'DELETE');
        alert('Usuario eliminado correctamente');
        cargarUsuarios();
    }
}

function limpiarFormUsuario() {
    document.getElementById('form-usuario').reset();
    document.getElementById('usuario-id').value = '';
}