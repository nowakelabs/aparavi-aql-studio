/**
 * AQL Studio Visualization Manager
 * 
 * Handles rendering of different visualization types for query results
 */

class QueryVisualization {
    constructor() {
        this.currentVisualization = null;
        this.currentType = null;
        this.resultData = null;
        this.visualizationOptions = {};
    }

    /**
     * Initialize visualization area and bind event handlers
     */
    init() {
        // Create visualization tab if it doesn't exist
        if ($('#visualization-tab').length === 0) {
            $('#results-tabs').append(`
                <li class="nav-item">
                    <a class="nav-link" id="visualization-tab" data-toggle="tab" href="#visualization" role="tab">
                        <i class="fas fa-chart-pie me-2"></i> Visualization
                    </a>
                </li>
            `);

            $('#results-content').append(`
                <div class="tab-pane fade" id="visualization" role="tabpanel">
                    <div class="visualization-container">
                        <div class="row mb-3">
                            <div class="col-md-12 d-flex justify-content-between">
                                <div class="visualization-selector">
                                    <label for="visualization-type">Visualization Type:</label>
                                    <select id="visualization-type" class="form-select form-select-sm">
                                        <option value="" disabled selected>Select Visualization</option>
                                    </select>
                                </div>
                                <div class="visualization-options">
                                    <!-- Dynamic options will be added here -->
                                </div>
                            </div>
                        </div>
                        <div id="visualization-loading" class="text-center py-5" style="display: none;">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2">Generating visualization...</p>
                        </div>
                        <div id="visualization-error" class="alert alert-danger" style="display: none;"></div>
                        <div id="visualization-content"></div>
                    </div>
                </div>
            `);

            // Bind events
            $('#visualization-type').on('change', (e) => {
                const vizType = $(e.target).val();
                if (vizType) {
                    this.renderVisualizationOptions(vizType);
                    this.createVisualization(vizType);
                }
            });
        }
    }

    /**
     * Reset visualization area
     */
    reset() {
        this.currentVisualization = null;
        this.currentType = null;
        this.resultData = null;
        this.visualizationOptions = {};
        $('#visualization-content').empty();
        $('#visualization-type').val('');
        $('.visualization-options').empty();
        $('#visualization-error').hide();
    }

    /**
     * Handle new query results
     * @param {Object} data - Query result data
     */
    handleQueryResults(data) {
        this.reset();
        this.resultData = data;

        // Get available visualization types from server
        $.ajax({
            url: '/api/visualizations/available',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ results: data }),
            success: (response) => {
                if (response.success) {
                    this.updateVisualizationSelector(response.visualizations);
                    
                    // Automatically select table view by default
                    if (response.visualizations.includes('table')) {
                        $('#visualization-type').val('table').trigger('change');
                    }
                }
            },
            error: (xhr) => {
                console.error('Error getting visualization types:', xhr.responseText);
            }
        });
    }

    /**
     * Update visualization type selector dropdown
     * @param {Array} visualizations - Available visualization types
     */
    updateVisualizationSelector(visualizations) {
        const $select = $('#visualization-type');
        $select.empty();
        
        $select.append('<option value="" disabled selected>Select Visualization</option>');
        
        visualizations.forEach(vizType => {
            const displayName = this.getDisplayName(vizType);
            $select.append(`<option value="${vizType}">${displayName}</option>`);
        });
    }

    /**
     * Get human-readable name for visualization type
     * @param {string} vizType - Visualization type ID
     * @returns {string} Display name
     */
    getDisplayName(vizType) {
        const displayNames = {
            'table': 'Data Table',
            'sunburst': 'Sunburst Chart'
        };
        
        return displayNames[vizType] || vizType.charAt(0).toUpperCase() + vizType.slice(1);
    }

    /**
     * Render options for the selected visualization type
     * @param {string} vizType - Visualization type ID
     */
    renderVisualizationOptions(vizType) {
        const $optionsContainer = $('.visualization-options');
        $optionsContainer.empty();
        
        // Get visualization-specific options from server
        $.ajax({
            url: `/api/visualizations/${vizType}/options`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ results: this.resultData }),
            success: (response) => {
                if (response.success) {
                    this.visualizationOptions = response.options;
                    
                    // Render options based on visualization type
                    if (vizType === 'sunburst') {
                        this.renderSunburstOptions(response.options);
                    }
                }
            }
        });
    }

    /**
     * Render sunburst chart specific options
     * @param {Object} options - Sunburst options data
     */
    renderSunburstOptions(options) {
        const $optionsContainer = $('.visualization-options');
        
        // Path column selector
        const pathOptions = options.detected_path_columns || [];
        const allColumns = options.columns || [];
        
        const pathSelect = $('<select id="sunburst-path-column" class="form-select form-select-sm me-2"></select>');
        pathSelect.append('<option value="" disabled>Select Path Column</option>');
        
        // Add detected path columns first
        if (pathOptions.length > 0) {
            pathOptions.forEach(col => {
                pathSelect.append(`<option value="${col}" ${pathOptions[0] === col ? 'selected' : ''}>${col}</option>`);
            });
        }
        
        // Add all other columns
        allColumns.filter(col => !pathOptions.includes(col)).forEach(col => {
            pathSelect.append(`<option value="${col}">${col}</option>`);
        });
        
        // Value column selector
        const valueOptions = options.detected_value_columns || [];
        
        const valueSelect = $('<select id="sunburst-value-column" class="form-select form-select-sm"></select>');
        valueSelect.append('<option value="">None (Count)</option>');
        
        // Add detected value columns first
        if (valueOptions.length > 0) {
            valueOptions.forEach(col => {
                valueSelect.append(`<option value="${col}" ${valueOptions[0] === col ? 'selected' : ''}>${col}</option>`);
            });
        }
        
        // Add all other columns
        allColumns.filter(col => !valueOptions.includes(col)).forEach(col => {
            valueSelect.append(`<option value="${col}">${col}</option>`);
        });
        
        // Create option containers
        const pathContainer = $('<div class="me-3"></div>').append('<label class="me-2">Path Column:</label>').append(pathSelect);
        const valueContainer = $('<div></div>').append('<label class="me-2">Value Column:</label>').append(valueSelect);
        
        $optionsContainer.append(pathContainer).append(valueContainer);
        
        // Bind change events to update visualization
        pathSelect.add(valueSelect).on('change', () => {
            this.createVisualization('sunburst');
        });
    }

    /**
     * Create visualization with the selected type
     * @param {string} vizType - Visualization type ID
     */
    createVisualization(vizType) {
        $('#visualization-loading').show();
        $('#visualization-content').empty();
        $('#visualization-error').hide();
        
        // Get options for the selected visualization type
        const options = {};
        
        if (vizType === 'sunburst') {
            options.path_column = $('#sunburst-path-column').val();
            options.value_column = $('#sunburst-value-column').val();
        }
        
        // Request visualization from server
        $.ajax({
            url: `/api/visualizations/${vizType}/create`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                results: this.resultData,
                options: options
            }),
            success: (response) => {
                $('#visualization-loading').hide();
                
                if (response.success) {
                    this.currentType = vizType;
                    this.renderVisualization(vizType, response.data);
                } else {
                    $('#visualization-error').text(response.error || 'Failed to create visualization').show();
                }
            },
            error: (xhr) => {
                $('#visualization-loading').hide();
                $('#visualization-error').text('Server error: ' + (xhr.responseText || 'Unknown error')).show();
                console.error('Error creating visualization:', xhr);
            }
        });
    }

    /**
     * Render the visualization in the container
     * @param {string} vizType - Visualization type ID
     * @param {Object} data - Visualization data
     */
    renderVisualization(vizType, data) {
        const $container = $('#visualization-content');
        
        if (vizType === 'sunburst') {
            // Create container for the chart
            $container.html('<div id="sunburst-chart"></div>');
            
            // Parse the Plotly figure data
            const figure = JSON.parse(data.plotly_figure);
            
            // Render the sunburst chart
            Plotly.newPlot('sunburst-chart', figure.data, figure.layout, {responsive: true});
        }
        else if (vizType === 'table') {
            // Table view is already handled by the main results table
            $container.html('<p class="text-center">Table view is available in the Results tab.</p>');
        }
    }
}

// Initialize the visualization manager when document is ready
$(document).ready(() => {
    // Create global visualization manager instance
    window.queryVisualization = new QueryVisualization();
    window.queryVisualization.init();
    
    // Hook into existing query result handler
    const originalHandleResults = window.handleQueryResults;
    
    // Override the function to also update visualizations
    window.handleQueryResults = function(data) {
        // Call the original function first
        if (originalHandleResults) {
            originalHandleResults(data);
        }
        
        // Then update visualizations
        window.queryVisualization.handleQueryResults(data);
    };
});
