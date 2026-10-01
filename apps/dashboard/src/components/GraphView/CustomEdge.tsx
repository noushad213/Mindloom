import { BaseEdge, EdgeLabelRenderer, getBezierPath } from "@xyflow/react";
import type { EdgeProps } from "@xyflow/react";
import type { GraphEdge } from "../../types";
import styles from "./CustomEdge.module.css";

export type CustomEdgeData = GraphEdge & {
  onDeleteEdge?: (edgeId: string) => void;
  color?: string;
};

export function CustomEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeData = data as unknown as CustomEdgeData | undefined;
  const isSuggested = edgeData?.origin === "suggested";
  const typeLabel = (edgeData?.type || "related_to").replace(/_/g, " ");

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: edgeData?.color || "var(--teal)",
          strokeWidth: 2,
          strokeDasharray: "3,5",
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
          }}
          className={`${styles.edgeLabel} ${isSuggested ? styles.suggested : ""}`}
          title={edgeData?.evidence || undefined}
        >
          <span>{edgeData?.label || typeLabel}</span>
          {edgeData?.onDeleteEdge && (
            <button
              className={styles.deleteBtn}
              onClick={(e) => {
                e.stopPropagation();
                edgeData.onDeleteEdge?.(id);
              }}
              title="Delete connection"
              aria-label="Delete connection"
            >
              ×
            </button>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
