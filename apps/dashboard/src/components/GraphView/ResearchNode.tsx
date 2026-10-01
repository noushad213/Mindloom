import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import type { GraphPage } from "../../types";
import styles from "./ResearchNode.module.css";

export type ResearchNodeData = GraphPage & {
  onSelectNode?: (page: GraphPage) => void;
  clusterColor?: string;
};

export const ResearchNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as unknown as ResearchNodeData;
  const statusClass =
    nodeData.status === "ready" || nodeData.status === "captured"
      ? styles.statusReady
      : nodeData.status === "processing" || nodeData.status === "queued"
      ? styles.statusProcessing
      : styles.statusFailed;

  return (
    <div
      className={`${styles.node} ${selected ? styles.selected : ""}`}
      style={{ borderTopColor: nodeData.clusterColor }}
      onClick={() => nodeData.onSelectNode?.(nodeData)}
    >
      <Handle
        id="target"
        type="target"
        position={Position.Top}
        className={styles.handle}
      />

      <div className={styles.header}>
        <span className={styles.clusterDot} style={{ backgroundColor: nodeData.clusterColor }} aria-hidden="true" />
        <span className={styles.domainBadge} title={nodeData.canonicalUrl}>
          {nodeData.sourceDomain || "web"}
        </span>
        <span className={`${styles.statusPill} ${statusClass}`}>
          {nodeData.status}
        </span>
      </div>

      <div className={styles.title} title={nodeData.title}>
        {nodeData.title || "Untitled Page"}
      </div>

      {nodeData.summary && (
        <div className={styles.summary} title={nodeData.summary}>
          {nodeData.summary}
        </div>
      )}

      <Handle
        id="source"
        type="source"
        position={Position.Bottom}
        className={styles.handle}
      />
    </div>
  );
});

ResearchNode.displayName = "ResearchNode";
