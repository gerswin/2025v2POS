/**
 * JavaScript for Zone Form with Variable Row Configuration
 */

document.addEventListener('DOMContentLoaded', function() {
    const zoneTypeField = document.getElementById('id_zone_type');
    const useVariableRowsField = document.getElementById('id_use_variable_rows');
    const rowsField = document.getElementById('id_rows');
    const seatsPerRowField = document.getElementById('id_seats_per_row');
    const capacityField = document.getElementById('id_capacity');
    const rowConfigJsonField = document.getElementById('id_row_config_json');
    
    let rowConfiguration = {};
    
    // Initialize
    if (zoneTypeField) {
        toggleZoneTypeFields();
        zoneTypeField.addEventListener('change', toggleZoneTypeFields);
    }
    
    if (useVariableRowsField) {
        toggleVariableRowsFields();
        useVariableRowsField.addEventListener('change', toggleVariableRowsFields);
    }
    
    if (rowsField) {
        rowsField.addEventListener('input', updateRowConfiguration);
    }
    
    if (seatsPerRowField) {
        seatsPerRowField.addEventListener('input', calculateCapacity);
    }
    
    // Load existing configuration if present
    if (rowConfigJsonField && rowConfigJsonField.value) {
        try {
            rowConfiguration = JSON.parse(rowConfigJsonField.value);
        } catch (e) {
            console.error('Error parsing row configuration:', e);
        }
    }
    
    function toggleZoneTypeFields() {
        const isNumbered = zoneTypeField.value === 'numbered';
        const numberedFields = document.querySelectorAll('.numbered-zone-field');
        
        numberedFields.forEach(field => {
            field.style.display = isNumbered ? 'block' : 'none';
        });
        
        if (isNumbered) {
            updateRowConfiguration();
        }
    }
    
    function toggleVariableRowsFields() {
        const useVariable = useVariableRowsField.checked;
        const variableContainer = document.getElementById('variable-rows-container');
        
        if (variableContainer) {
            variableContainer.style.display = useVariable ? 'block' : 'none';
        }
        
        if (useVariable) {
            updateRowConfiguration();
        } else {
            rowConfiguration = {};
            updateRowConfigJson();
            calculateCapacity();
        }
    }
    
    function updateRowConfiguration() {
        const rows = parseInt(rowsField.value) || 0;
        const useVariable = useVariableRowsField.checked;
        
        if (!useVariable || rows === 0) {
            return;
        }
        
        // Create or update row configuration container
        let container = document.getElementById('variable-rows-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'variable-rows-container';
            container.className = 'mt-3';
            useVariableRowsField.closest('.form-group').after(container);
        }
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0">
                        <i class="fas fa-cog"></i> Configuración de Asientos por Fila
                    </h6>
                </div>
                <div class="card-body">
                    <div class="row" id="row-inputs">
                        ${generateRowInputs(rows)}
                    </div>
                    <div class="mt-3">
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="fillAllRows()">
                            <i class="fas fa-fill"></i> Llenar Todas
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-secondary" onclick="resetRowConfig()">
                            <i class="fas fa-undo"></i> Resetear
                        </button>
                        <span class="ms-3 text-muted">
                            Total calculado: <strong id="calculated-total">0</strong> asientos
                        </span>
                    </div>
                </div>
            </div>
        `;
        
        // Add event listeners to new inputs
        container.querySelectorAll('.row-seats-input').forEach(input => {
            input.addEventListener('input', onRowSeatsChange);
        });
        
        calculateVariableCapacity();
    }
    
    function generateRowInputs(rows) {
        let html = '';
        const defaultSeats = parseInt(seatsPerRowField.value) || 10;
        
        for (let i = 1; i <= rows; i++) {
            const currentValue = rowConfiguration[i.toString()] || defaultSeats;
            
            html += `
                <div class="col-md-3 col-sm-4 col-6 mb-3">
                    <label class="form-label">Fila ${i}</label>
                    <input type="number" 
                           class="form-control form-control-sm row-seats-input" 
                           data-row="${i}"
                           value="${currentValue}"
                           min="1" 
                           placeholder="Asientos">
                </div>
            `;
        }
        
        return html;
    }
    
    function onRowSeatsChange(event) {
        const row = event.target.dataset.row;
        const seats = parseInt(event.target.value) || 0;
        
        if (seats > 0) {
            rowConfiguration[row] = seats;
        } else {
            delete rowConfiguration[row];
        }
        
        updateRowConfigJson();
        calculateVariableCapacity();
    }
    
    function calculateVariableCapacity() {
        const rows = parseInt(rowsField.value) || 0;
        const defaultSeats = parseInt(seatsPerRowField.value) || 0;
        let total = 0;
        
        for (let i = 1; i <= rows; i++) {
            const rowSeats = rowConfiguration[i.toString()] || defaultSeats;
            total += rowSeats;
        }
        
        capacityField.value = total;
        
        const calculatedTotalElement = document.getElementById('calculated-total');
        if (calculatedTotalElement) {
            calculatedTotalElement.textContent = total;
        }
    }
    
    function calculateCapacity() {
        if (!useVariableRowsField.checked) {
            const rows = parseInt(rowsField.value) || 0;
            const seatsPerRow = parseInt(seatsPerRowField.value) || 0;
            capacityField.value = rows * seatsPerRow;
        }
    }
    
    function updateRowConfigJson() {
        rowConfigJsonField.value = JSON.stringify(rowConfiguration);
    }
    
    // Global functions for buttons
    window.fillAllRows = function() {
        const defaultSeats = prompt('¿Cuántos asientos por fila?', seatsPerRowField.value || '10');
        if (defaultSeats && !isNaN(defaultSeats)) {
            const seats = parseInt(defaultSeats);
            document.querySelectorAll('.row-seats-input').forEach(input => {
                input.value = seats;
                rowConfiguration[input.dataset.row] = seats;
            });
            updateRowConfigJson();
            calculateVariableCapacity();
        }
    };
    
    window.resetRowConfig = function() {
        if (confirm('¿Resetear la configuración de filas?')) {
            rowConfiguration = {};
            updateRowConfigJson();
            updateRowConfiguration();
        }
    };
    
    // Auto-fill row configuration when rows or seats_per_row changes
    if (rowsField && seatsPerRowField) {
        [rowsField, seatsPerRowField].forEach(field => {
            field.addEventListener('input', function() {
                if (useVariableRowsField.checked) {
                    updateRowConfiguration();
                } else {
                    calculateCapacity();
                }
            });
        });
    }
});