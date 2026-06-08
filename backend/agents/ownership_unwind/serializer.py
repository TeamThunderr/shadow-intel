"""
Graph Serializer Module

Converts NetworkX ownership graph to D3.js-compatible JSON format.
Handles node positioning, link metadata, and color coding.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import networkx as nx
from backend.shared.logger import get_logger

logger = get_logger(__name__)


class GraphNode(BaseModel):
    """D3.js compatible node representation."""
    id: str
    label: str
    type: str  # person, company, trust, fund
    jurisdiction: Optional[str] = None
    registration_number: Optional[str] = None
    color: Optional[str] = None  # Color coding for visualization
    size: Optional[float] = None  # Node size (influence/stake)
    source_system: Optional[str] = None
    source_reference: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional fields for D3.js


class GraphLink(BaseModel):
    """D3.js compatible link representation."""
    source: str  # Entity ID
    target: str  # Entity ID
    value: float  # Ownership percentage
    type: str = "ownership"
    source_data: Optional[str] = None
    source_system: Optional[str] = None
    source_reference: Optional[str] = None
    
    class Config:
        extra = "allow"


class SerializedOwnershipGraph(BaseModel):
    """Complete serialized ownership graph in D3.js format."""
    nodes: List[GraphNode]
    links: List[GraphLink]
    metadata: Dict[str, Any] = {}


class OwnershipGraphSerializer:
    """
    Serializes NetworkX directed graphs to D3.js-compatible JSON.
    
    Provides:
    - Node coloring by entity type
    - Link strength based on ownership percentage
    - Node sizing based on network centrality
    """
    
    # Color scheme by entity type
    COLOR_SCHEME = {
        "person": "#1f77b4",      # Blue
        "company": "#ff7f0e",     # Orange
        "trust": "#2ca02c",       # Green
        "fund": "#d62728",        # Red
    }
    
    def __init__(self, graph: nx.DiGraph):
        """
        Initialize serializer with a NetworkX graph.
        
        Args:
            graph: NetworkX DiGraph representing ownership structure
        """
        self.graph = graph
        self.logger = get_logger(self.__class__.__name__)
    
    def serialize(self) -> SerializedOwnershipGraph:
        """
        Serialize the graph to D3.js compatible format.
        
        Returns:
            SerializedOwnershipGraph with nodes and links
        """
        nodes = self._serialize_nodes()
        links = self._serialize_links()
        
        result = SerializedOwnershipGraph(
            nodes=nodes,
            links=links,
            metadata={
                "total_nodes": len(nodes),
                "total_links": len(links),
                "directed": True,
            }
        )
        
        self.logger.info(f"Serialized graph: {len(nodes)} nodes, {len(links)} links")
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary format for JSON output.
        
        Returns:
            Dictionary with 'nodes' and 'links' keys
        """
        serialized = self.serialize()
        return {
            "nodes": [node.model_dump() for node in serialized.nodes],
            "links": [link.model_dump() for link in serialized.links],
            "metadata": serialized.metadata
        }
    
    def _serialize_nodes(self) -> List[GraphNode]:
        """
        Convert graph nodes to D3.js format.
        
        Returns:
            List of GraphNode objects
        """
        nodes = []
        
        # Calculate node centrality for sizing
        in_degree_centrality = nx.in_degree_centrality(self.graph)
        out_degree_centrality = nx.out_degree_centrality(self.graph)
        
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            
            # Determine color based on type
            node_type = node_data.get("type", "unknown")
            color = self.COLOR_SCHEME.get(node_type, "#999999")
            
            # Calculate node size based on centrality (influence in network)
            centrality = (in_degree_centrality.get(node_id, 0) +
                         out_degree_centrality.get(node_id, 0)) / 2
            size = 5.0 + (centrality * 20)  # Scale from 5 to 25
            
            node = GraphNode(
                id=node_id,
                label=node_data.get("name", node_id),
                type=node_type,
                jurisdiction=node_data.get("jurisdiction"),
                registration_number=node_data.get("registration_number"),
                color=color,
                size=size,
                source_system=node_data.get("source_system"),
                source_reference=node_data.get("source_reference")
            )
            nodes.append(node)
        
        return nodes
    
    def _serialize_links(self) -> List[GraphLink]:
        """
        Convert graph edges to D3.js format.
        
        Returns:
            List of GraphLink objects
        """
        links = []
        
        for from_id, to_id, edge_data in self.graph.edges(data=True):
            link = GraphLink(
                source=from_id,
                target=to_id,
                value=edge_data.get("ownership_percentage", 100.0),
                type=edge_data.get("link_type", "ownership"),
                source_data=edge_data.get("source"),
                source_system=edge_data.get("source_system"),
                source_reference=edge_data.get("source_reference")
            )
            links.append(link)
        
        return links
    
    def get_node_colors(self) -> Dict[str, str]:
        """Return mapping of node IDs to colors."""
        return {
            node_id: self.COLOR_SCHEME.get(
                self.graph.nodes[node_id].get("type", "unknown"),
                "#999999"
            )
            for node_id in self.graph.nodes()
        }
    
    def get_node_sizes(self) -> Dict[str, float]:
        """Return mapping of node IDs to calculated sizes."""
        in_degree = nx.in_degree_centrality(self.graph)
        out_degree = nx.out_degree_centrality(self.graph)
        
        return {
            node_id: 5.0 + ((in_degree.get(node_id, 0) + out_degree.get(node_id, 0)) / 2) * 20
            for node_id in self.graph.nodes()
        }


class OwnershipVisualizationHelper:
    """
    Helper class for preparing graph visualization data.
    Includes layout algorithms and force-directed positioning.
    """
    
    @staticmethod
    def prepare_hierarchical_layout(graph: nx.DiGraph) -> Dict[str, Dict[str, float]]:
        """
        Prepare hierarchical node positions for tree-like ownership structures.
        
        Args:
            graph: NetworkX DiGraph
            
        Returns:
            Dict mapping node_id to {x, y} positions
        """
        positions = {}
        levels = {}  # node_id -> hierarchy level
        
        # Find root nodes (entities with no predecessors)
        roots = [node for node in graph.nodes() if graph.in_degree(node) == 0]
        
        # BFS to assign levels
        from collections import deque
        queue = deque([(root, 0) for root in roots])
        visited = set()
        
        while queue:
            node, level = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            levels[node] = level
            
            for successor in graph.successors(node):
                queue.append((successor, level + 1))
        
        # Calculate positions
        level_nodes = {}
        for node, level in levels.items():
            if level not in level_nodes:
                level_nodes[level] = []
            level_nodes[level].append(node)
        
        for level, nodes in level_nodes.items():
            y = level * 150
            x_spacing = 200
            total_width = len(nodes) * x_spacing
            
            for idx, node in enumerate(nodes):
                x = (idx * x_spacing) - (total_width / 2)
                positions[node] = {"x": x, "y": y}
        
        return positions
