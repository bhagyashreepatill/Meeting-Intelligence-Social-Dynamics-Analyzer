/**
 * Interactive Social Graph Engine using Cytoscape.js
 */

class SocialGraphRenderer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.cy = null;
  }

  render(graphData) {
    if (!this.container || typeof cytoscape === 'undefined') return;

    const elements = [];

    // Map Nodes
    (graphData.nodes || []).forEach(node => {
      elements.push({
        data: {
          id: node.id,
          label: node.label,
          color: node.color || '#6366f1',
          size: node.size || 40,
          speakingTime: node.speaking_time,
          speakingPct: node.speaking_percentage,
          turnCount: node.turn_count,
          interruptionsMade: node.interruptions_made,
          interruptionsReceived: node.interruptions_received
        }
      });
    });

    // Map Edges
    (graphData.edges || []).forEach(edge => {
      let edgeColor = '#6366f1';
      let lineStyle = 'solid';

      if (edge.type === 'INTERRUPTION') {
        edgeColor = '#f43f5e';
      } else if (edge.type === 'DIRECT_REPLY') {
        edgeColor = '#06b6d4';
      } else if (edge.type === 'IDEA_OVERLAP') {
        edgeColor = '#a855f7';
        lineStyle = 'dashed';
      }

      elements.push({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: edge.type,
          weight: edge.weight,
          label: edge.label || '',
          color: edgeColor,
          lineStyle: lineStyle,
          width: Math.min(6, Math.max(1.5, edge.width || 2))
        }
      });
    });

    if (this.cy) {
      this.cy.destroy();
    }

    this.cy = cytoscape({
      container: this.container,
      elements: elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            'label': 'data(label)',
            'color': '#f8fafc',
            'font-family': 'Outfit, sans-serif',
            'font-size': '12px',
            'font-weight': '600',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'width': 'data(size)',
            'height': 'data(size)',
            'border-width': 2,
            'border-color': 'rgba(255, 255, 255, 0.4)',
            'transition-property': 'background-color, border-color, width, height, border-width',
            'transition-duration': '0.3s'
          }
        },
        {
          selector: 'node.speaking-now',
          style: {
            'border-color': '#06b6d4',
            'border-width': 5,
            'shadow-blur': 25,
            'shadow-color': '#06b6d4',
            'shadow-opacity': 0.8
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'data(width)',
            'line-color': 'data(color)',
            'target-arrow-color': 'data(color)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'line-style': 'data(lineStyle)',
            'arrow-scale': 1.2,
            'opacity': 0.75
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'opacity': 1.0,
            'width': 6
          }
        }
      ],
      layout: {
        name: 'circle',
        padding: 50,
        animate: false
      }
    });

    // Node click handler
    this.cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const data = node.data();
      if (window.showNodeDetailsModal) {
        window.showNodeDetailsModal(data);
      }
    });
  }

  highlightSpeaker(activeSpeaker) {
    if (!this.cy) return;
    this.cy.nodes().forEach(node => {
      if (node.id() === activeSpeaker) {
        node.addClass('speaking-now');
      } else {
        node.removeClass('speaking-now');
      }
    });
  }

  updateNodeSizes(cumulativePercentages) {
    if (!this.cy || !cumulativePercentages) return;
    this.cy.nodes().forEach(node => {
      const id = node.id();
      const pct = cumulativePercentages[id] || 0;
      const newSize = Math.max(26, Math.min(65, 26 + (pct / 100) * 45));
      node.style({ 'width': newSize, 'height': newSize });
    });
  }
}
