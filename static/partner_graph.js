// Cytoscape Partner Graph Implementation
// Based on cytoscape-fcose documentation: https://github.com/iVis-at-Bilkent/cytoscape.js-fcose

function initializePartnerGraph(elementsJson) {
    console.log('Initializing partner graph...');
    let waitTimeout = 0;
    const MAX_WAIT_TIME = 10000; // 10 seconds

    function waitForDependencies(callback) {
        waitTimeout += 100;
        if (waitTimeout > MAX_WAIT_TIME) {
            console.error('Timeout waiting for fcose extension. Proceeding with default cose layout.');
            renderGraphWithFallback(elementsJson);
            return;
        }
        if (typeof cytoscape !== 'undefined' && 
            (typeof window.cytoscapeFcose !== 'undefined' || typeof cytoscapeFcose !== 'undefined')) {
            console.log('All dependencies loaded successfully');
            console.log('cytoscape:', typeof cytoscape);
            console.log('window.cytoscapeFcose:', typeof window.cytoscapeFcose);
            console.log('cytoscapeFcose (global):', typeof cytoscapeFcose);
            callback();
        } else {
            console.log('Waiting for dependencies... (timeout in ' + (MAX_WAIT_TIME - waitTimeout) + 'ms)');
            console.log('cytoscape:', typeof cytoscape);
            console.log('window.cytoscapeFcose:', typeof window.cytoscapeFcose);
            console.log('cytoscapeFcose (global):', typeof cytoscapeFcose);
            console.log('layout-base:', typeof layoutBase);
            console.log('cose-base:', typeof coseBase);
            setTimeout(() => waitForDependencies(callback), 100);
        }
    }

    waitForDependencies(() => {
        // Register the fcose extension
        if (!cytoscape.prototype.layoutFcoseRegistered) {
            try {
                let fcoseExtension = null;
                if (typeof window.cytoscapeFcose !== 'undefined') {
                    fcoseExtension = window.cytoscapeFcose;
                    console.log('Found fcose extension in window.cytoscapeFcose');
                } else if (typeof cytoscapeFcose !== 'undefined') {
                    fcoseExtension = cytoscapeFcose;
                    console.log('Found fcose extension in global cytoscapeFcose');
                } else if (typeof window.fcose !== 'undefined') {
                    fcoseExtension = window.fcose;
                    console.log('Found fcose extension in window.fcose');
                }
                if (fcoseExtension) {
                    cytoscape.use(fcoseExtension);
                    cytoscape.prototype.layoutFcoseRegistered = true;
                    console.log('fcose extension registered successfully');
                } else {
                    console.error('fcose extension not found in any expected location');
                    console.log('Available globals:', Object.keys(window).filter(k => k.toLowerCase().includes('fcos')));
                }
            } catch (e) {
                console.error('Failed to register fcose extension:', e);
            }
        }
        // Initialize the graph
        renderGraph(elementsJson);
    });
}

function renderGraphWithFallback(elementsJson) {
    const elements = JSON.parse(elementsJson);
    console.log('Rendering graph with fallback cose layout');
    if (window.cy && window.cy.destroy) {
        window.cy.destroy();
    }
    window.cy = cytoscape({
        container: document.getElementById('cy'),
        elements: elements,
        style: getCytoscapeStyles(),
        layout: getCoseLayout()
    });
    console.log('Cytoscape instance created with fallback cose layout');
    setupEventHandlers();
}

function renderGraph(elementsJson) {
    const elements = JSON.parse(elementsJson);
    console.log('Rendering graph with', elements.length, 'elements');
    if (window.cy && window.cy.destroy) {
        window.cy.destroy();
    }
    window.cy = cytoscape({
        container: document.getElementById('cy'),
        elements: elements,
        style: getCytoscapeStyles(),
        layout: getFcoseLayout(),
    });
    console.log('Cytoscape instance created with fcose layout');
    setupEventHandlers();
}

function getCytoscapeStyles() {
    return [
        {
            selector: '$node > node',
            style: {
                'label': 'data(label)',
                'background-color': 'data(color)',
                'background-opacity': 0.15,
                'border-color': '#999',
                'border-width': 2,
                'border-opacity': 0.3,
                'padding': '12px',
                'font-size': 14,
                'color': '#333',
                'text-valign': 'center',
                'text-halign': 'center'
            }
        },
        {
            selector: 'node[count]',
            style: {
                'label': 'data(label)',
                'background-color': 'data(color)',
                'width': 'mapData(count, 1, 200, 20, 60)',
                'height': 'mapData(count, 1, 200, 20, 60)',
                'text-valign': 'center',
                'text-halign': 'center',
                'color': '#333',
                'font-size': 'mapData(count, 1, 200, 10, 14)',
                'text-outline-width': 1,
                'text-outline-color': '#fff',
                'border-color': '#666',
                'border-width': 1,
                'border-opacity': 0.5
            }
        },
        {
            selector: 'node.high-usage',
            style: {
                'border-width': 2,
                'border-color': '#4682B4'
            }
        },
        {
            selector: 'edge',
            style: {
                'width': 'mapData(weight, 1, 50, 1, 4)',
                'line-color': 'data(color)',
                'curve-style': 'bezier',
                'opacity': 0.6,
                'line-cap': 'round'
            }
        },
        {
            selector: '.faded',
            style: {
                'opacity': 0.2,
                'text-opacity': 0.3
            }
        }
    ];
}

function getFcoseLayout() {
    return {
        name: 'fcose',
        animate: true,
        animationDuration: 1000,
        randomize: false,
        fit: true,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 120,
        edgeElasticity: 0.2,
        gravity: 1,
        numIter: 1000,
        tile: true,
        quality: 'default',
        stop: function() {
            console.log('fcose layout completed');
        }
    };
}

function getCoseLayout() {
    return {
        name: 'cose',
        animate: true,
        animationDuration: 1000,
        randomize: false,
        fit: true,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 120,
        edgeElasticity: 0.2,
        gravity: 1,
        numIter: 1000,
        tile: true
    };
}

function setupEventHandlers() {
    function showMeta(html) {
        const panel = document.getElementById('meta_panel');
        if (panel) {
            panel.innerHTML = html;
        }
    }
    function focusOnNode(node) {
        const neighborhood = node.closedNeighborhood();
        const connectedNodes = node.connectedEdges().connectedNodes();
        node.style({
            'width': 120,
            'height': 120,
            'font-size': 22
        });
        connectedNodes.forEach(n => {
            n.style({
                'width': 60,
                'height': 60,
                'font-size': 18
            });
        });
        window.cy.animate({
            fit: { eles: neighborhood, padding: 60 },
            duration: 500
        });
        window.cy.nodes().not(neighborhood).style({
            'width': 20,
            'height': 20,
            'font-size': 12
        });
        window.cy.elements().removeClass('faded');
        window.cy.elements().not(neighborhood).addClass('faded');
        const d = node.data();
        showMeta(`<b>Partner:</b> ${d.label}<br><b>Playlist:</b> ${d.playlist}<br><b>Usage:</b> ${d.count}`);
    }
    // Node events
    window.cy.on('tap', 'node', function(evt) {
        const d = evt.target.data();
        showDetails(d);
    });
    window.cy.on('mouseover', 'node', function(evt) {
        const d = evt.target.data();
        showMeta(`<b>Partner:</b> ${d.label}<br><b>Playlist:</b> ${d.playlist}<br><b>Usage:</b> ${d.count}`);
    });
    window.cy.on('mouseout', 'node', function(evt) {
        showMeta('');
    });
    // Edge events
    window.cy.on('mouseover', 'edge', function(evt) {
        const d = evt.target.data();
        showMeta(`<b>Edge:</b> ${d.source} - ${d.target}<br><b>Shared clips:</b> ${d.clips}<br><b>Shared films:</b> ${d.films}`);
    });
    window.cy.on('mouseout', 'edge', function(evt) {
        showMeta('');
    });
    window.cy.on('tap', 'edge', function(evt) {
        const d = evt.target.data();
        showDetails(d);
    });
    // Layout events
    window.cy.on('layoutstop', function() {
        console.log('Layout completed');
        window.cy.fit(null, 50);
    });
    window.cy.on('layoutstart', function() {
        console.log('Layout started');
    });
    window.cy.on('layouterror', function(event) {
        console.error('Layout error:', event);
    });
} 