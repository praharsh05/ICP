"use client";

import { useEffect, useRef, useState, useLayoutEffect } from "react";

interface FamilyGraphProps {
  treeData: any;
  personId: string;
  onPersonSelect?: (personId: string) => void;
  onNodeClick?: (nodeId: string) => void;
}

// ============================================================================
// HELPER FUNCTIONS (Outside Component for Performance)
// ============================================================================

function buildAdj(data: any) {
  const parentsOf = new Map();
  const childrenOf = new Map();
  const spousesOf = new Map();

  (data.edges || []).forEach((e: any) => {
    if (!e || !e.source || !e.target) return;
    const T = String(e.type || "").toUpperCase();
    if (T === "CHILD_OF") {
      if (!parentsOf.has(e.source)) parentsOf.set(e.source, new Set());
      parentsOf.get(e.source).add(e.target);
      if (!childrenOf.has(e.target)) childrenOf.set(e.target, new Set());
      childrenOf.get(e.target).add(e.source);
    } else if (T === "SPOUSE_OF") {
      if (!spousesOf.has(e.source)) spousesOf.set(e.source, new Set());
      spousesOf.get(e.source).add(e.target);
      if (!spousesOf.has(e.target)) spousesOf.set(e.target, new Set());
      spousesOf.get(e.target).add(e.source);
    }
  });

  return { parentsOf, childrenOf, spousesOf };
}

function siblingsOf(
  id: string,
  parentsOf: Map<any, any>,
  childrenOf: Map<any, any>
) {
  const ps = parentsOf.get(id) || new Set();
  const out = new Set();
  ps.forEach((p: any) => {
    (childrenOf.get(p) || new Set()).forEach((c: any) => {
      if (c !== id) out.add(c);
    });
  });
  return out;
}

function spouseParents(spouses: Set<any>, parentsOf: Map<any, any>) {
  const out = new Set();
  spouses.forEach((s: any) => {
    (parentsOf.get(s) || new Set()).forEach((p: any) => out.add(p));
  });
  return out;
}

function gpOf(id: string, parentsOf: Map<any, any>) {
  const res = new Set();
  (parentsOf.get(id) || new Set()).forEach((p: any) => {
    (parentsOf.get(p) || new Set()).forEach((g: any) => res.add(g));
  });
  return res;
}

function grandKidsOf(id: string, childrenOf: Map<any, any>) {
  const gs = new Set();
  (childrenOf.get(id) || new Set()).forEach((k: any) => {
    (childrenOf.get(k) || new Set()).forEach((gc: any) => gs.add(gc));
  });
  return gs;
}

function firstWords(name: string, n = 1) {
  if (!name) return "";
  const toks = String(name).trim().split(/\s+/);
  return toks.slice(0, n).join(" ");
}

function boundsFromCoords(coords: Map<any, any>, ids: Set<any>) {
  const xs: number[] = [];
  const ys: number[] = [];
  ids.forEach((id) => {
    const c = coords.get(id);
    if (c) {
      xs.push(c.x);
      ys.push(c.y);
    }
  });
  if (!xs.length) return { cx: 0, cy: 0, minX: 0, maxX: 0, minY: 0, maxY: 0 };
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    cx: (minX + maxX) / 2,
    cy: (minY + maxY) / 2,
    minX,
    maxX,
    minY,
    maxY,
  };
}

function prettyType(t: string) {
  return t === "CHILD_OF"
    ? "children"
    : t === "SPOUSE_OF"
    ? "spouse"
    : t === "MATERNAL_GP"
    ? "maternal grandparents"
    : t === "PATERNAL_GP"
    ? "paternal grandparents"
    : t === "DESCENDANT"
    ? "descendant"
    : t === "IN_LAW"
    ? "in-law"
    : t.toLowerCase();
}

// ============================================================================
// FIVE-TIER LAYOUT FUNCTION
// ============================================================================

function layoutFiveTier(
  data: any,
  adj: any,
  root: string,
  UNIT: number,
  GAP: number,
  Y: any,
  ID_INLAWS: string,
  ID_GPS_M: string,
  ID_GPS_F: string,
  ID_GCK: string
) {
  const { parentsOf, childrenOf, spousesOf } = adj;
  const idMap = new Map(data.nodes.map((n: any) => [n.id, n]));

  const spouses = new Set(spousesOf.get(root) || []);
  const parents = new Set(parentsOf.get(root) || []);
  const siblings = siblingsOf(root, parentsOf, childrenOf);
  const children = new Set(childrenOf.get(root) || []);
  const inlawParents = spouseParents(spouses, parentsOf);
  const grandparents = gpOf(root, parentsOf);
  const grandkids = grandKidsOf(root, childrenOf);

  const coords = new Map();

  // Row 0: Root + Spouses + Siblings
  coords.set(root, { x: 0, y: Y.MID });

  const spousesArr = Array.from(spouses).sort();
  spousesArr.forEach((s: any, i: number) => {
    coords.set(s, { x: (i + 1) * GAP, y: Y.MID });
  });

  // Siblings (split left/right, excluding spouses)
  const sibArr = Array.from(siblings)
    .filter((s: any) => !spouses.has(s))
    .sort();
  const left: any[] = [];
  const right: any[] = [];
  sibArr.forEach((id, i) => (i % 2 === 0 ? left : right).push(id));
  left.forEach((id, i) => coords.set(id, { x: -(i + 1) * GAP, y: Y.MID }));
  right.forEach((id, i) =>
    coords.set(id, { x: (i + 1 + spousesArr.length) * GAP, y: Y.MID })
  );

  // Row +1: Parents + In-laws cluster
  const pArr = Array.from(parents);
  const father =
    pArr.find(
      (p: any) => (idMap.get(p)?.kin || "").toLowerCase() === "father"
    ) || pArr[0];
  const mother =
    pArr.find(
      (p: any) => (idMap.get(p)?.kin || "").toLowerCase() === "mother"
    ) || pArr.find((p: any) => p !== father);

  if (father) coords.set(father, { x: -0.9 * GAP, y: Y.P });
  if (mother) coords.set(mother, { x: 0.9 * GAP, y: Y.P });

  // In-laws cluster (only if visible nodes exist)
  const inlaws = Array.from(inlawParents).filter((id: any) => !parents.has(id));
  const inlawsVisible = inlaws.filter((id: any) => idMap.has(id));
  if (inlawsVisible.length > 0) {
    const baseX = spousesArr.length
      ? (spousesArr.length + 1.5) * GAP
      : 2.5 * GAP;
    coords.set(ID_INLAWS, { x: baseX, y: Y.P });
  }

  // Row +2: Grandparents clusters (split paternal/maternal)
  const gpsF = father ? gpOf(father, parentsOf) : new Set();
  const gpsM = mother ? gpOf(mother, parentsOf) : new Set();
  const gpsFVisible = Array.from(gpsF).filter((id: any) => idMap.has(id));
  const gpsMVisible = Array.from(gpsM).filter((id: any) => idMap.has(id));

  if (gpsFVisible.length > 0) coords.set(ID_GPS_F, { x: -0.9 * GAP, y: Y.GP });
  if (gpsMVisible.length > 0) coords.set(ID_GPS_M, { x: 0.9 * GAP, y: Y.GP });

  // Row -1: Children (grouped by mother if spouse)
  const KEY_ROOT = "__root__";
  const xOf = (id: string) => (coords.has(id) ? coords.get(id).x : 0);
  const childGroups = new Map();

  Array.from(children).forEach((c: any) => {
    const ps = Array.from(parentsOf.get(c) || []);
    const motherId =
      ps.find((p: any) => (idMap.get(p)?.sex || "F") === "F") || null;
    const key = motherId && spouses.has(motherId) ? motherId : KEY_ROOT;
    if (!childGroups.has(key)) childGroups.set(key, []);
    childGroups.get(key).push(c);
  });

  childGroups.forEach((arr: any[], key: string) => {
    arr.sort();
    const centerX = key === KEY_ROOT ? xOf(root) : (xOf(root) + xOf(key)) / 2;
    if (arr.length === 1) {
      coords.set(arr[0], { x: centerX, y: Y.C });
    } else {
      const n = arr.length;
      const start = centerX - ((n - 1) / 2) * GAP;
      arr.forEach((cid, i) => coords.set(cid, { x: start + i * GAP, y: Y.C }));
    }
  });

  // Row -2: Grandchildren cluster
  const grandkidsVisible = Array.from(grandkids).filter((id: any) =>
    idMap.has(id)
  );
  if (grandkidsVisible.length > 0) {
    coords.set(ID_GCK, { x: 0, y: Y.GC });
  }

  // Build explicit set of visible nodes
  const explicit = new Set(
    [
      root,
      ...spousesArr,
      ...sibArr,
      father,
      mother,
      ...Array.from(children),
    ].filter(Boolean)
  );

  if (coords.has(ID_INLAWS)) explicit.add(ID_INLAWS);
  if (coords.has(ID_GPS_F)) explicit.add(ID_GPS_F);
  if (coords.has(ID_GPS_M)) explicit.add(ID_GPS_M);
  if (coords.has(ID_GCK)) explicit.add(ID_GCK);

  // Build filtered edges (only direct relationships)
  const edges: any[] = [];

  (data.edges || []).forEach((e: any) => {
    if (!e || e.source === e.target) return;
    if (!explicit.has(e.source) || !explicit.has(e.target)) return;

    const T = String(e.type || "").toUpperCase();
    if (T === "CHILD_OF") {
      const ps = parentsOf.get(e.source) || new Set();
      if (ps.has(e.target)) {
        edges.push({ source: e.source, target: e.target, type: "CHILD_OF" });
      }
    } else if (T === "SPOUSE_OF") {
      const sp = spousesOf.get(e.source) || new Set();
      if (sp.has(e.target)) {
        edges.push({ source: e.source, target: e.target, type: "SPOUSE_OF" });
      }
    }
  });

  // Cluster connections
  if (coords.has(ID_GPS_F) && father) {
    edges.push({ source: ID_GPS_F, target: father, type: "PATERNAL_GP" });
  }
  if (coords.has(ID_GPS_M) && mother) {
    edges.push({ source: ID_GPS_M, target: mother, type: "MATERNAL_GP" });
  }
  if (coords.has(ID_INLAWS)) {
    if (spousesArr.length) {
      spousesArr.forEach((s: any) =>
        edges.push({ source: ID_INLAWS, target: s, type: "IN_LAW" })
      );
    } else {
      edges.push({ source: ID_INLAWS, target: root, type: "IN_LAW" });
    }
  }
  if (coords.has(ID_GCK)) {
    const kids = Array.from(children);
    if (kids.length) {
      kids.forEach((k: any) =>
        edges.push({ source: ID_GCK, target: k, type: "DESCENDANT" })
      );
    } else {
      edges.push({ source: ID_GCK, target: root, type: "DESCENDANT" });
    }
  }

  return { coords, explicitIds: explicit, edges };
}

function waitForSize(el: HTMLElement, timeout = 5000) {
  return new Promise<void>((resolve, reject) => {
    const ok = () => el.clientWidth > 0 && el.clientHeight > 0;
    if (ok()) return resolve();

    const ro = new ResizeObserver(() => {
      if (ok()) {
        ro.disconnect();
        resolve();
      }
    });
    ro.observe(el);

    const t = setTimeout(() => {
      ro.disconnect();
      reject(new Error("Timed out waiting for container size"));
    }, timeout);
  });
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function FamilyGraph({
  treeData,
  personId,
  onPersonSelect,
  onNodeClick,
}: FamilyGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [currentRoot, setCurrentRoot] = useState(personId);
  const [loading, setLoading] = useState(false);

  //Sync external personId changes with internal state
  useEffect(() => {
    setCurrentRoot(personId);
  }, [personId]);

  // Cluster IDs
  const ID_INLAWS = "__cluster_inlaws__";
  const ID_GPS_M = "__cluster_grandparents_m__";
  const ID_GPS_F = "__cluster_grandparents_f__";
  const ID_GCK = "__cluster_grandchildren__";

  // Layout constants
  const UNIT = 120;
  const GAP = 3.2;
  const Y = { GP: -3.6, P: -1.8, MID: 0, C: 1.8, GC: 3.6 };

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const markIfReady = () => {
      const { width, height } = el.getBoundingClientRect();
      if (width > 0 && height > 0) setIsReady(true);
    };

    const ro = new ResizeObserver(markIfReady);
    ro.observe(el);
    // run once immediately
    markIfReady();

    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!containerRef.current || !treeData || !isReady) return;

    const initializeGraph = async () => {
      try {
        const { default: Graph } = await import("graphology");
        const { default: Sigma } = await import("sigma");

        const container = containerRef.current;
        if (!container) return;

        container.innerHTML = "";

        // Create wrapper structure
        const wrapper = document.createElement("div");
        wrapper.style.cssText =
          "position: absolute; inset: 0; display: flex; flex-direction: column;";

        // Toolbar
        const toolbar = document.createElement("div");
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
            <button id="reset-btn" style="background-color: #DAA520; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: 600; cursor: pointer; transition: all 0.2s;">Reset</button>
            <button id="fit-btn" style="background-color: #DAA520; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: 600; cursor: pointer; transition: all 0.2s;">Fit</button>
            <button id="fullscreen-btn" style="background-color: #DAA520; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: 600; cursor: pointer; transition: all 0.2s;">Full Screen</button>
          </div>
        `;

        // Graph container
        const graphContainer = document.createElement("div");
        graphContainer.id = "sigma-container";
        graphContainer.style.cssText =
          "flex: 1; position: relative; background: #f7f4f1;";

        // Floating fullscreen controls
        const fsControls = document.createElement("div");
        fsControls.id = "fs-controls";
        fsControls.className = "fs-controls";
        fsControls.style.cssText = `
          position: absolute;
          top: 10px;
          right: 10px;
          display: none;
          gap: 8px;
          z-index: 1000;
          pointer-events: auto;
        `;
        fsControls.innerHTML = `
          <button id="fs-reset-btn" style="background-color: #DAA520; color: white; border: none; border-radius: 6px; padding: 6px 10px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);">Reset</button>
          <button id="fs-fit-btn" style="background-color: #DAA520; color: white; border: none; border-radius: 6px; padding: 6px 10px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);">Fit</button>
          <button id="fs-exit-btn" style="background-color: #DAA520; color: white; border: none; border-radius: 6px; padding: 6px 10px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);">Exit</button>
        `;
        graphContainer.appendChild(fsControls);

        wrapper.appendChild(toolbar);
        wrapper.appendChild(graphContainer);
        container.appendChild(wrapper);

        // ... after you append graphContainer to the DOM:
        await waitForSize(graphContainer).catch(() => {
          // As a fallback, don't crash the app—just keep going; Sigma can still mount
          // or you can show a gentle message but do not return early
          console.warn("Container took too long to size; proceeding anyway.");
        });
        // Create graph
        const graph = new Graph({ multi: false, allowSelfLoops: false });

        // Build adjacency
        const adj = buildAdj(treeData);

        // Compute layout
        const layout = layoutFiveTier(
          treeData,
          adj,
          currentRoot,
          UNIT,
          GAP,
          Y,
          ID_INLAWS,
          ID_GPS_M,
          ID_GPS_F,
          ID_GCK
        );

        const idMap = new Map(treeData.nodes.map((n: any) => [n.id, n]));

        // Add nodes to graph
        layout.explicitIds.forEach((id: any) => {
          const c = layout.coords.get(id) || { x: 0, y: 0 };
          graph.addNode(id, {
            x: c.x * UNIT,
            y: c.y * UNIT,
            size: 8,
            color: "#00000000",
          });
        });

        // Wait for container dimensions
        // await new Promise((resolve) => setTimeout(resolve, 50));

        // if (!graphContainer.clientWidth || !graphContainer.clientHeight) {
        //   console.warn("Graph container not ready");
        //   setError("Graph container not ready. Please refresh the page.");
        //   return;
        // }

        // Render sigma
        const renderer = new Sigma(graph, graphContainer, {
          renderLabels: false,
          enableEdgeClickEvents: false,
          allowInvalidContainer: true,
        });

        // Create overlay
        const overlay = document.createElement("div");
        overlay.style.cssText =
          "position: absolute; inset: 0; pointer-events: none; z-index: 10;";

        const svg = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "svg"
        );
        svg.setAttribute("width", "100%");
        svg.setAttribute("height", "100%");
        svg.style.cssText = "position: absolute; inset: 0;";

        const nodeLayer = document.createElement("div");
        nodeLayer.style.cssText = "position: absolute; inset: 0;";

        overlay.appendChild(svg);
        overlay.appendChild(nodeLayer);
        graphContainer.appendChild(overlay);

        // Helper: world to CSS
        const worldToCSSForNode = (id: string) => {
          const wx = graph.getNodeAttribute(id, "x") || 0;
          const wy = graph.getNodeAttribute(id, "y") || 0;
          const cam = renderer.getCamera();
          const { x: cx, y: cy, ratio: z } = cam.getState();
          const cw = graphContainer.clientWidth || 800;
          const ch = graphContainer.clientHeight || 600;
          return {
            x: (wx - cx) / (z || 1) + cw / 2,
            y: (wy - cy) / (z || 1) + ch / 2,
          };
        };

        // Draw edges
        const drawEdges = () => {
          svg.innerHTML = "";
          nodeLayer.querySelectorAll(".edge-label").forEach((n) => n.remove());

          layout.edges.forEach((e: any) => {
            const S = worldToCSSForNode(e.source);
            const T = worldToCSSForNode(e.target);

            const midY = (S.y + T.y) / 2;
            const path = `M ${S.x} ${S.y} L ${S.x} ${midY} L ${T.x} ${midY} L ${T.x} ${T.y}`;

            const p = document.createElementNS(
              "http://www.w3.org/2000/svg",
              "path"
            );
            p.setAttribute("d", path);
            p.setAttribute("fill", "none");
            p.setAttribute(
              "stroke",
              e.type === "SPOUSE_OF" ? "#bf7f00" : "#aeb4bd"
            );
            p.setAttribute("stroke-width", "2");
            p.setAttribute("stroke-linecap", "round");
            svg.appendChild(p);
          });
        };

        // Draw cards
        const drawCards = () => {
          const existing = new Map();
          nodeLayer.querySelectorAll(".card").forEach((el: any) => {
            existing.set(el.dataset.id, el);
          });
          const used = new Set();

          layout.explicitIds.forEach((id: any) => {
            const P = worldToCSSForNode(id);

            let el = existing.get(id);
            if (!el) {
              el = document.createElement("div");
              el.className = "card";
              el.dataset.id = id;
              el.innerHTML = `
                <div class="avatar">
                  <img class="avatar-img" style="width: 100%; height: 100%; object-fit: cover; border-radius: 6px;" />
                </div>
                <div class="info" style="line-height: 1.2; overflow: hidden; flex: 1;">
                  <div class="meta" style="font-size: 11px; color: #6b7280; margin-bottom: 2px;"></div>
                  <div class="name" style="font-weight: 600; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"></div>
                </div>
              `;
              nodeLayer.appendChild(el);
            }
            used.add(id);

            const d = idMap.get(id) || {};
            const isCluster =
              typeof id === "string" && id.startsWith("__cluster_");
            const isSelf = !isCluster && id === currentRoot;

            // Styling
            el.style.cssText = `
              position: absolute;
              left: ${P.x}px;
              top: ${P.y}px;
              transform: translate(-50%, -50%);
              pointer-events: auto;
              background: ${isSelf ? "#FFFAF0" : "white"};
              border: ${isSelf ? "1.5px solid #DAA520" : "none"};
              border-radius: 12px;
              box-shadow: ${
                isSelf
                  ? "0 0 0 3px rgba(218,165,32,0.16), 0 10px 22px rgba(0,0,0,0.12)"
                  : "0 6px 18px rgba(0,0,0,0.08)"
              };
              display: flex;
              align-items: center;
              gap: 10px;
              padding: 8px 10px;
              max-width: 140px;
              cursor: pointer;
            `;

            // Card click handler - navigate to new person
            el.onclick = async (ev: MouseEvent) => {
              ev.preventDefault();
              ev.stopPropagation();
              if (loading || isCluster) return;

              // 🔥 NEW: If clicking same person, just notify parent to update details
              if (id === currentRoot) {
                if (onNodeClick) {
                  onNodeClick(id);
                }
                return;
              }

              // 🔥 NEW: If parent provides navigation callback, use it
              if (onPersonSelect) {
                onPersonSelect(id);
                return;
              }

              // 🔥 FALLBACK: Self-contained behavior (original logic)
              setLoading(true);
              setCurrentRoot(id);

              try {
                const apiUrl =
                  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const resp = await fetch(
                  `${apiUrl}/api/v1/persons/${id}/tree?depth=3&lang=en`
                );
                const newData = await resp.json();

                if (!newData.nodes || !newData.nodes.length) {
                  console.warn("No nodes in response");
                  return;
                }

                // Rebuild with new root
                const newAdj = buildAdj(newData);
                const newLayout = layoutFiveTier(
                  newData,
                  newAdj,
                  id,
                  UNIT,
                  GAP,
                  Y,
                  ID_INLAWS,
                  ID_GPS_M,
                  ID_GPS_F,
                  ID_GCK
                );
                const newIdMap = new Map(
                  newData.nodes.map((n: any) => [n.id, n])
                );

                // Clear and rebuild graph
                graph.clear();
                newLayout.explicitIds.forEach((nid: any) => {
                  const c = newLayout.coords.get(nid) || { x: 0, y: 0 };
                  graph.addNode(nid, {
                    x: c.x * UNIT,
                    y: c.y * UNIT,
                    size: 8,
                    color: "#00000000",
                  });
                });

                // Update layout reference
                Object.assign(layout, newLayout);
                idMap.clear();
                newIdMap.forEach((v, k) => idMap.set(k, v));

                // Center camera
                centerCamera();

                renderer.refresh();
                draw();

                // Update URL
                const url = new URL(window.location.href);
                url.searchParams.set("eid", id);
                window.history.replaceState({}, "", url);
              } catch (e) {
                console.error("Failed to load new ego:", e);
              } finally {
                setLoading(false);
              }
            };

            const fullName =
              d.full_name ||
              d.name ||
              d.label ||
              d.FullName ||
              d.person_name ||
              id;

            // Avatar
            const apiUrl =
              process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            let avatarPath = `${apiUrl}/static/img/male_icon.jpg`;

            if (d.sex) {
              const sex = String(d.sex).toUpperCase();
              avatarPath =
                sex === "F"
                  ? `${apiUrl}/static/img/female_icon.jpg`
                  : `${apiUrl}/static/img/male_icon.jpg`;
            } else if (isCluster) {
              avatarPath = `${apiUrl}/static/img/male_icon.jpg`;
            }

            const avatarImg = el.querySelector(
              ".avatar-img"
            ) as HTMLImageElement;
            if (avatarImg) avatarImg.src = avatarPath;

            // Display name
            const displayName = isCluster
              ? id === ID_GCK
                ? "Grandchildren"
                : id === ID_GPS_F
                ? "Paternal Grandparents"
                : id === ID_GPS_M
                ? "Maternal Grandparents"
                : "In-laws"
              : firstWords(fullName, 1);

            el.querySelector(".name")!.textContent = displayName;

            // Kin
            const kinText = isCluster
              ? id === ID_GCK
                ? "grandchildren"
                : id === ID_GPS_F
                ? "paternal grandparents"
                : id === ID_GPS_M
                ? "maternal grandparents"
                : "in-laws"
              : d.kin || "";

            el.querySelector(".meta")!.textContent = kinText;

            // Popover data
            const metaBits: string[] = [];
            if (d.life_status) metaBits.push(String(d.life_status));
            if (d.sex)
              metaBits.push(
                String(d.sex).toUpperCase() === "F" ? "Female" : "Male"
              );
            if (d.national_id) metaBits.push(`NID: ${d.national_id}`);
            if (d.passport) metaBits.push(`Passport: ${d.passport}`);

            const hoverTitle = isCluster ? displayName : fullName;
            const hoverMeta = metaBits.join(" • ");
            const popText = [hoverTitle, hoverMeta].filter(Boolean).join("\n");
            el.setAttribute("data-pop", popText);
          });

          // Remove unused cards
          existing.forEach((el: any, id: string) => {
            if (!used.has(id)) el.remove();
          });
        };

        // Combined draw
        const draw = () => {
          drawEdges();
          drawCards();
        };

        // Center camera
        const centerCamera = () => {
          const ids = Array.from(layout.explicitIds);
          const b = boundsFromCoords(layout.coords, new Set(ids));

          const cw = graphContainer.clientWidth || 800;
          const ch = graphContainer.clientHeight || 600;

          const dx = Math.max(1e-6, (b.maxX - b.minX) * UNIT);
          const dy = Math.max(1e-6, (b.maxY - b.minY) * UNIT);

          const margin = 0.15;
          const rx = dx / (cw * (1 - margin));
          const ry = dy / (ch * (1 - margin));
          const ratio = Math.max(rx, ry, 0.0001);

          renderer
            .getCamera()
            .setState({ x: b.cx * UNIT, y: b.cy * UNIT, ratio });
        };

        // Initial draw
        setTimeout(() => {
          centerCamera();
          renderer.refresh();
          draw();
        }, 100);

        // Redraw on camera move
        renderer.on("afterRender", draw);

        // Button handlers
        document.getElementById("reset-btn")?.addEventListener("click", () => {
          renderer.getCamera().animatedReset({ duration: 300 });
        });

        document
          .getElementById("fit-btn")
          ?.addEventListener("click", centerCamera);

        // Fullscreen handling
        document
          .getElementById("fullscreen-btn")
          ?.addEventListener("click", () => {
            if (!document.fullscreenElement) {
              graphContainer.requestFullscreen();
            } else {
              document.exitFullscreen();
            }
          });

        document
          .getElementById("fs-reset-btn")
          ?.addEventListener("click", () => {
            renderer.getCamera().animatedReset({ duration: 300 });
          });

        document
          .getElementById("fs-fit-btn")
          ?.addEventListener("click", centerCamera);

        document
          .getElementById("fs-exit-btn")
          ?.addEventListener("click", () => {
            if (document.exitFullscreen) document.exitFullscreen();
          });

        // Fullscreen visibility toggle
        const syncFsControlsVisibility = () => {
          const inFS = document.fullscreenElement === graphContainer;
          fsControls.style.display = inFS ? "flex" : "none";
        };

        document.addEventListener("fullscreenchange", syncFsControlsVisibility);
        syncFsControlsVisibility();

        // Window resize handler
        const handleResize = () => {
          centerCamera();
          renderer.refresh();
          draw();
        };
        window.addEventListener("resize", handleResize);

        // Cleanup
        return () => {
          document.removeEventListener(
            "fullscreenchange",
            syncFsControlsVisibility
          );
          window.removeEventListener("resize", handleResize);
          renderer.kill();
        };
      } catch (err) {
        console.error("Error initializing graph:", err);
        setError("Failed to initialize graph visualization");
      }
    };

    const cleanup = initializeGraph();
    return () => {
      cleanup?.then((cleanupFn) => cleanupFn?.());
    };
  }, [
    treeData,
    currentRoot,
    isReady,
    ID_INLAWS,
    ID_GPS_M,
    ID_GPS_F,
    ID_GCK,
    UNIT,
    GAP,
    Y,
    loading,
    onPersonSelect,
    onNodeClick,
  ]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-red-600 mb-2">{error}</p>
          <p className="text-sm text-neutral-500">
            Please try refreshing the page
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-full min-h-[480px] relative"
    />
  );
}
