"""
Graph Builder Module

Constructs a NetworkX directed graph representing ownership relationships.
Handles entity management (persons, companies) and ownership links (shares, stakes).
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Set, Any
from enum import Enum
import uuid
import networkx as nx
from shared.logger import get_logger
from shared.schemas import EvidenceItem

logger = get_logger(__name__)


class EntityType(str, Enum):
    """Entity type classification."""
    person = "person"
    company = "company"
    trust = "trust"
    fund = "fund"


class OwnershipEntity(BaseModel):
    """Represents a person or organization in the ownership structure."""
    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: EntityType
    jurisdiction: Optional[str] = None
    registration_number: Optional[str] = None
    description: Optional[str] = None
    source_system: Optional[str] = None
    source_reference: Optional[str] = None
    
    class Config:
        use_enum_values = False


class OwnershipLink(BaseModel):
    """Represents a direct ownership relationship between two entities."""
    from_entity_id: str
    to_entity_id: str
    ownership_percentage: float = Field(ge=0.0, le=100.0)
    link_type: str = "ownership"  # ownership, directorship, beneficiary, etc.
    source: Optional[str] = None  # Where this relationship comes from
    date_recorded: Optional[str] = None
    source_system: Optional[str] = None
    source_reference: Optional[str] = None
    
    class Config:
        use_enum_values = False


class OwnershipGraphBuilder:
    """
    Constructs and manages a directed ownership graph.
    
    Nodes represent entities (persons or companies).
    Edges represent ownership relationships with percentages.
    """
    
    def __init__(self):
        self.graph: nx.DiGraph = nx.DiGraph()
        self.entities: Dict[str, OwnershipEntity] = {}
        self.evidence: List[EvidenceItem] = []
        self.logger = get_logger(self.__class__.__name__)
    
    def add_entity(self, entity: OwnershipEntity) -> str:
        """
        Add an entity (person or company) to the graph.
        
        Args:
            entity: OwnershipEntity object
            
        Returns:
            entity_id: The unique identifier for the entity
        """
        self.entities[entity.entity_id] = entity
        self.graph.add_node(
            entity.entity_id,
            name=entity.name,
            type=entity.type.value,
            jurisdiction=entity.jurisdiction,
            registration_number=entity.registration_number,
            source_system=entity.source_system,
            source_reference=entity.source_reference
        )
        self.logger.debug(f"Added entity: {entity.name} ({entity.entity_id})")
        return entity.entity_id
    
    def add_ownership_link(self, link: OwnershipLink) -> None:
        """
        Add an ownership relationship between two entities.
        
        Args:
            link: OwnershipLink describing the relationship
            
        Raises:
            ValueError: If entities don't exist in graph
        """
        if link.from_entity_id not in self.graph:
            raise ValueError(f"Source entity {link.from_entity_id} not found in graph")
        if link.to_entity_id not in self.graph:
            raise ValueError(f"Target entity {link.to_entity_id} not found in graph")
        
        self.graph.add_edge(
            link.from_entity_id,
            link.to_entity_id,
            ownership_percentage=link.ownership_percentage,
            link_type=link.link_type,
            source=link.source,
            date_recorded=link.date_recorded,
            source_system=link.source_system,
            source_reference=link.source_reference
        )
        self.logger.debug(
            f"Added ownership link: {link.from_entity_id} "
            f"--({link.ownership_percentage}%)--> {link.to_entity_id}"
        )
        
    def add_evidence(self, evidence_item: EvidenceItem) -> None:
        """Add an evidence item representing a discovered relationship."""
        self.evidence.append(evidence_item)
        self.logger.debug(f"Added evidence: {evidence_item.detail}")
        
    def get_graph(self) -> nx.DiGraph:
        """Return the underlying NetworkX graph."""
        return self.graph
    
    def get_entity(self, entity_id: str) -> Optional[OwnershipEntity]:
        """Retrieve an entity by ID."""
        return self.entities.get(entity_id)
    
    def get_all_entities(self) -> Dict[str, OwnershipEntity]:
        """Return all entities in the graph."""
        return self.entities.copy()
    
    def get_node_count(self) -> int:
        """Return total number of entities (nodes)."""
        return self.graph.number_of_nodes()
    
    def get_edge_count(self) -> int:
        """Return total number of ownership relationships (edges)."""
        return self.graph.number_of_edges()
    
    def get_predecessors(self, entity_id: str) -> List[str]:
        """
        Get all entities that own the given entity (upstream).
        
        Args:
            entity_id: The entity to find predecessors for
            
        Returns:
            List of entity IDs that own this entity
        """
        if entity_id not in self.graph:
            return []
        return list(self.graph.predecessors(entity_id))
    
    def get_successors(self, entity_id: str) -> List[str]:
        """
        Get all entities owned by the given entity (downstream).
        
        Args:
            entity_id: The entity to find successors for
            
        Returns:
            List of entity IDs owned by this entity
        """
        if entity_id not in self.graph:
            return []
        return list(self.graph.successors(entity_id))
    
    def get_edge_data(self, from_id: str, to_id: str) -> Optional[Dict]:
        """Get the relationship data between two entities."""
        return self.graph.get_edge_data(from_id, to_id)
    
    def validate_graph(self) -> List[str]:
        """
        Validate graph structure. Returns list of warnings.
        
        Checks:
        - Ownership percentages (should sum reasonably)
        - Isolated nodes
        """
        warnings = []
        
        # Check for isolated nodes
        isolated = list(nx.isolates(self.graph))
        if isolated:
            warnings.append(f"Found {len(isolated)} isolated nodes with no ownership relationships")
        
        # Check for nodes with multiple owners where total > 100%
        for node in self.graph.nodes():
            predecessors = list(self.graph.predecessors(node))
            if len(predecessors) > 1:
                total_ownership = sum(
                    self.graph[pred][node].get('ownership_percentage', 0)
                    for pred in predecessors
                )
                if total_ownership > 100:
                    warnings.append(
                        f"Node {node} has ownership exceeding 100% "
                        f"(total: {total_ownership}%)"
                    )
        
        return warnings


# ------------------------------------------------------------------------------
# Mock Data Generator (for Phase 1 testing)
# ------------------------------------------------------------------------------

def create_mock_ownership_graph() -> OwnershipGraphBuilder:
    """
    Create a sample ownership graph with mock data for testing.
    
    Ownership structure:
        John Doe (60%) --?
                         ?-? XYZ Holdings (100%) --? ABC Trading Ltd
        Jane Smith (40%)-?
        
        Plus: Circular reference detection
    """
    builder = OwnershipGraphBuilder()
    
    # Create entities
    john_doe = OwnershipEntity(
        name="John Doe",
        type=EntityType.person,
        jurisdiction="US"
    )
    john_id = builder.add_entity(john_doe)
    
    jane_smith = OwnershipEntity(
        name="Jane Smith",
        type=EntityType.person,
        jurisdiction="US"
    )
    jane_id = builder.add_entity(jane_smith)
    
    xyz_holdings = OwnershipEntity(
        name="XYZ Holdings Ltd",
        type=EntityType.company,
        jurisdiction="UK",
        registration_number="12345678"
    )
    xyz_id = builder.add_entity(xyz_holdings)
    
    abc_trading = OwnershipEntity(
        name="ABC Trading Ltd",
        type=EntityType.company,
        jurisdiction="UK",
        registration_number="87654321"
    )
    abc_id = builder.add_entity(abc_trading)
    
    # Create circular relationship for testing
    circular_company = OwnershipEntity(
        name="Circular Holdings Inc",
        type=EntityType.company,
        jurisdiction="US",
        registration_number="11111111"
    )
    circular_id = builder.add_entity(circular_company)
    
    # Add ownership links
    builder.add_ownership_link(OwnershipLink(
        from_entity_id=john_id,
        to_entity_id=xyz_id,
        ownership_percentage=60.0,
        link_type="ownership",
        source="Companies House"
    ))
    
    builder.add_ownership_link(OwnershipLink(
        from_entity_id=jane_id,
        to_entity_id=xyz_id,
        ownership_percentage=40.0,
        link_type="ownership",
        source="Companies House"
    ))
    
    builder.add_ownership_link(OwnershipLink(
        from_entity_id=xyz_id,
        to_entity_id=abc_id,
        ownership_percentage=100.0,
        link_type="ownership",
        source="Companies House"
    ))
    
    # Circular link: ABC owns back to XYZ (creating a cycle)
    builder.add_ownership_link(OwnershipLink(
        from_entity_id=abc_id,
        to_entity_id=circular_id,
        ownership_percentage=50.0,
        link_type="ownership",
        source="Companies House"
    ))
    
    builder.add_ownership_link(OwnershipLink(
        from_entity_id=circular_id,
        to_entity_id=xyz_id,
        ownership_percentage=100.0,
        link_type="ownership",
        source="Computed"
    ))
    
    logger.info(f"Created mock ownership graph with {builder.get_node_count()} nodes "
                f"and {builder.get_edge_count()} edges")
    
    return builder
