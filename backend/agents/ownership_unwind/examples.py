"""
Ownership Unwind Agent - Example Usage and Testing

This module demonstrates how to use the Ownership Unwind Agent
components for ownership analysis.

Phase 1 Focus: Mock data demonstration
Phase 2: Will integrate with real APIs
"""

import asyncio
from .graph_builder import (
    OwnershipGraphBuilder,
    OwnershipEntity,
    OwnershipLink,
    EntityType,
    create_mock_ownership_graph,
)
from .ubo_detector import (
    UBODetector,
)
from .risk import (
    OwnershipRiskCalculator,
)
from .serializer import (
    OwnershipGraphSerializer,
)
from .service import (
    OwnershipUnwindAgent,
    OwnershipAnalysisService,
)

try:
    from shared.schemas import EntityFingerprint, EntityType as SchemaEntityType
except ImportError:
    # Fallback for running from examples
    from pydantic import BaseModel, Field
    from typing import Optional
    
    class EntityFingerprint(BaseModel):
        entity_id: str
        canonical_name: str
        aliases: list[str] = []
        jurisdictions: list[str] = []
        directors: list[str] = []
        addresses: list[str] = []
        registration_numbers: list[str] = []
        sanctions_lists: list[str] = []


# ──────────────────────────────────────────────────────────────────────────────
# Example 1: Manual Graph Building
# ──────────────────────────────────────────────────────────────────────────────

def example_manual_graph_building():
    """
    Demonstrates how to manually build an ownership graph.
    
    Output:
    -------
    A NetworkX graph representing:
    
        Alice (50%) ──┐
                      ├─→ Holding Co Ltd ──→ Trading Corp
        Bob (50%) ────┘
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Manual Graph Building")
    print("="*70)
    
    # Create builder
    builder = OwnershipGraphBuilder()
    
    # Add entities
    alice = OwnershipEntity(
        name="Alice Johnson",
        type=EntityType.person,
        jurisdiction="US"
    )
    alice_id = builder.add_entity(alice)
    
    bob = OwnershipEntity(
        name="Bob Smith",
        type=EntityType.person,
        jurisdiction="US"
    )
    bob_id = builder.add_entity(bob)
    
    holding_co = OwnershipEntity(
        name="Holding Co Ltd",
        type=EntityType.company,
        jurisdiction="UK",
        registration_number="12345678"
    )
    holding_id = builder.add_entity(holding_co)
    
    trading_corp = OwnershipEntity(
        name="Trading Corp",
        type=EntityType.company,
        jurisdiction="UK",
        registration_number="87654321"
    )
    trading_id = builder.add_entity(trading_corp)
    
    # Add ownership links
    builder.add_ownership_link(OwnershipLink(
        from_entity_id=alice_id,
        to_entity_id=holding_id,
        ownership_percentage=50.0,
        link_type="ownership",
        source="Companies House"
    ))
    
    builder.add_ownership_link(OwnershipLink(
        from_entity_id=bob_id,
        to_entity_id=holding_id,
        ownership_percentage=50.0,
        link_type="ownership",
        source="Companies House"
    ))
    
    builder.add_ownership_link(OwnershipLink(
        from_entity_id=holding_id,
        to_entity_id=trading_id,
        ownership_percentage=100.0,
        link_type="ownership",
        source="Companies House"
    ))
    
    # Report
    print(f"\n✓ Built ownership graph:")
    print(f"  - Total entities: {builder.get_node_count()}")
    print(f"  - Total relationships: {builder.get_edge_count()}")
    print(f"  - Entities: {', '.join(e.name for e in builder.get_all_entities().values())}")
    
    # Validate
    warnings = builder.validate_graph()
    if warnings:
        print(f"\n⚠️  Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print(f"\n✓ Graph validation passed")
    
    return builder


# ──────────────────────────────────────────────────────────────────────────────
# Example 2: Using Mock Data
# ──────────────────────────────────────────────────────────────────────────────

def example_mock_data():
    """
    Demonstrates using the built-in mock ownership graph.
    
    Includes circular ownership for testing cycle detection.
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Using Mock Data")
    print("="*70)
    
    builder = create_mock_ownership_graph()
    
    print(f"\n✓ Created mock ownership graph:")
    print(f"  - Entities: {builder.get_node_count()}")
    print(f"  - Relationships: {builder.get_edge_count()}")
    
    # Print structure
    print(f"\nOwnership structure:")
    for entity_id, entity in builder.get_all_entities().items():
        predecessors = builder.get_predecessors(entity_id)
        successors = builder.get_successors(entity_id)
        
        role = "Owner" if not predecessors else "Target" if not successors else "Intermediary"
        print(f"  [{role}] {entity.name}")
        
        if successors:
            for succ_id in successors:
                succ_entity = builder.get_entity(succ_id)
                edge_data = builder.get_edge_data(entity_id, succ_id)
                ownership = edge_data.get('ownership_percentage', 100)
                print(f"    └─ owns {ownership}% of {succ_entity.name}")
    
    return builder


# ──────────────────────────────────────────────────────────────────────────────
# Example 3: UBO Detection
# ──────────────────────────────────────────────────────────────────────────────

def example_ubo_detection():
    """
    Demonstrates Ultimate Beneficial Owner detection.
    
    Shows:
    - UBO identification with confidence scores
    - Ownership path tracing
    - Circular ownership detection
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Ultimate Beneficial Owner Detection")
    print("="*70)
    
    builder = create_mock_ownership_graph()
    graph = builder.get_graph()
    
    # Create detector
    detector = UBODetector(graph, confidence_threshold=0.5)
    
    # Get a company to analyze
    target_id = None
    for entity_id, entity in builder.get_all_entities().items():
        if entity.type == EntityType.company:
            target_id = entity_id
            break
    
    if not target_id:
        print("No company entities found in graph")
        return
    
    target_entity = builder.get_entity(target_id)
    print(f"\n📊 Analyzing ownership of: {target_entity.name}")
    
    # Detect UBOs
    ubo_result = detector.detect(target_id)
    
    print(f"\n✓ Detection results:")
    print(f"  - UBOs identified: {len(ubo_result.ubos)}")
    print(f"  - Max chain depth: {ubo_result.max_chain_depth}")
    print(f"  - Circular ownership: {ubo_result.has_circular_ownership}")
    print(f"  - Complexity level: {ubo_result.complexity_level}")
    
    if ubo_result.ubos:
        print(f"\n👤 Ultimate Beneficial Owners:")
        for ubo in ubo_result.ubos:
            print(f"\n  {ubo.entity_name}")
            print(f"    - Type: {ubo.entity_type.value}")
            print(f"    - Ownership: {ubo.effective_ownership_percentage:.1f}%")
            print(f"    - Confidence: {ubo.confidence_score:.2f}")
            print(f"    - Depth: {ubo.depth_from_target} levels")
            print(f"    - Natural person: {ubo.is_natural_person}")
            
            if ubo.ownership_paths:
                print(f"    - Ownership paths: {len(ubo.ownership_paths)}")
                for i, path in enumerate(ubo.ownership_paths[:1]):  # Show first path
                    path_str = " → ".join([
                        builder.get_entity(eid).name for eid in path.path
                    ])
                    print(f"      Path {i+1}: {path_str}")
    
    if ubo_result.has_circular_ownership:
        print(f"\n🔄 Circular ownership detected!")
        print(f"  Entities involved: {len(ubo_result.circular_entities)}")
        for entity_id in ubo_result.circular_entities:
            entity = builder.get_entity(entity_id)
            print(f"    - {entity.name}")
    
    return ubo_result


# ──────────────────────────────────────────────────────────────────────────────
# Example 4: Risk Calculation
# ──────────────────────────────────────────────────────────────────────────────

def example_risk_calculation():
    """
    Demonstrates ownership risk score calculation.
    
    Shows:
    - Risk factors identified
    - Overall risk score
    - Risk level classification
    - Mitigation suggestions
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Ownership Risk Calculation")
    print("="*70)
    
    builder = create_mock_ownership_graph()
    graph = builder.get_graph()
    
    # Detect UBOs first
    detector = UBODetector(graph, confidence_threshold=0.5)
    target_id = None
    for entity_id, entity in builder.get_all_entities().items():
        if entity.type == EntityType.company:
            target_id = entity_id
            break
    
    ubo_result = detector.detect(target_id)
    
    # Calculate risk
    calculator = OwnershipRiskCalculator(graph, ubo_result)
    risk_profile = calculator.calculate()
    
    print(f"\n📈 Risk Assessment Results:")
    print(f"  - Overall Score: {risk_profile.overall_risk_score:.2f} (0.0-1.0)")
    print(f"  - Risk Level: {risk_profile.risk_level.upper()}")
    print(f"  - Risk Factors: {len(risk_profile.risk_factors)}")
    
    if risk_profile.risk_factors:
        print(f"\n⚠️  Risk Factors:")
        for factor in risk_profile.risk_factors:
            print(f"\n  [{factor.severity.upper()}] {factor.factor.value.replace('_', ' ').title()}")
            print(f"    Score: {factor.score:.2f}")
            print(f"    {factor.description}")
    
    if risk_profile.key_concerns:
        print(f"\n🚨 Key Concerns:")
        for concern in risk_profile.key_concerns:
            print(f"  {concern}")
    
    if risk_profile.mitigation_suggestions:
        print(f"\n💡 Mitigation Suggestions:")
        for suggestion in risk_profile.mitigation_suggestions:
            print(f"  - {suggestion}")
    
    return risk_profile


# ──────────────────────────────────────────────────────────────────────────────
# Example 5: Graph Serialization (D3.js Format)
# ──────────────────────────────────────────────────────────────────────────────

def example_graph_serialization():
    """
    Demonstrates converting the NetworkX graph to D3.js compatible JSON.
    
    Output format:
    {
        "nodes": [
            {"id": "...", "label": "...", "type": "...", "color": "..."},
            ...
        ],
        "links": [
            {"source": "...", "target": "...", "value": 50.0},
            ...
        ]
    }
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Graph Serialization (D3.js Format)")
    print("="*70)
    
    builder = create_mock_ownership_graph()
    graph = builder.get_graph()
    
    serializer = OwnershipGraphSerializer(graph)
    serialized = serializer.serialize()
    
    print(f"\n✓ Serialization results:")
    print(f"  - Total nodes: {len(serialized.nodes)}")
    print(f"  - Total links: {len(serialized.links)}")
    
    print(f"\nNodes (D3.js compatible):")
    for node in serialized.nodes[:3]:  # Show first 3
        print(f"  - {node.label}")
        print(f"    id: {node.id}")
        print(f"    type: {node.type}")
        print(f"    color: {node.color}")
        print(f"    size: {node.size:.1f}")
    
    if len(serialized.nodes) > 3:
        print(f"  ... and {len(serialized.nodes) - 3} more")
    
    print(f"\nLinks (D3.js compatible):")
    for link in serialized.links[:3]:  # Show first 3
        source_entity = builder.get_entity(link.source)
        target_entity = builder.get_entity(link.target)
        print(f"  - {source_entity.name} --({link.value}%)--> {target_entity.name}")
    
    if len(serialized.links) > 3:
        print(f"  ... and {len(serialized.links) - 3} more")
    
    # Get JSON format
    json_data = serializer.to_dict()
    print(f"\nJSON structure ready for frontend visualization")
    print(f"Keys: {list(json_data.keys())}")
    
    return json_data


# ──────────────────────────────────────────────────────────────────────────────
# Example 6: Using the Agent
# ──────────────────────────────────────────────────────────────────────────────

async def example_agent_usage():
    """
    Demonstrates using the OwnershipUnwindAgent directly.
    
    This shows how it integrates with the BaseAgent pattern
    and will be called by the orchestrator.
    """
    print("\n" + "="*70)
    print("EXAMPLE 6: Using OwnershipUnwindAgent")
    print("="*70)
    
    agent = OwnershipUnwindAgent()
    
    # Create a sample fingerprint
    fingerprint = EntityFingerprint(
        entity_id="entity_123",
        canonical_name="ABC Trading Ltd",
        aliases=["ABC Ltd", "ABC Corp"],
        registration_numbers=["87654321"],
        jurisdictions=["UK"]
    )
    
    print(f"\n📋 Analyzing entity: {fingerprint.canonical_name}")
    
    # Run agent
    response = await agent.run(fingerprint)
    
    print(f"\n✓ Agent execution completed:")
    print(f"  - Status: {response.status}")
    print(f"  - Processing time: {response.processing_time_ms}ms")
    print(f"  - Risk score: {response.risk_score:.2f}")
    print(f"  - Evidence items: {len(response.evidence)}")
    
    # Extract data from response
    data = response.data
    if data:
        print(f"\n📊 Analysis results:")
        print(f"  - UBOs identified: {len(data.get('ultimate_beneficial_owners', []))}")
        print(f"  - Entities in graph: {data.get('entities_count', 0)}")
        print(f"  - Relationships: {data.get('relationships_count', 0)}")
        print(f"  - Risk level: {data.get('risk_level', 'unknown')}")
        print(f"  - Max chain depth: {data.get('max_chain_depth', 0)}")
        print(f"  - Circular ownership: {data.get('circular_ownership_detected', {}).get('detected', False)}")
    
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Example 7: Using the Service (Non-Agent)
# ──────────────────────────────────────────────────────────────────────────────

def example_service_usage():
    """
    Demonstrates using the standalone OwnershipAnalysisService.
    
    This can be used directly in API routes without agent orchestration.
    """
    print("\n" + "="*70)
    print("EXAMPLE 7: Using OwnershipAnalysisService")
    print("="*70)
    
    service = OwnershipAnalysisService()
    
    # Get a target entity from mock data
    builder = create_mock_ownership_graph()
    target_id = None
    for entity_id, entity in builder.get_all_entities().items():
        if entity.type == EntityType.company:
            target_id = entity_id
            break
    
    if not target_id:
        print("No target entity found")
        return
    
    print(f"\n🔍 Analyzing with service...")
    response = service.analyze(target_id)
    
    print(f"\n✓ Service analysis completed:")
    print(f"  - UBOs found: {len(response.ultimate_beneficial_owners)}")
    print(f"  - Risk score: {response.ownership_risk_score:.2f}")
    print(f"  - Risk level: {response.risk_level}")
    print(f"  - Entities: {response.entities_count}")
    print(f"  - Relationships: {response.relationships_count}")
    
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Main Demo Runner
# ──────────────────────────────────────────────────────────────────────────────

def run_all_examples():
    """Run all examples in sequence."""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + " OWNERSHIP UNWIND AGENT - PHASE 1 EXAMPLES ".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    
    try:
        # Sync examples
        example_manual_graph_building()
        example_mock_data()
        example_ubo_detection()
        example_risk_calculation()
        example_graph_serialization()
        example_service_usage()
        
        # Async example
        print("\n" + "="*70)
        print("EXAMPLE 6: Using OwnershipUnwindAgent (Async)")
        print("="*70)
        asyncio.run(example_agent_usage())
        
        print("\n" + "█"*70)
        print("█" + " ALL EXAMPLES COMPLETED SUCCESSFULLY ".center(68) + "█")
        print("█"*70)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_examples()
