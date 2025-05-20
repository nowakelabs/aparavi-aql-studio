/**
 * Aparaviz - Data Visualization Dashboard for Aparavi
 * 
 * This script handles loading data from the DuckDB database and 
 * rendering an interactive sunburst visualization.
 */

// Global variables
let folderData = [];
let currentVisualization = null;

// Format bytes to human-readable size
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
}

// Load data from the API
function loadData() {
    // Show loading state
    $('#loading-container').show();
    $('#error-container').hide();
    $('#visualization-content').hide();
    
    // Fetch data from the API
    fetch('/api/aparaviz/data')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data && data.data.length > 0) {
                handleDataLoaded(data);
            } else {
                showError(data.error || 'No data available', data);
            }
        })
        .catch(error => {
            showError('Error loading data: ' + error.message);
        });
}

// Handle successful data load
function handleDataLoaded(response) {
    // Filter out the root object "File System/" as it doesn't provide value
    folderData = response.data.filter(folder => {
        // Skip the root "File System/" folder
        return folder.path !== 'File System/' && folder.path !== 'File System';
    });
    
    // Log data to console for debugging
    console.log('Loaded folder data (filtered):', folderData);
    console.log('Database tables:', response.tables);
    
    // Hide loading and error containers
    $('#loading-container').hide();
    $('#error-container').hide();
    
    // Calculate statistics
    const totalFolders = folderData.length;
    let totalFiles = 0;
    let totalSize = 0;
    
    folderData.forEach(folder => {
        // Ensure we're getting numeric values with fallbacks
        const fileCount = parseInt(folder.file_count || 0);
        const folderSize = parseFloat(folder.total_size || 0);
        
        totalFiles += fileCount;
        totalSize += folderSize;
        
        // Add to debug output
        console.log(`Folder: ${folder.path}, Files: ${fileCount}, Size: ${folderSize}`);
    });
    
    console.log(`Total stats - Folders: ${totalFolders}, Files: ${totalFiles}, Size: ${totalSize}`);
    
    // Update statistics
    $('#total-folders').text(totalFolders.toLocaleString());
    $('#total-files').text(totalFiles.toLocaleString());
    $('#total-size').text(formatBytes(totalSize));
    
    // Create visualization
    createVisualization();
    
    // Show the visualization container
    $('#visualization-content').show();
}

// Show error message
function showError(message, details = null) {
    $('#loading-container').hide();
    $('#visualization-content').hide();
    $('#error-container').show();
    
    $('#error-message').text(message);
    
    if (details) {
        let detailsText = JSON.stringify(details, null, 2);
        $('#db-info').text(detailsText);
    }
}

// Create the sunburst visualization
function createVisualization() {
    // Get current settings
    const maxDepth = parseInt($('#depth-selector').val()) || 5;
    const metric = $('#metric-selector').val() || 'file_count';
    
    // Prepare the data for sunburst visualization
    const { labels, parents, values, paths } = prepareHierarchyData(folderData, metric, maxDepth);
    
    // Create the sunburst chart
    const data = [{
        type: 'sunburst',
        labels: labels,
        parents: parents,
        values: values,
        outsidetextfont: { size: 20, color: '#377eb8' },
        leaf: { opacity: 0.7 },
        marker: { line: { width: 2 } },
        branchvalues: 'total',
        hovertemplate: '<b>%{label}</b><br>Value: %{value}<br>Path: %{customdata}<extra></extra>',
        customdata: paths,
        // Set initial maxdepth
        maxdepth: maxDepth
    }];
    
    const layout = {
        margin: { l: 0, r: 0, b: 0, t: 30 },
        title: metric === 'file_count' ? 'File Count by Folder' : 'Storage Size by Folder',
        sunburstcolorway: [
            '#636efa', '#EF553B', '#00cc96', '#ab63fa', '#19d3f3',
            '#e763fa', '#fecb52', '#ffa15a', '#ff6692', '#b6e880'
        ],
        height: 600,
    };
    
    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        displaylogo: false
    };
    
    // Render the chart
    Plotly.newPlot('sunburst-chart', data, layout, config);
    
    // Add click event to handle drill-down
    document.getElementById('sunburst-chart').on('plotly_click', function(data) {
        const point = data.points[0];
        updateBreadcrumbs(point.customdata || 'Root');
    });
}

// Prepare hierarchical data for sunburst visualization
function prepareHierarchyData(data, metricName, maxDepth) {
    // Initialize arrays for sunburst chart data
    // Note: We're no longer showing the root "File System/" folder
    let rootLabel = "Aparavi Data";
    const labels = [rootLabel];  // Start with custom root node
    const parents = [''];     // Root has no parent
    const values = [0];       // Initialize root value
    const paths = [''];       // Path for root
    
    // Process each folder
    data.forEach(folder => {
        let path = folder.path || '';
        if (!path) return;
        
        // Get the value based on the selected metric
        const value = metricName === 'file_count' 
            ? (folder.file_count || 0) 
            : (folder.total_size || 0);
        
        // Add value to root's total
        values[0] += value;
        
        // Split path into components
        const pathComponents = path.split('/').filter(p => p);
        
        // Limit depth if needed
        const limitedComponents = pathComponents.slice(0, maxDepth);
        
        // Process each level of the path
        let currentPath = "";
        let parentLabel = "Aparavi Data";
        
        for (let i = 0; i < limitedComponents.length; i++) {
            const component = limitedComponents[i];
            if (!component) continue; // Skip empty components
            
            // Build the current path
            if (currentPath === "") {
                currentPath = component;
            } else {
                currentPath = `${currentPath}/${component}`;
            }
            
            // Create a label for this level
            const label = component;
            
            // Check if this node already exists
            const existingIndex = labels.indexOf(label + " [" + currentPath + "]");
            
            if (existingIndex !== -1) {
                // Node exists, just add the value
                values[existingIndex] += value;
            } else {
                // Node doesn't exist, add it with a unique label that includes the path
                labels.push(label + " [" + currentPath + "]");
                parents.push(parentLabel);
                values.push(value);
                paths.push(currentPath);
            }
            
            // Update the parent for the next level
            parentLabel = label + " [" + currentPath + "]";
        }
    });
    
    return { labels, parents, values, paths };
}

// Update the breadcrumb navigation
function updateBreadcrumbs(path) {
    // Reset breadcrumbs
    const $breadcrumb = $('#path-breadcrumb');
    $breadcrumb.empty();
    
    // Always add root with our custom label
    $breadcrumb.append('<li class="breadcrumb-item"><a href="#" data-path="">Aparavi Data</a></li>');
    
    // If path is empty or matches root label, we're done
    if (!path || path === 'Aparavi Data' || path === 'Root') {
        return;
    }
    
    // Remove File System/ prefix if present
    if (path.startsWith('File System/')) {
        path = path.substring('File System/'.length);
    }
    
    // Split path into components
    const components = path.split('/').filter(p => p);
    
    // Build breadcrumb
    let currentPath = '';
    components.forEach((component, i) => {
        currentPath = currentPath ? `${currentPath}/${component}` : component;
        const isLast = i === components.length - 1;
        
        if (isLast) {
            $breadcrumb.append(`<li class="breadcrumb-item active">${component}</li>`);
        } else {
            $breadcrumb.append(`<li class="breadcrumb-item"><a href="#" data-path="${currentPath}">${component}</a></li>`);
        }
    });
    
    // Add click event to breadcrumb links
    $breadcrumb.find('a').on('click', function(e) {
        e.preventDefault();
        const path = $(this).data('path');
        updateBreadcrumbs(path);
    });
}

// Initialize all event handlers
function initEventHandlers() {
    // Depth selector change
    $('#depth-selector').on('change', function() {
        createVisualization();
    });
    
    // Metric selector change
    $('#metric-selector').on('change', function() {
        createVisualization();
    });
}

// Initialize the page
$(document).ready(function() {
    // Initialize with depth 5 by default
    $('#depth-selector').val(5);
    
    // Initialize events
    initEventHandlers();
    
    // Load data
    loadData();
});
