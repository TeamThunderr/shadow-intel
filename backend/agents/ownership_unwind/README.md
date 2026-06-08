# Ownership Unwind Agent - Implementation Documentation

## Overview

The Ownership Unwind Agent is a comprehensive ownership analysis module that detects Ultimate Beneficial Owners (UBOs), analyzes ownership structures, and calculates ownership risk scores using graph-based algorithms.

## Phase 1: Complete Implementation

### ✅ Completed Components

#### 1. **graph_builder.py** (160 lines)
Graph construction and entity management using NetworkX.

**Key Classes:**
- `OwnershipEntity`: Pydantic model representing persons/companies
- `OwnershipLink`: Pydantic model representing ownership relationships
- `OwnershipGraphBuilder`: Manages directed graph construction
- `create_mock_ownership_graph()`: Generates test data with circular references

**Capabilities:**
- Add entities (persons, companies, trusts, funds)
- Create ownership relationships with percentages
- Retrieve predecessors/successors
- Graph validation
- Entity querying by ID

**Mock Data Structure:**
```
John Doe (60%)     ┐
                   ├─→ XYZ Holdings (100%) ──→ ABC Trading Ltd
Jane Smith (40%)   ┘
                   
Circular: ABC → Circular Inc → XYZ (for testing)
```

---

#### 2. **serializer.py** (250 lines)
Converts NetworkX graphs to D3.js-compatible visualization format.

**Key Classes:**
- `GraphNode`: D3.js node format with color coding
- `GraphLink`: D3.js link format with ownership percentages
- `SerializedOwnershipGraph`: Complete graph in D3.js format
- `OwnershipGraphSerializer`: Conversion engine
- `OwnershipVisualizationHelper`: Layout algorithms

**Output Format:**
```json
{
  "nodes": [
    {
      "id": "entity_1",
      "label": "Company Name",
      "type": "company",
      "color": "#ff7f0e",
      "size": 15.5
    }
  ],
  "links": [
    {
      "source": "entity_1",
      "target": "entity_2",
      "value": 75.0,
      "type": "ownership"
    }
  ],
  "metadata": {
    "total_nodes": 5,
    "total_links": 4,
    "directed": true
  }
}
```

**Features:**
- Type-based color coding (person=blue, company=orange, etc.)
- Node sizing by network centrality
- Hierarchical layout support
- D3.js compatible JSON output

---

#### 3. **ubo_detector.py** (400 lines)
Ultimate Beneficial Owner detection and cycle analysis.

**Key Classes:**
- `UBOType`: Enum (natural_person, corporate_entity, nominee, unknown)
- `OwnershipPath`: Represents complete ownership chains
- `UBOEntity`: UBO with confidence score and paths
- `UBODetectionResult`: Complete detection results
- `UBODetector`: Main detection engine

**Algorithms:**
- Depth-first search for path finding
- Cycle detection using NetworkX
- Confidence scoring based on:
  - Natural person status (+0.35)
  - Ownership percentage (+0.40)
  - Chain depth (-penalty)
  - Other factors

**Key Methods:**
- `detect(target_entity_id)`: Find UBOs for target
- `_find_all_ownership_paths()`: Trace all chains
- `_identify_ubos_from_paths()`: Extract UBOs with scores
- `_has_cycles()`: Detect circular ownership
- `_assess_complexity()`: Classify ownership structure

**Output:**
```python
UBODetectionResult(
    target_entity_id="abc_corp",
    ubos=[
        UBOEntity(
            entity_id="john_doe",
            entity_name="John Doe",
            effective_ownership_percentage=60.0,
            confidence_score=0.85,
            is_natural_person=True
        )
    ],
    has_circular_ownership=True,
    max_chain_depth=2,
    complexity_level="moderate"
)
```

---

#### 4. **risk.py** (450 lines)
Comprehensive ownership risk assessment.

**Key Classes:**
- `RiskFactor`: Enum of risk types
- `RiskFactorDetail`: Individual risk with score
- `OwnershipRiskProfile`: Complete risk assessment
- `OwnershipRiskCalculator`: Risk scoring engine

**Risk Factors Assessed:**
1. **Circular Ownership** (0.30 weight)
   - Circular references detected
   - Severity: Critical
   - Score: 0.95 if present

2. **Deep Chain** (0.15 weight)
   - 1-4+ levels of ownership
   - Progressive scoring: 0.25 → 0.85

3. **Multiple UBOs** (0.15 weight)
   - Fragmented ownership
   - Unclear control

4. **Partial Ownership** (0.10 weight)
   - Less than 100% owned
   - Indicates shared control

5. **Unknown Entities** (0.10 weight)
   - Missing type/registration info
   - Undocumented entities

6. **Corporate Veil** (0.15 weight)
   - Heavy intermediary structures
   - Deliberate obscuration

7. **Jurisdiction Risk** (0.05 weight)
   - Offshore financial centers
   - High-risk jurisdictions (VI, BVI, PA, etc.)

8. **Nominee Structures** (0.10 weight)
   - Person owns multiple companies
   - Potential nominee arrangements

**Output:**
```python
OwnershipRiskProfile(
    overall_risk_score=0.68,
    risk_level="high",
    risk_factors=[...],
    key_concerns=[...],
    mitigation_suggestions=[...]
)
```

---

#### 5. **service.py** (350 lines)
Agent orchestration and response building.

**Key Classes:**
- `UBODetail`: Response UBO format
- `CircularOwnershipDetail`: Circular ownership info
- `OwnershipUnwindResponse`: Complete response schema
- `OwnershipUnwindAgent`: BaseAgent implementation
- `OwnershipAnalysisService`: Standalone service

**OwnershipUnwindAgent:**
- Extends `BaseAgent` from shared module
- Async implementation
- Integrates all components
- Returns standardized AgentResponse

**OwnershipAnalysisService:**
- Standalone usage (API routes)
- Synchronous operation
- Direct analysis without orchestrator

**Response Structure:**
```python
{
    "ownership_graph": {...},  # D3.js JSON
    "ultimate_beneficial_owners": [
        {
            "entity_id": "john_doe",
            "entity_name": "John Doe",
            "effective_ownership_percentage": 60.0,
            "confidence_score": 0.85,
            "is_natural_person": True
        }
    ],
    "circular_ownership_detected": {
        "detected": True,
        "entity_count": 3,
        "entity_ids": [...]
    },
    "max_chain_depth": 2,
    "complexity_level": "moderate",
    "ownership_risk_score": 0.68,
    "risk_level": "high",
    "key_concerns": [...],
    "entities_count": 5,
    "relationships_count": 4
}
```

---

#### 6. **__init__.py**
Package initialization with public exports.

---

#### 7. **examples.py**
Comprehensive examples demonstrating all functionality.

---

## Architecture Highlights

### Separation of Concerns
```
┌─────────────────────────────────────────┐
│     OwnershipUnwindAgent (service.py)   │  ← BaseAgent Interface
├─────────────────────────────────────────┤
│  Orchestration Layer                    │
├─────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────┐│
│  │Graph Builder │  │  UBO Detector    ││
│  │(graph.py)    │  │(ubo_detector.py) ││
│  └──────────────┘  └──────────────────┘│
│  ┌──────────────┐  ┌──────────────────┐│
│  │   Serializer │  │Risk Calculator   ││
│  │(serializer)  │  │(risk.py)         ││
│  └──────────────┘  └──────────────────┘│
├─────────────────────────────────────────┤
│  NetworkX Graph (Directed)              │
└─────────────────────────────────────────┘
```

### Data Flow
```
Mock Data (Phase 1)
    ↓
OwnershipGraphBuilder → NetworkX DiGraph
    ↓
UBODetector → UBODetectionResult
    ↓
RiskCalculator → OwnershipRiskProfile
    ↓
Serializer → D3.js JSON
    ↓
OwnershipUnwindAgent → AgentResponse
```

---

## Phase 1 Features Implemented

✅ **Graph Construction**
- Entity management (persons, companies, trusts, funds)
- Ownership relationships with percentages
- Mock data generation
- Graph validation

✅ **UBO Detection**
- Path finding (DFS-based)
- Circular ownership detection
- Confidence scoring
- Complexity assessment

✅ **Risk Assessment**
- 8 risk factors evaluated
- Weighted scoring system
- Risk level classification (low/medium/high/critical)
- Mitigation suggestions

✅ **Visualization**
- D3.js compatible JSON
- Color coding by entity type
- Node sizing by centrality
- Hierarchical layout support

✅ **Integration**
- BaseAgent compliance
- Pydantic models throughout
- Async/sync support
- Evidence generation

---

## Phase 2 Enhancement Plan (Future)

### API Integrations
- [ ] Companies House API
- [ ] SEC EDGAR
- [ ] OpenOwnership API
- [ ] GLEIF Entity Data

### Advanced Features
- [ ] Beneficial ownership thresholds
- [ ] Sanctions list matching
- [ ] Director overlap detection
- [ ] Address clustering
- [ ] Timeline tracking
- [ ] Change detection

### Performance
- [ ] Database caching
- [ ] Incremental updates
- [ ] Batch processing
- [ ] Query optimization

---

## Code Quality

### Type Hints
- ✅ 100% type coverage
- ✅ Pydantic v2 models
- ✅ Generic types used appropriately

### Documentation
- ✅ Docstrings on all classes/methods
- ✅ Type hints throughout
- ✅ Architecture diagrams
- ✅ Examples provided

### Testing Readiness
- ✅ Mock data generator
- ✅ Examples file
- ✅ Modular design for unit testing
- ✅ Dependency injection patterns

---

## Usage Examples

### Example 1: Using the Agent
```python
from agents.ownership_unwind import OwnershipUnwindAgent
from shared.schemas import EntityFingerprint

agent = OwnershipUnwindAgent()
fingerprint = EntityFingerprint(
    entity_id="entity_123",
    canonical_name="ABC Trading Ltd"
)

response = await agent.run(fingerprint)
print(f"Risk Score: {response.risk_score}")
print(f"UBOs Found: {len(response.data['ultimate_beneficial_owners'])}")
```

### Example 2: Standalone Service
```python
from agents.ownership_unwind import OwnershipAnalysisService

service = OwnershipAnalysisService()
result = service.analyze("entity_id")

print(f"Complexity: {result.complexity_level}")
print(f"Risk Level: {result.risk_level}")
```

### Example 3: Manual Analysis
```python
from agents.ownership_unwind import (
    create_mock_ownership_graph,
    UBODetector,
    OwnershipRiskCalculator,
    OwnershipGraphSerializer
)

builder = create_mock_ownership_graph()
graph = builder.get_graph()

detector = UBODetector(graph)
ubo_result = detector.detect(target_id)

calculator = OwnershipRiskCalculator(graph, ubo_result)
risk_profile = calculator.calculate()

serializer = OwnershipGraphSerializer(graph)
d3_json = serializer.to_dict()
```

---

## Integration with Shadow Intel

### Orchestrator Integration
The OwnershipUnwindAgent integrates with Shadow Intel's orchestrator:

```
InvestigationRequest
    ↓
Orchestrator.run()
    ├─→ GhostTracker (creates EntityFingerprint)
    ├─→ OwnershipUnwindAgent (this module)
    ├─→ MoneyTrail
    ├─→ DarkSignal
    └─→ Resurface
    ↓
InvestigationResponse (consolidated)
```

### API Routes
Can be exposed via FastAPI routes:

```python
@router.post("/api/investigate/ownership/{entity_id}")
async def analyze_ownership(entity_id: str):
    service = OwnershipAnalysisService()
    result = service.analyze(entity_id)
    return result
```

---

## File Structure

```
backend/agents/ownership_unwind/
├── __init__.py                 # Package exports
├── graph_builder.py            # Entity & relationship management
├── serializer.py               # D3.js visualization
├── ubo_detector.py             # UBO detection algorithms
├── risk.py                     # Risk assessment
├── service.py                  # Agent implementation
└── examples.py                 # Usage demonstrations
```

---

## Dependencies

- **networkx==3.3**: Graph algorithms and data structures
- **pydantic==2.7.0**: Data validation and serialization
- **Python 3.11+**: Type hints and async features

---

## Testing

Run the examples file to test all components:

```bash
cd backend/agents/ownership_unwind
python examples.py
```

---

## Author Notes

This Phase 1 implementation provides a solid foundation for ownership analysis with:
- Clean, modular architecture
- Type-safe Pydantic models
- Comprehensive documentation
- Extensible design for Phase 2 APIs
- Production-ready code patterns

Next phase will add real data sources and advanced algorithms while maintaining this structure.

---

**Status**: ✅ Phase 1 Complete - Ready for integration and testing
**Last Updated**: 2024
**Version**: 1.0.0-phase1
