"""Social interaction graph and network analytics using NetworkX."""

from typing import List, Dict, Any, Optional
import networkx as nx
from app.services.transcript_parser import ParsedSegment


class SocialGraphService:
    """Builds interactive social networks and conversation flow graphs."""

    def build_graph(
        self,
        participants: Dict[str, Any],
        segments: List[ParsedSegment],
        interruptions: List[Dict[str, Any]],
        idea_overlaps: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Construct nodes and directed edges for participant interactions.
        Returns a structure directly consumable by Cytoscape.js and D3.
        """
        idea_overlaps = idea_overlaps or []
        G = nx.MultiDiGraph()

        # Add Nodes
        nodes = []
        max_speaking = max((p.get("speaking_time", 1.0) for p in participants.values()), default=1.0) or 1.0

        for name, data in participants.items():
            sp_time = data.get("speaking_time", 0.0)
            # Size between 28px and 68px based on speaking share
            node_size = int(28 + (sp_time / max_speaking) * 40)
            node_item = {
                "id": name,
                "label": name,
                "speaking_time": sp_time,
                "speaking_percentage": data.get("speaking_percentage", 0.0),
                "turn_count": data.get("turn_count", 0),
                "interruptions_made": data.get("interruptions_made", 0),
                "interruptions_received": data.get("interruptions_received", 0),
                "ideas_count": data.get("ideas_introduced", 0),
                "color": data.get("avatar_color", "#4f46e5"),
                "size": node_size
            }
            nodes.append(node_item)
            G.add_node(name, **node_item)

        # Track Edge counts: (source, target, type) -> count
        edge_counts: Dict[tuple, Dict[str, Any]] = {}

        # 1. Sequential Turn Responses (Conversation Flow)
        for i in range(len(segments) - 1):
            s1 = segments[i].speaker
            s2 = segments[i + 1].speaker
            if s1 and s2 and s1 != s2 and s1 != "Unknown" and s2 != "Unknown":
                key = (s2, s1, "RESPONSE")  # s2 responded to s1
                if key not in edge_counts:
                    edge_counts[key] = {"count": 0, "conf_sum": 0.0}
                edge_counts[key]["count"] += 1
                edge_counts[key]["conf_sum"] += 0.90

                # Check for direct address in s1 towards s2 (Direct Reply)
                if s2.lower() in segments[i].text.lower():
                    direct_key = (s1, s2, "DIRECT_REPLY")
                    if direct_key not in edge_counts:
                        edge_counts[direct_key] = {"count": 0, "conf_sum": 0.0}
                    edge_counts[direct_key]["count"] += 1
                    edge_counts[direct_key]["conf_sum"] += 0.95

        # 2. Interruption Edges
        for item in interruptions:
            src = item["speaker_a"]  # Interrupter
            tgt = item["speaker_b"]  # Interrupted
            if src and tgt and src != tgt:
                key = (src, tgt, "INTERRUPTION")
                if key not in edge_counts:
                    edge_counts[key] = {"count": 0, "conf_sum": 0.0}
                edge_counts[key]["count"] += 1
                edge_counts[key]["conf_sum"] += item.get("confidence", 0.8)

        # 3. Idea Overlap Edges
        for item in idea_overlaps:
            src = item["speaker_b"]  # Later speaker
            tgt = item["speaker_a"]  # Original speaker
            if src and tgt and src != tgt:
                key = (src, tgt, "IDEA_OVERLAP")
                if key not in edge_counts:
                    edge_counts[key] = {"count": 0, "conf_sum": 0.0}
                edge_counts[key]["count"] += 1
                edge_counts[key]["conf_sum"] += item.get("similarity", 0.85)

        # Build Cytoscape/D3 Edge List
        edges = []
        for (src, tgt, edge_type), val in edge_counts.items():
            count = val["count"]
            avg_conf = round(val["conf_sum"] / count, 2)
            edge_id = f"{src}->{tgt}:{edge_type}"
            edge_obj = {
                "id": edge_id,
                "source": src,
                "target": tgt,
                "type": edge_type,
                "weight": count,
                "confidence": avg_conf,
                "width": min(8, 1 + count * 1.2),
                "label": f"{count} {edge_type.lower().replace('_', ' ')}"
            }
            edges.append(edge_obj)
            G.add_edge(src, tgt, key=edge_type, **edge_obj)

        # Compute Network Graph Centrality
        centrality = {}
        if len(G.nodes) > 1:
            try:
                centrality = {
                    node: round(score, 3)
                    for node, score in nx.degree_centrality(G).items()
                }
            except Exception:
                centrality = {}

        return {
            "nodes": nodes,
            "edges": edges,
            "metrics": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "degree_centrality": centrality
            }
        }
