import React, { useEffect, useRef } from "react";
import Sigma from "sigma";
import { MultiDirectedGraph } from "graphology";
import { Streamlit, withStreamlitConnection, ComponentProps } from "streamlit-component-lib";

// Color map
const COLORS: Record<string, string> = {
  CENTER: "#1f2937",
  PARENTS: "#10b981",
  CHILDREN: "#3b82f6",
  SPOUSES: "#f59e0b",
  SIBLINGS: "#8b5cf6",
  CLUSTER: "#9ca3af",
  HINT_CHILDREN: "#d1d5db",
  HINT_SPOUSES: "#e5e7eb",
};

type Props = ComponentProps & {
  args: {
    graph: { nodes: any[]; edges: any[] };
    height?: number;
  };
};

// add this helper near the top
function placeNodes(g: MultiDirectedGraph) {
  // center
  const center = g.nodes().find(n => g.getNodeAttribute(n, "type") === "CENTER");
  if (center) {
    if (g.getNodeAttribute(center, "x") === undefined) g.setNodeAttribute(center, "x", 0);
    if (g.getNodeAttribute(center, "y") === undefined) g.setNodeAttribute(center, "y", 0);
  }

  const rings: Record<string, number> = {
    PARENTS: 1.0,
    CHILDREN: 1.0,
    SPOUSES: 1.2,
    SIBLINGS: 1.4,
    CLUSTER: 1.6,
    HINT_CHILDREN: 0.35,
    HINT_SPOUSES: 0.45,
  };

  Object.entries(rings).forEach(([type, radius]) => {
    const nodes = g.nodes().filter(n => g.getNodeAttribute(n, "type") === type);
    const n = nodes.length || 1;
    nodes.forEach((node, i) => {
      if (g.getNodeAttribute(node, "x") === undefined || g.getNodeAttribute(node, "y") === undefined){
        const angle = (i / n) * Math.PI * 2;
        g.setNodeAttribute(node, "x", Math.cos(angle) * radius);
        g.setNodeAttribute(node, "y", Math.sin(angle) * radius);
      }
    });
  });
}

function upsertGraph(g: MultiDirectedGraph, payload: any) {
  g.clear();
  for (const n of payload.nodes) {
    const nx = (n as any).x;
    const ny = (n as any).y;
    g.addNode(n.id, {
      label: n.label,
      type: n.type,
      color: COLORS[n.type] || "#6b7280",
      size: n.type === "CENTER" ? 12 : String(n.type).startsWith("HINT_") ? 3 : 6,
      clusterOf: (n as any).clusterOf,
      of: (n as any).of,
      // Use provided coordinates if they exist
      ...(Number.isFinite(nx)) ? {x:nx} : {},
      ...(Number.isFinite(ny)) ? {y: ny} : {},
    });
  }
  for (const e of payload.edges) {
    const key = e.id || `${e.source}->${e.target}:${e.type}`;
    if (!g.hasEdge(key)) {
      g.addEdgeWithKey(key, e.source, e.target, {
        type: e.type,
        color: e.type === "SPOUSE_OF" ? "#f59e0b" : "#9ca3af",
      });
    }
  }
}

const StreamlitSigma: React.FC<Props> = (props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<MultiDirectedGraph | null>(null);
  const height = props.args?.height ?? 820;

  // One-time init
  useEffect(() => {
    graphRef.current = new MultiDirectedGraph();
    sigmaRef.current = new Sigma(graphRef.current, containerRef.current!, {
      renderLabels: true,
    });

    // Tell Streamlit the component is ready & how tall we are
    Streamlit.setComponentReady();
    Streamlit.setFrameHeight(height);

    const onResize = () => Streamlit.setFrameHeight(height);
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      sigmaRef.current?.kill();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // On args change: update graph and wire events
  useEffect(() => {
    if (!sigmaRef.current || !graphRef.current) return;

    const g = graphRef.current;
    upsertGraph(g, props.args.graph);
    placeNodes(g);

    // Center camera to CENTER node
    const center =
      g.nodes().find((n) => g.getNodeAttribute(n, "type") === "CENTER") ||
      g.nodes()[0];
    if (center) {
      const cam = sigmaRef.current.getCamera();
      const pos = sigmaRef.current.getNodeDisplayData(center);
      if (pos) cam.animate({ x: pos.x, y: pos.y, ratio: 0.8 }, { duration: 250 });
    }

    const onClick = ({ node }: any) => {
      const attrs = g.getNodeAttributes(node);
      // Smooth pan first
      const cam = sigmaRef.current!.getCamera();
      const pos = sigmaRef.current!.getNodeDisplayData(node);
      if (pos) cam.animate({ x: pos.x, y: pos.y, ratio: 0.7 }, { duration: 250 });

      // Emit value to Streamlit (this is the official API)
      if (attrs.type === "CLUSTER") {
        Streamlit.setComponentValue({ type: "expand_cluster", group: attrs.clusterOf });
        return;
      }
      if (String(attrs.type).startsWith("HINT_")) {
        Streamlit.setComponentValue({ type: "center", uid: attrs.of });
        return;
      }
      Streamlit.setComponentValue({ type: "center", uid: node });
    };

    sigmaRef.current.on("clickNode", onClick);
    return () => {
      sigmaRef.current?.removeListener("clickNode", onClick);
    };
  }, [props.args]);

  return <div ref={containerRef} style={{ width: "100%", height }} />;
};

export default withStreamlitConnection(StreamlitSigma);
