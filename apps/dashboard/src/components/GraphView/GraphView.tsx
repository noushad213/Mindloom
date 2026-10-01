import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  useNodesState,
  useEdgesState,
  addEdge,
} from "@xyflow/react";
import type {
  Connection,
  Edge,
  Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { ResearchNode } from "./ResearchNode";
import { CustomEdge } from "./CustomEdge";
import type { GraphEdge, GraphPage, Workspace } from "../../types";
import { createEdge, deleteEdge, fetchGraphSnapshot, updatePositions } from "../../api";
import styles from "./GraphView.module.css";

interface GraphViewProps {
  activeWorkspace: Workspace;
  onSelectPage?: (page: GraphPage) => void;
  onStartTracking?: () => void;
  embedded?: boolean;
}

function calculatePositions(pages: GraphPage[]): Array<{ x: number; y: number }> {
  const total = pages.length;
  if (total === 0) return [];
  if (total === 1) return [{ x: 350, y: 220 }];

  const radius = Math.max(220, total * 45);
  return pages.map((page, index) => {
    if (page.pos && typeof page.pos.x === "number" && typeof page.pos.y === "number") {
      return { x: page.pos.x, y: page.pos.y };
    }
    const angle = (index / total) * 2 * Math.PI - Math.PI / 2;
    return {
      x: Math.round(450 + Math.cos(angle) * radius),
      y: Math.round(320 + Math.sin(angle) * radius),
    };
  });
}

export function GraphView({
  activeWorkspace,
  onSelectPage,
  onStartTracking,
  embedded = false,
}: GraphViewProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const nodeTypes = useMemo(() => ({ researchNode: ResearchNode }), []);
  const edgeTypes = useMemo(() => ({ customEdge: CustomEdge }), []);

  const handleDeleteEdge = useCallback(
    async (edgeId: string) => {
      try {
        await deleteEdge(edgeId);
        setEdges((prev) => prev.filter((e) => e.id !== edgeId));
      } catch (err) {
        console.error("Failed to delete edge:", err);
      }
    },
    [setEdges],
  );

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const snapshot = await fetchGraphSnapshot(activeWorkspace.id);
      const positions = calculatePositions(snapshot.pages);

      const flowNodes: Node[] = snapshot.pages.map((page, i) => ({
        id: page.id,
        type: "researchNode",
        position: positions[i],
        data: {
          ...page,
          onSelectNode: onSelectPage,
        },
      }));

      const flowEdges: Edge[] = snapshot.edges.map((edge: GraphEdge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: "customEdge",
        data: {
          ...edge,
          onDeleteEdge: handleDeleteEdge,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: edge.origin === "suggested" ? "#a8a5a0" : "#787774",
        },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to load graph.");
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace.id, handleDeleteEdge, onSelectPage, setEdges, setNodes]);

  useEffect(() => {
    let cancelled = false;
    async function syncGraph() {
      try {
        const snapshot = await fetchGraphSnapshot(activeWorkspace.id);
        if (cancelled) return;
        const positions = calculatePositions(snapshot.pages);

        const flowNodes: Node[] = snapshot.pages.map((page, i) => ({
          id: page.id,
          type: "researchNode",
          position: positions[i],
          data: {
            ...page,
            onSelectNode: onSelectPage,
          },
        }));

        const flowEdges: Edge[] = snapshot.edges.map((edge: GraphEdge) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: "customEdge",
          data: {
            ...edge,
            onDeleteEdge: handleDeleteEdge,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 14,
            height: 14,
            color: edge.origin === "suggested" ? "#a8a5a0" : "#787774",
          },
        }));

        setNodes(flowNodes);
        setEdges(flowEdges);
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Failed to load graph.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void syncGraph();
    return () => {
      cancelled = true;
    };
  }, [activeWorkspace.id, handleDeleteEdge, onSelectPage, setEdges, setNodes]);

  const handleConnect = useCallback(
    async (params: Connection) => {
      if (!params.source || !params.target || params.source === params.target) return;
      try {
        const newEdge = await createEdge(activeWorkspace.id, {
          source: params.source,
          target: params.target,
          type: "related_to",
        });

        const flowEdge: Edge = {
          id: newEdge.id,
          source: newEdge.source,
          target: newEdge.target,
          type: "customEdge",
          data: {
            ...newEdge,
            onDeleteEdge: handleDeleteEdge,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 14,
            height: 14,
            color: "#787774",
          },
        };

        setEdges((eds) => addEdge(flowEdge, eds));
      } catch (err) {
        console.error("Failed to create connection:", err);
      }
    },
    [activeWorkspace.id, handleDeleteEdge, setEdges],
  );

  const handleNodeDragStop = useCallback(
    (_event: MouseEvent | TouchEvent, node: Node) => {
      void updatePositions(activeWorkspace.id, [
        {
          id: node.id,
          x: Math.round(node.position.x),
          y: Math.round(node.position.y),
        },
      ]);
    },
    [activeWorkspace.id],
  );

  const handleAutoArrange = useCallback(() => {
    setNodes((prevNodes) => {
      const total = prevNodes.length;
      if (total <= 1) return prevNodes;
      const radius = Math.max(220, total * 45);
      const updated = prevNodes.map((n, idx) => {
        const angle = (idx / total) * 2 * Math.PI - Math.PI / 2;
        return {
          ...n,
          position: {
            x: Math.round(450 + Math.cos(angle) * radius),
            y: Math.round(320 + Math.sin(angle) * radius),
          },
        };
      });

      void updatePositions(
        activeWorkspace.id,
        updated.map((n) => ({ id: n.id, x: n.position.x, y: n.position.y })),
      );

      return updated;
    });
  }, [activeWorkspace.id, setNodes]);

  return (
    <div className={`${styles.container} ${embedded ? styles.embedded : ""}`}>
      <header className={`${styles.toolbar} ${embedded ? styles.embeddedToolbar : ""}`}>
        <div className={styles.toolbarLeft}>
          <h2 className={styles.title}>Knowledge Canvas</h2>
          <span className={styles.stats}>
            {nodes.length} page{nodes.length !== 1 ? "s" : ""} • {edges.length} connection
            {edges.length !== 1 ? "s" : ""}
          </span>
        </div>
        <div className={styles.toolbarRight}>
          <button className={styles.toolBtn} onClick={handleAutoArrange} title="Arrange nodes in a circle">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 3v18" />
              <path d="M3 12h18" />
            </svg>
            Auto Arrange
          </button>
          <button className={styles.toolBtn} onClick={() => void loadGraph()} title="Refresh graph snapshot">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            Refresh
          </button>
        </div>
      </header>

      <div className={styles.flowWrapper}>
        {loading && nodes.length === 0 ? (
          <div className={styles.emptyOverlay}>
            <h3 className={styles.emptyTitle}>Loading Knowledge Canvas…</h3>
            <p className={styles.emptyText}>Fetching research pages and relationship graph.</p>
          </div>
        ) : nodes.length === 0 ? (
          <div className={styles.emptyOverlay}>
            <h3 className={styles.emptyTitle}>No Pages in Canvas Yet</h3>
            <p className={styles.emptyText}>
              Start tracking browser tabs to collect articles, documents, and repos into this visual graph.
            </p>
            {onStartTracking && (
              <button className={styles.emptyAction} onClick={onStartTracking}>
                Start Tracking
              </button>
            )}
          </div>
        ) : null}

        {loadError && (
          <div className={styles.emptyOverlay}>
            <h3 className={styles.emptyTitle}>Could not load graph</h3>
            <p className={styles.emptyText}>{loadError}</p>
            <button className={styles.emptyAction} onClick={() => void loadGraph()}>
              Retry
            </button>
          </div>
        )}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={handleConnect}
          onNodeDragStop={handleNodeDragStop}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          attributionPosition="bottom-right"
        >
          <Background color="#dcdbd8" gap={20} size={1} />
          <Controls showInteractive={false} />
          <MiniMap
            nodeColor="#eaeaea"
            maskColor="rgba(247, 246, 243, 0.7)"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
