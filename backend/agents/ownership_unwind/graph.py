import networkx as nx
from shared.logger import get_logger

logger = get_logger(__name__)


class OwnershipGraph:
    """
    Directed graph for modelling corporate ownership chains.
    Uses NetworkX DiGraph for traversal and cycle detection.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_entity(self, entity_id: str, name: str, entity_type: str = "company", **attrs):
        """Add an entity node to the graph."""
        self.graph.add_node(entity_id, name=name, entity_type=entity_type, **attrs)

    def add_ownership(self, owner_id: str, owned_id: str, stake_pct: float = 0.0):
        """Add a directed ownership edge: owner -> owned."""
        self.graph.add_edge(owner_id, owned_id, stake_pct=stake_pct)

    def detect_circular(self) -> list[list[str]]:
        """Detect circular ownership patterns (shell company indicator)."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except Exception as e:
            logger.error(f"Cycle detection failed: {e}")
            return []

    def find_ultimate_beneficial_owner(self, root_id: str) -> list[str]:
        """
        Traverse ownership chain upward to find nodes with no incoming edges
        (i.e. entities that own others but are not owned by anyone).
        """
        ubos = []
        for node in self.graph.nodes:
            if self.graph.in_degree(node) == 0 and node != root_id:
                ubos.append(node)
        return ubos

    def to_json(self) -> dict:
        """Serialize graph to D3.js-compatible JSON format."""
        nodes = [
            {"id": n, **self.graph.nodes[n]}
            for n in self.graph.nodes
        ]
        edges = [
            {"source": u, "target": v, **self.graph.edges[u, v]}
            for u, v in self.graph.edges
        ]
        return {"nodes": nodes, "edges": edges}
