'use client';

import { useEffect, useRef, useState } from 'react';

interface FamilyGraphProps {
  treeData: any;
  personId: string;
}

export default function FamilyGraph({ treeData, personId }: FamilyGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || !treeData) return;

    // Wait for container to be fully mounted with dimensions
    const checkReady = () => {
      if (containerRef.current && containerRef.current.offsetWidth > 0) {
        setIsReady(true);
      } else {
        setTimeout(checkReady, 100);
      }
    };
    checkReady();
  }, [treeData]);

  useEffect(() => {
    if (!containerRef.current || !treeData || !isReady) return;

    const initializeGraph = async () => {
      try {
        // Dynamically import Sigma and Graphology
        const { default: Graph } = await import('graphology');
        const { default: Sigma } = await import('sigma');

        const container = containerRef.current;
        if (!container) return;

        // Clear container
        container.innerHTML = '';

        // Create wrapper structure
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'position: absolute; inset: 0; display: flex; flex-direction: column;';

        // Toolbar
        const toolbar = document.createElement('div');
        toolbar.style.cssText = `
          flex: 0 0 52px;
          padding: 10px 14px;
          border-bottom: 1px solid #eee;
          display: flex;
          gap: 12px;
          align-items: center;
          background: white;
        `;
        toolbar.innerHTML = `
          <div style="font-weight: 600; color: #DAA520;">Family Tree</div>
          <div style="margin-left: auto; display: flex; gap: 8px;">
            <button id="reset-btn" style="background-color: #DAA520; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: 600; cursor: pointer;">Reset</button>
            <button id="fit-btn" style="background-color: #DAA520; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: 600; cursor: pointer;">Fit</button>
            <button id="fullscreen-btn" style="background-color: #DAA520; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: 600; cursor: pointer;">Full Screen</button>
          </div>
        `;

        // Graph container
        const graphContainer = document.createElement('div');
        graphContainer.id = 'sigma-container';
        graphContainer.style.cssText = 'flex: 1; position: relative; background: #f7f4f1;';

        wrapper.appendChild(toolbar);
        wrapper.appendChild(graphContainer);
        container.appendChild(wrapper);

        // Create graph
        const graph = new Graph({ multi: false, allowSelfLoops: false });

        // Layout constants
        const UNIT = 120;
        const GAP = 3.2;
        const Y = { GP: -3.6, P: -1.8, MID: 0, C: 1.8, GC: 3.6 };

        // Build adjacency
        const parentsOf = new Map();
        const childrenOf = new Map();
        const spousesOf = new Map();

        (treeData.edges || []).forEach((e: any) => {
          if (!e || !e.source || !e.target) return;
          const type = String(e.type || '').toUpperCase();
          if (type === 'CHILD_OF') {
            if (!parentsOf.has(e.source)) parentsOf.set(e.source, new Set());
            parentsOf.get(e.source).add(e.target);
            if (!childrenOf.has(e.target)) childrenOf.set(e.target, new Set());
            childrenOf.get(e.target).add(e.source);
          } else if (type === 'SPOUSE_OF') {
            if (!spousesOf.has(e.source)) spousesOf.set(e.source, new Set());
            spousesOf.get(e.source).add(e.target);
            if (!spousesOf.has(e.target)) spousesOf.set(e.target, new Set());
            spousesOf.get(e.target).add(e.source);
          }
        });

        const root = treeData.root || personId;
        const idMap = new Map(treeData.nodes.map((n: any) => [n.id, n]));

        // Simple layout
        const coords = new Map();
        const spouses = Array.from(spousesOf.get(root) || []);
        const parents = Array.from(parentsOf.get(root) || []);
        const children = Array.from(childrenOf.get(root) || []);

        // Root
        coords.set(root, { x: 0, y: Y.MID });

        // Spouses
        spouses.forEach((s, i) => {
          coords.set(s, { x: (i + 1) * GAP, y: Y.MID });
        });

        // Parents
        const father = parents.find(p => (idMap.get(p) as any)?.sex === 'M') || parents[0];
        const mother = parents.find(p => (idMap.get(p) as any)?.sex === 'F') || parents[1];
        if (father) coords.set(father, { x: -0.9 * GAP, y: Y.P });
        if (mother) coords.set(mother, { x: 0.9 * GAP, y: Y.P });

        // Children
        children.forEach((c, i) => {
          const offset = (i - (children.length - 1) / 2) * GAP;
          coords.set(c, { x: offset, y: Y.C });
        });

        // Add nodes to graph
        const explicit = new Set([root, ...spouses, ...parents, ...children].filter(Boolean));
        explicit.forEach((id) => {
          const c = coords.get(id) || { x: 0, y: 0 };
          graph.addNode(id, {
            x: c.x * UNIT,
            y: c.y * UNIT,
            size: 8,
            color: '#00000000',
          });
        });

        // Wait for container to have dimensions
        await new Promise(resolve => setTimeout(resolve, 50));

        // Ensure container has dimensions
        if (!graphContainer.clientWidth || !graphContainer.clientHeight) {
          console.warn('Graph container not ready');
          setError('Graph container not ready. Please refresh the page.');
          return;
        }

        // Render sigma
        const renderer = new Sigma(graph, graphContainer, {
          renderLabels: false,
          enableEdgeClickEvents: false,
          allowInvalidContainer: true,
        });

        // Create overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position: absolute; inset: 0; pointer-events: none; z-index: 10;';

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.style.cssText = 'position: absolute; inset: 0;';

        const nodeLayer = document.createElement('div');
        nodeLayer.style.cssText = 'position: absolute; inset: 0;';

        overlay.appendChild(svg);
        overlay.appendChild(nodeLayer);
        graphContainer.appendChild(overlay);

        // Draw function
        const draw = () => {
          // Clear
          svg.innerHTML = '';
          nodeLayer.innerHTML = '';

          // Draw edges
          (treeData.edges || []).forEach((e: any) => {
            if (!explicit.has(e.source) || !explicit.has(e.target)) return;

            const camera = renderer.getCamera();
            const { x: cx, y: cy, ratio: z } = camera.getState();
            const w = graphContainer.clientWidth || 800;
            const h = graphContainer.clientHeight || 600;

            const sx = graph.getNodeAttribute(e.source, 'x');
            const sy = graph.getNodeAttribute(e.source, 'y');
            const tx = graph.getNodeAttribute(e.target, 'x');
            const ty = graph.getNodeAttribute(e.target, 'y');

            const x1 = (sx - cx) / z + w / 2;
            const y1 = (sy - cy) / z + h / 2;
            const x2 = (tx - cx) / z + w / 2;
            const y2 = (ty - cy) / z + h / 2;

            const midY = (y1 + y2) / 2;
            const path = `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`;

            const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            p.setAttribute('d', path);
            p.setAttribute('fill', 'none');
            p.setAttribute('stroke', e.type === 'SPOUSE_OF' ? '#bf7f00' : '#aeb4bd');
            p.setAttribute('stroke-width', '2');
            p.setAttribute('stroke-linecap', 'round');
            svg.appendChild(p);
          });

          // Draw cards
          explicit.forEach((id) => {
            const camera = renderer.getCamera();
            const { x: cx, y: cy, ratio: z } = camera.getState();
            const w = graphContainer.clientWidth || 800;
            const h = graphContainer.clientHeight || 600;

            const nx = graph.getNodeAttribute(id, 'x');
            const ny = graph.getNodeAttribute(id, 'y');

            const x = (nx - cx) / z + w / 2;
            const y = (ny - cy) / z + h / 2;

            const node = (idMap.get(id) || {}) as any;
            const name = node.full_name || node.name || node.label || id;
            const kin = node.kin || '';
            const sex = node.sex || 'M';
            const isSelf = id === root;

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const avatarUrl = sex === 'F'
              ? `${apiUrl}/static/img/female_icon.jpg`
              : `${apiUrl}/static/img/male_icon.jpg`;

            const card = document.createElement('div');
            card.style.cssText = `
              position: absolute;
              left: ${x}px;
              top: ${y}px;
              transform: translate(-50%, -50%);
              pointer-events: auto;
              background: white;
              border-radius: 12px;
              box-shadow: 0 6px 18px rgba(0,0,0,0.08);
              display: flex;
              align-items: center;
              gap: 10px;
              padding: 8px 10px;
              max-width: 140px;
              ${isSelf ? 'background: #FFFAF0; border: 1.5px solid #DAA520; box-shadow: 0 0 0 3px rgba(218,165,32,0.16);' : ''}
            `;

            card.innerHTML = `
              <div style="width: 28px; height: 28px; border-radius: 6px; overflow: hidden; background: #f2e7d7;">
                <img src="${avatarUrl}" style="width: 100%; height: 100%; object-fit: cover;" />
              </div>
              <div style="line-height: 1.2; overflow: hidden; flex: 1;">
                <div style="font-size: 11px; color: #6b7280; margin-bottom: 2px;">${kin}</div>
                <div style="font-weight: 600; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${name.split(' ')[0]}</div>
              </div>
            `;

            nodeLayer.appendChild(card);
          });
        };

        // Initial draw
        setTimeout(() => {
          renderer.refresh();
          draw();

          // Center camera
          const xs: number[] = [];
          const ys: number[] = [];
          explicit.forEach((id) => {
            xs.push(graph.getNodeAttribute(id, 'x'));
            ys.push(graph.getNodeAttribute(id, 'y'));
          });

          const minX = Math.min(...xs);
          const maxX = Math.max(...xs);
          const minY = Math.min(...ys);
          const maxY = Math.max(...ys);
          const cx = (minX + maxX) / 2;
          const cy = (minY + maxY) / 2;

          const dx = Math.max(1, (maxX - minX));
          const dy = Math.max(1, (maxY - minY));
          const w = graphContainer.clientWidth || 800;
          const h = graphContainer.clientHeight || 600;

          const margin = 0.15;
          const rx = dx / (w * (1 - margin));
          const ry = dy / (h * (1 - margin));
          const ratio = Math.max(rx, ry, 0.0001);

          renderer.getCamera().setState({ x: cx, y: cy, ratio });
          renderer.refresh();
          draw();
        }, 100);

        // Redraw on render
        renderer.on('afterRender', draw);

        // Button handlers
        document.getElementById('reset-btn')?.addEventListener('click', () => {
          renderer.getCamera().animatedReset({ duration: 300 });
        });

        document.getElementById('fit-btn')?.addEventListener('click', () => {
          const xs: number[] = [];
          const ys: number[] = [];
          explicit.forEach((id) => {
            xs.push(graph.getNodeAttribute(id, 'x'));
            ys.push(graph.getNodeAttribute(id, 'y'));
          });

          const minX = Math.min(...xs);
          const maxX = Math.max(...xs);
          const minY = Math.min(...ys);
          const maxY = Math.max(...ys);
          const cx = (minX + maxX) / 2;
          const cy = (minY + maxY) / 2;

          const dx = Math.max(1, (maxX - minX));
          const dy = Math.max(1, (maxY - minY));
          const w = graphContainer.clientWidth || 800;
          const h = graphContainer.clientHeight || 600;

          const margin = 0.15;
          const rx = dx / (w * (1 - margin));
          const ry = dy / (h * (1 - margin));
          const ratio = Math.max(rx, ry, 0.0001);

          renderer.getCamera().setState({ x: cx, y: cy, ratio });
        });

        document.getElementById('fullscreen-btn')?.addEventListener('click', () => {
          if (!document.fullscreenElement) {
            graphContainer.requestFullscreen();
          } else {
            document.exitFullscreen();
          }
        });

        // Cleanup
        return () => {
          renderer.kill();
        };
      } catch (err) {
        console.error('Error initializing graph:', err);
        setError('Failed to initialize graph visualization');
      }
    };

    const cleanup = initializeGraph();
    return () => {
      cleanup?.then(cleanupFn => cleanupFn?.());
    };
  }, [treeData, personId, isReady]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-red-600 mb-2">{error}</p>
          <p className="text-sm text-neutral-500">Please try refreshing the page</p>
        </div>
      </div>
    );
  }

  return <div ref={containerRef} className="w-full h-full relative" />;
}
