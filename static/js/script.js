document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const excelFile = document.getElementById('excelFile');
    const analyzeButton = document.getElementById('analyze-button');
    const fileError = document.getElementById('file-error');
    const resultsArea = document.getElementById('results-area');
    const messageArea = document.getElementById('message-area');
    const criticalWellsTableBody = document.querySelector('#critical-wells-table tbody');
    const graphsContainer = document.getElementById('graphs-container');
    const spinner = analyzeButton.querySelector('.spinner-border');
    const downloadCriticalExcelBtn = document.getElementById('download-critical-excel');

    // Valida la extensión del archivo antes de habilitar el botón de análisis
    excelFile.addEventListener('change', () => {
        const file = excelFile.files[0];
        if (file) {
            const fileName = file.name;
            const fileExtension = fileName.split('.').pop().toLowerCase();
            if (fileExtension === 'xlsx') {
                analyzeButton.disabled = false;
                fileError.style.display = 'none';
                fileError.textContent = '';
            } else {
                analyzeButton.disabled = true;
                fileError.style.display = 'block';
                fileError.textContent = 'Por favor, selecciona un archivo Excel con extensión .xlsx';
            }
        } else {
            analyzeButton.disabled = true;
            fileError.style.display = 'none';
            fileError.textContent = '';
        }
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Evita la recarga de la página

        const file = excelFile.files[0];
        if (!file) {
            alert('Por favor, selecciona un archivo Excel.');
            return;
        }

        // Mostrar spinner y deshabilitar botón
        spinner.style.display = 'inline-block';
        analyzeButton.disabled = true;
        analyzeButton.classList.add('loading'); // Añadir clase para estilos de carga
        resultsArea.style.display = 'none'; // Ocultar resultados anteriores
        messageArea.style.display = 'none';
        messageArea.textContent = '';
        criticalWellsTableBody.innerHTML = ''; // Limpiar tabla
        graphsContainer.innerHTML = ''; // Limpiar gráficos
        downloadCriticalExcelBtn.style.display = 'none';


        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                // Manejo de errores del servidor
                messageArea.textContent = data.error || 'Ocurrió un error al procesar el archivo.';
                messageArea.className = 'alert alert-danger';
                messageArea.style.display = 'block';
                resultsArea.style.display = 'block'; // Mostrar el área para el mensaje de error
                return;
            }

            // Mostrar mensaje de éxito o informativos
            if (data.message) {
                messageArea.textContent = data.message;
                messageArea.className = 'alert alert-info';
                messageArea.style.display = 'block';
            } else {
                messageArea.style.display = 'none';
            }

            // Mostrar tabla de pozos críticos
            if (data.results && data.results.length > 0) {
                data.results.forEach(pozo => {
                    const row = criticalWellsTableBody.insertRow();
                    row.innerHTML = `
                        <td>${pozo['Nombre del Pozo']}</td>
                        <td>${pozo['Campo']}</td>
                        <td>${pozo['Caudal Inicial'].toFixed(2)}</td>
                        <td>${pozo['Caudal Actual'].toFixed(2)}</td>
                        <td>${pozo['Promedio Histórico'].toFixed(2)}</td>
                        <td>${pozo['% Caída'].toFixed(2)}%</td>
                        <td><span class="badge ${pozo['Estado'] === 'Crítico' ? 'bg-danger' : 'bg-success'}">${pozo['Estado']}</span></td>
                    `;
                });
                // Habilitar y mostrar botón de descarga de Excel de pozos críticos
                downloadCriticalExcelBtn.href = `/download_excel/${data.excel_criticos_download}`;
                downloadCriticalExcelBtn.style.display = 'inline-block';

            } else {
                const row = criticalWellsTableBody.insertRow();
                row.innerHTML = `<td colspan="7" class="text-center">No se detectaron pozos críticos con una caída superior al 20%.</td>`;
            }

            // Mostrar gráficos
            if (data.graph_paths && data.graph_paths.length > 0) {
                data.graph_paths.forEach(graphFilename => {
                    const graphUrl = `/graficos/${graphFilename}`;
                    const colDiv = document.createElement('div');
                    colDiv.className = 'col';
                    colDiv.innerHTML = `
                        <div class="card h-100 shadow-sm graph-card">
                            <div class="card-body text-center">
                                <h6 class="card-title">${graphFilename.replace('Pozo_', '').replace('.png', '').replace(/_/g, ' ')}</h6>
                                <img src="${graphUrl}" alt="Gráfico del Pozo" class="img-fluid mb-2" style="cursor: pointer;" data-bs-toggle="modal" data-bs-target="#imageModal" data-bs-src="${graphUrl}">
                                <a href="${graphUrl}" download="${graphFilename}" class="btn btn-outline-primary btn-sm">Descargar Gráfico</a>
                            </div>
                        </div>
                    `;
                    graphsContainer.appendChild(colDiv);
                });
            } else {
                 const colDiv = document.createElement('div');
                 colDiv.className = 'col-12 text-center text-muted';
                 colDiv.innerHTML = '<p>No se generaron gráficos. Esto puede ocurrir si no hay pozos críticos o datos válidos para graficar.</p>';
                 graphsContainer.appendChild(colDiv);
            }

            resultsArea.style.display = 'block'; // Mostrar toda el área de resultados

        } catch (error) {
            console.error('Error al subir el archivo:', error);
            messageArea.textContent = 'Error de conexión o del servidor: ' + error.message;
            messageArea.className = 'alert alert-danger';
            messageArea.style.display = 'block';
            resultsArea.style.display = 'block';
        } finally {
            // Ocultar spinner y habilitar botón
            spinner.style.display = 'none';
            analyzeButton.disabled = false;
            analyzeButton.classList.remove('loading');
        }
    });

    // --- Modal para visualizar gráficos grandes ---
    const imageModal = new bootstrap.Modal(document.getElementById('imageModal'), {});
    const modalImage = document.getElementById('modalImage');

    document.getElementById('graphs-container').addEventListener('click', function(event) {
        if (event.target.tagName === 'IMG' && event.target.dataset.bsSrc) {
            modalImage.src = event.target.dataset.bsSrc;
            imageModal.show();
        }
    });

    // Añadir el modal HTML al body (o donde desees en index.html)
    const modalHtml = `
        <div class="modal fade" id="imageModal" tabindex="-1" aria-labelledby="imageModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="imageModalLabel">Vista Previa del Gráfico</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body text-center">
                        <img id="modalImage" src="" alt="Gráfico del Pozo en Modal" class="img-fluid">
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml); // Inserta el modal al final del body
});