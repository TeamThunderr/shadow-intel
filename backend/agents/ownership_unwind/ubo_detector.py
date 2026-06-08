"""
UBO (Ultimate Beneficial Owner) Detection Module

Identifies ultimate beneficial owners, traces ownership chains,
and detects circular/cyclical ownership structures.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Set, Dict
from enum import Enum
import networkx as nx
from backend.shared.logger import get_logger

logger = get_logger(__name__)


class UBOType(str, Enum):
    """Classification of UBO detection confidence."""
    natural_person = "natural_person"  # Individual
    corporate_entity = "corporate_entity"  # Company/Trust/Fund
    nominee = "nominee"  # Potential nominee structure
    unknown = "unknown"


class OwnershipPath(BaseModel):
    """Represents a complete ownership chain from UBO to target."""
    path: List[str] = Field(description="List of entity IDs from owner to target")
    total_ownership_percentage: float = Field(
        ge=0.0, le=100.0,
        description="Cumulative ownership percentage through chain"
    )
    depth: int = Field(ge=1, description="Number of hops in the chain")
    link_sources: List[str] = Field(default_factory=list, description="Sources of links")
    link_source_systems: List[str] = Field(default_factory=list, description="Source systems of links")
    link_source_references: List[str] = Field(default_factory=list, description="Source references of links")
    
    class Config:
        use_enum_values = False


class UBOEntity(BaseModel):
    """Ultimate Beneficial Owner with confidence score."""
    entity_id: str
    entity_name: str
    entity_type: UBOType
    direct_ownership_percentage: Optional[float] = None
    effective_ownership_percentage: float = Field(ge=0.0, le=100.0)
    ownership_paths: List[OwnershipPath] = []
    depth_from_target: int = Field(ge=0, description="Minimum hops from target entity")
    is_natural_person: bool = Field(
        description="Whether UBO is a natural person (high priority for regulation)"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Confidence that this is the true UBO (1.0 = definitive)"
    )


class UBODetectionResult(BaseModel):
    """Complete UBO detection results."""
    target_entity_id: str
    target_entity_name: str
    ubos: List[UBOEntity] = []
    has_circular_ownership: bool = False
    circular_entities: List[str] = Field(default_factory=list, description="IDs of entities in cycles")
    max_chain_depth: int = 0
    complexity_level: str = Field(default="simple", description="simple|moderate|complex|critical")
    confidence_threshold_applied: float = Field(default=0.5, ge=0.0, le=1.0)


class UBODetector:
    """
    Detects Ultimate Beneficial Owners and analyzes ownership structures.
    
    Algorithms:
    - DFS/BFS to trace ownership chains
    - Cycle detection (NetworkX algorithms)
    - Confidence scoring based on ownership percentage and chain length
    """
    
    def __init__(self, graph: nx.DiGraph, confidence_threshold: float = 0.5):
        """
        Initialize UBO detector with ownership graph.
        
        Args:
            graph: NetworkX DiGraph of ownership relationships
            confidence_threshold: Minimum confidence to report UBO (0.0-1.0)
        """
        self.graph = graph
        self.confidence_threshold = confidence_threshold
        self.logger = get_logger(self.__class__.__name__)
    
    def detect(self, target_entity_id: str) -> UBODetectionResult:
        """
        Detect ultimate beneficial owners for a given entity.
        
        Args:
            target_entity_id: The entity to investigate (typically a company)
            
        Returns:
            UBODetectionResult with comprehensive ownership analysis
        """
        if target_entity_id not in self.graph:
            self.logger.warning(f"Target entity {target_entity_id} not in graph")
            return UBODetectionResult(
                target_entity_id=target_entity_id,
                target_entity_name="Unknown",
                ubos=[],
                has_circular_ownership=False
            )
        
        target_name = self.graph.nodes[target_entity_id].get("name", target_entity_id)
        result = UBODetectionResult(
            target_entity_id=target_entity_id,
            target_entity_name=target_name,
            confidence_threshold_applied=self.confidence_threshold
        )
        
        # Detect cycles
        result.has_circular_ownership = self._has_cycles()
        if result.has_circular_ownership:
            result.circular_entities = self._find_cycle_entities()
        
        # Find ownership paths
        ownership_paths = self._find_all_ownership_paths(target_entity_id)
        
        # Identify UBOs from paths
        ubos_dict = self._identify_ubos_from_paths(ownership_paths)
        result.ubos = list(ubos_dict.values())
        
        # Set complexity level
        result.max_chain_depth = max(
            (p.depth for p in ownership_paths),
            default=0
        )
        result.complexity_level = self._assess_complexity(result)
        
        self.logger.info(
            f"Detected {len(result.ubos)} UBOs for {target_name} "
            f"(depth: {result.max_chain_depth}, cycles: {result.has_circular_ownership})"
        )
        
        return result
    
    def _find_all_ownership_paths(self, target_entity_id: str) -> List[OwnershipPath]:
        """
        Find all ownership paths from predecessors to target entity.
        
        Uses DFS to trace all paths through the graph going backwards.
        
        Args:
            target_entity_id: Starting entity for path finding
            
        Returns:
            List of OwnershipPath objects
        """
        paths = []
        visited_global = set()
        
        # Recursive DFS for path finding
        def dfs(current_id: str, path: List[str], 
                ownership_pct: float, link_sources: List[str],
                link_source_systems: List[str], link_source_references: List[str],
                visited_path: Set[str]) -> None:
            """
            Depth-first search to find ownership paths.
            
            Args:
                current_id: Current entity in traversal
                path: List of entity IDs in current path (target first)
                ownership_pct: Cumulative ownership percentage
                link_sources: Sources of relationships
                link_source_systems: Source systems of relationships
                link_source_references: Source references of relationships
                visited_path: Entities visited in current path (cycle detection)
            """
            # Get predecessors (entities that own current entity)
            predecessors = list(self.graph.predecessors(current_id))
            
            if not predecessors:
                # Leaf node (root owner) - we found a complete path
                if len(path) > 1:
                    paths.append(OwnershipPath(
                        path=path,
                        total_ownership_percentage=ownership_pct,
                        depth=len(path) - 1,
                        link_sources=link_sources,
                        link_source_systems=link_source_systems,
                        link_source_references=link_source_references
                    ))
                return
            
            # Explore each predecessor
            for pred_id in predecessors:
                # Avoid infinite loops in current path
                if pred_id in visited_path:
                    continue
                
                edge_data = self.graph[pred_id][current_id]
                ownership_pct_link = edge_data.get("ownership_percentage", 100.0)
                link_source = edge_data.get("source", "unknown")
                link_src_system = edge_data.get("source_system", "unknown")
                link_src_ref = edge_data.get("source_reference", "unknown")
                
                new_path = path + [pred_id]
                new_ownership = ownership_pct * (ownership_pct_link / 100.0)
                new_sources = link_sources + [link_source]
                new_src_systems = link_source_systems + [str(link_src_system)]
                new_src_refs = link_source_references + [str(link_src_ref)]
                new_visited = visited_path | {pred_id}
                
                dfs(pred_id, new_path, new_ownership, new_sources, new_src_systems, new_src_refs, new_visited)
        
        # Start DFS from target
        dfs(
            target_entity_id,
            path=[target_entity_id],
            ownership_pct=100.0,
            link_sources=[],
            link_source_systems=[],
            link_source_references=[],
            visited_path={target_entity_id}
        )
        
        return paths
    
    def _identify_ubos_from_paths(self, paths: List[OwnershipPath]) -> Dict[str, UBOEntity]:
        """
        Identify Ultimate Beneficial Owners from ownership paths.
        
        Rules:
        - Natural persons at the end of chains are high-confidence UBOs
        - Single-owner paths are more certain
        - Circular references reduce confidence
        
        Args:
            paths: List of ownership paths to analyze
            
        Returns:
            Dict mapping entity_id to UBOEntity
        """
        ubos: Dict[str, UBOEntity] = {}
        
        for path in paths:
            if len(path.path) < 2:
                continue  # Ignore single-entity paths
            
            # The first entity in path (after reversing) is the owner
            owner_id = path.path[-1]
            target_id = path.path[0]
            
            if owner_id not in self.graph.nodes:
                continue
            
            owner_data = self.graph.nodes[owner_id]
            owner_name = owner_data.get("name", owner_id)
            owner_type_str = owner_data.get("type", "unknown")
            
            # Determine if natural person
            is_natural_person = owner_type_str == "person"
            
            # Determine UBO type
            if is_natural_person:
                ubo_type = UBOType.natural_person
            else:
                ubo_type = UBOType.corporate_entity
            
            # Calculate confidence
            # Higher confidence for: natural persons, shorter chains, higher ownership
            confidence = self._calculate_ubo_confidence(
                path,
                is_natural_person,
                owner_id,
                target_id
            )
            
            if confidence >= self.confidence_threshold:
                if owner_id not in ubos:
                    ubos[owner_id] = UBOEntity(
                        entity_id=owner_id,
                        entity_name=owner_name,
                        entity_type=ubo_type,
                        effective_ownership_percentage=path.total_ownership_percentage,
                        depth_from_target=path.depth,
                        is_natural_person=is_natural_person,
                        confidence_score=confidence,
                        ownership_paths=[path]
                    )
                else:
                    # Update existing UBO with additional path
                    ubos[owner_id].ownership_paths.append(path)
                    # Update effective ownership (take max from multiple paths)
                    ubos[owner_id].effective_ownership_percentage = max(
                        ubos[owner_id].effective_ownership_percentage,
                        path.total_ownership_percentage
                    )
        
        return ubos
    
    def _calculate_ubo_confidence(
        self,
        path: OwnershipPath,
        is_natural_person: bool,
        owner_id: str,
        target_id: str
    ) -> float:
        """
        Calculate confidence score for a UBO.
        
        Factors:
        - Natural persons: +0.3
        - Ownership percentage: +0.4 (scaled by %)
        - Chain depth: -0.3 (longer chains = less certainty)
        - No cycles involving this owner: +0.0 or neutral
        
        Args:
            path: The ownership path
            is_natural_person: Whether owner is a person
            owner_id: Owner entity ID
            target_id: Target entity ID
            
        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.0
        
        # Natural person factor
        if is_natural_person:
            confidence += 0.40
        else:
            confidence += 0.15
        
        # Ownership percentage factor
        ownership_factor = min(path.total_ownership_percentage / 100.0, 1.0)
        confidence += ownership_factor * 0.35
        
        # Depth penalty (longer chains less certain)
        if path.depth <= 1:
            confidence += 0.20
        elif path.depth <= 2:
            confidence += 0.10
        elif path.depth <= 3:
            confidence += 0.05
        # else: deeper chains get no bonus
        
        # Ensure bounds
        return min(max(confidence, 0.0), 1.0)
    
    def _has_cycles(self) -> bool:
        """Check if graph contains any cycles (circular ownership)."""
        try:
            nx.find_cycle(self.graph)
            return True
        except nx.NetworkXNoCycle:
            return False
    
    def _find_cycle_entities(self) -> List[str]:
        """
        Find all entities involved in cycles.
        
        Returns:
            List of entity IDs that are part of circular ownership
        """
        cycle_entities = []
        
        # Find all simple cycles
        try:
            cycles = nx.simple_cycles(self.graph)
            for cycle in cycles:
                cycle_entities.extend(cycle)
        except:
            pass
        
        return list(set(cycle_entities))
    
    def _assess_complexity(self, result: UBODetectionResult) -> str:
        """
        Assess complexity of ownership structure.
        
        Args:
            result: The UBO detection result
            
        Returns:
            Complexity level: simple, moderate, complex, or critical
        """
        if len(result.ubos) == 0:
            return "simple"
        
        score = 0
        
        # Multiple UBOs increases complexity
        score += min(len(result.ubos) - 1, 3)
        
        # Circular ownership increases complexity significantly
        if result.has_circular_ownership:
            score += 3
        
        # Deep chains increase complexity
        if result.max_chain_depth > 2:
            score += 2
        elif result.max_chain_depth > 1:
            score += 1
        
        # Non-100% ownership increases complexity
        has_partial = any(u.effective_ownership_percentage < 100 for u in result.ubos)
        if has_partial:
            score += 1
        
        if score >= 8:
            return "critical"
        elif score >= 5:
            return "complex"
        elif score >= 2:
            return "moderate"
        else:
            return "simple"
