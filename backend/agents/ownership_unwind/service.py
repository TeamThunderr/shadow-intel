"""
Ownership Unwind Agent Service

Main agent implementation integrating graph building, UBO detection,
risk calculation, and serialization.

Phase 2: Integrates real data sources (OpenOwnership, Companies House, SEC EDGAR)
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time
import asyncio
from datetime import datetime
from shared.schemas import (
    AgentResponse, EntityFingerprint, AgentStatus, EvidenceItem
)
from shared.logger import get_logger
from agents.base import BaseAgent
from .graph_builder import (
    OwnershipGraphBuilder, OwnershipEntity, OwnershipLink,
    EntityType, create_mock_ownership_graph
)
from .serializer import OwnershipGraphSerializer, SerializedOwnershipGraph
from .ubo_detector import UBODetector, UBODetectionResult
from .risk import OwnershipRiskCalculator, OwnershipRiskProfile
from .sources import openownership, companies_house, sec_edgar

logger = get_logger(__name__)


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Helper to parse a date string into a datetime object for EvidenceItem."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(str(date_str), "%Y-%m-%d")
        except ValueError:
            return None


class UBODetail(BaseModel):
    """UBO details for response."""
    entity_id: str
    entity_name: str
    entity_type: str
    effective_ownership_percentage: float
    depth_from_target: int
    is_natural_person: bool
    confidence_score: float
    source_system: Optional[str] = None
    source_reference: Optional[str] = None
    
    class Config:
        use_enum_values = False


class CircularOwnershipDetail(BaseModel):
    """Details about circular ownership detected."""
    detected: bool
    entity_count: int
    entity_ids: List[str] = []


class OwnershipUnwindResponse(BaseModel):
    """
    Ownership Unwind Agent response.
    
    Returns complete ownership analysis including:
    - Graph visualization (D3.js compatible)
    - Ultimate Beneficial Owners with confidence
    - Circular ownership detection
    - Risk assessment
    - Chain depth analysis
    """
    ownership_graph: Dict[str, Any]
    ultimate_beneficial_owners: List[UBODetail]
    circular_ownership_detected: CircularOwnershipDetail
    max_chain_depth: int
    complexity_level: str  # simple, moderate, complex, critical
    ownership_risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: str  # low, medium, high, critical
    key_concerns: List[str] = []
    entities_count: int
    relationships_count: int
    evidence: List[Dict[str, Any]] = []
    
    class Config:
        use_enum_values = False


class OwnershipUnwindAgent(BaseAgent):
    """
    Ultimate Beneficial Owner (UBO) Detection and Ownership Analysis Agent.
    
    Responsibilities:
    1. Build ownership graph from available data (APIs or mock)
    2. Detect ultimate beneficial owners
    3. Identify circular ownership structures
    4. Calculate ownership risk scores
    5. Generate D3.js compatible visualization
    6. Provide evidence chain
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
    
    @property
    def module_name(self) -> str:
        """Return module identifier."""
        return "ownership_unwind"
    
    async def run(self, fingerprint: EntityFingerprint) -> AgentResponse:
        """
        Execute ownership analysis for an entity.
        
        Args:
            fingerprint: Entity fingerprint from Ghost Tracker
            
        Returns:
            AgentResponse with ownership analysis results
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting ownership analysis for {fingerprint.canonical_name}")
            
            # Build ownership graph using real data (falls back to mock if all fail)
            graph_builder = await self._build_ownership_graph(
                use_real_data=True,
                entity_name=fingerprint.canonical_name
            )
            graph = graph_builder.get_graph()
            
            # Detect UBOs
            ubo_detector = UBODetector(
                graph,
                confidence_threshold=0.5
            )
            ubo_result = ubo_detector.detect(
                self._find_target_entity_id(graph_builder, fingerprint)
            )
            
            # Calculate risk
            risk_calculator = OwnershipRiskCalculator(graph, ubo_result)
            risk_profile = risk_calculator.calculate()
            
            # Serialize graph
            serializer = OwnershipGraphSerializer(graph)
            graph_json = serializer.to_dict()
            
            # Build response
            response_data = self._build_response(
                graph_builder,
                graph_json,
                ubo_result,
                risk_profile,
                fingerprint
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return AgentResponse(
                module=self.module_name,
                entity_id=fingerprint.entity_id,
                status=AgentStatus.complete,
                processing_time_ms=elapsed_ms,
                risk_score=risk_profile.overall_risk_score,
                evidence=self._build_evidence(graph_builder, ubo_result, risk_profile),
                data=response_data.model_dump()
            )
            
        except Exception as e:
            self.logger.error(f"Error in ownership analysis: {e}", exc_info=True)
            raise
    
    async def _build_ownership_graph(
        self,
        use_real_data: bool = True,
        entity_name: Optional[str] = None
    ) -> OwnershipGraphBuilder:
        """
        Build ownership graph from available data sources.
        
        Data source priority (if available):
        1. Companies House (UK companies)
        2. SEC EDGAR (US companies)
        3. OpenOwnership (International) - Strictly optional
        
        Returns:
            OwnershipGraphBuilder with populated graph
        """
        builder = OwnershipGraphBuilder()
        
        if not use_real_data or not entity_name:
            return create_mock_ownership_graph()
        
        # Real data from multiple sources
        try:
            self.logger.info(f"Building ownership graph for {entity_name} using real data sources")
            
            # Try Companies House first (for UK companies)
            ch_results = await companies_house.search_companies(entity_name, limit=5)
            if ch_results:
                self.logger.info(f"Found {len(ch_results)} Companies House results")
                for result in ch_results:
                    await self._process_companies_house_result(builder, result)
            
            # Try SEC EDGAR (for US companies)
            edgar_results = await sec_edgar.search_companies(entity_name, limit=5)
            if edgar_results:
                self.logger.info(f"Found {len(edgar_results)} SEC EDGAR results")
                for result in edgar_results:
                    await self._process_edgar_result(builder, result)
            
            # Try OpenOwnership (international) - treated as strictly optional
            try:
                oo_results = await openownership.search_companies(entity_name, limit=5)
                if oo_results:
                    self.logger.info(f"Found {len(oo_results)} OpenOwnership results")
                    for result in oo_results:
                        await self._process_openownership_result(builder, result)
            except Exception as oo_err:
                self.logger.warning(f"Optional OpenOwnership source failed: {oo_err}. Continuing.")
            
            # Return graph even if partial
            if builder.get_node_count() > 0:
                self.logger.info(
                    f"Built ownership graph with {builder.get_node_count()} entities "
                    f"and {builder.get_edge_count()} relationships"
                )
                return builder
            else:
                self.logger.warning("No real data found, falling back to mock data")
                return create_mock_ownership_graph()
                
        except Exception as e:
            self.logger.error(f"Error building graph from real data: {e}, using mock data")
            return create_mock_ownership_graph()
    
    async def _process_companies_house_result(
        self,
        builder: OwnershipGraphBuilder,
        company_result: Dict[str, Any]
    ) -> None:
        """Process Companies House API result and add to graph."""
        try:
            company_number = company_result.get("company_number")
            company_name = company_result.get("name")
            
            # Add company as entity
            company_entity = OwnershipEntity(
                entity_id=f"ch_{company_number}",
                name=company_name,
                type=EntityType.company,
                jurisdiction="GB",
                registration_number=company_number,
                description=f"Status: {company_result.get('status')}",
                source_system="Companies House",
                source_reference=f"Company Number: {company_number}"
            )
            builder.add_entity(company_entity)
            
            # Get officers/directors
            officers = await companies_house.get_officers(company_number)
            for officer in officers:
                officer_id = f"ch_officer_{company_number}_{officer['name'].replace(' ', '_')}"
                officer_entity = OwnershipEntity(
                    entity_id=officer_id,
                    name=officer["name"],
                    type=EntityType.person,
                    jurisdiction=officer.get("nationality"),
                    description=f"Role: {officer.get('role')}",
                    source_system="Companies House",
                    source_reference=f"Officer role in {company_number}"
                )
                builder.add_entity(officer_entity)
                
                # Add relationship
                link = OwnershipLink(
                    from_entity_id=officer_id,
                    to_entity_id=f"ch_{company_number}",
                    ownership_percentage=0.0,  # Directorships have 0.0% default
                    link_type="directorship",
                    source="companies_house",
                    source_system="Companies House",
                    source_reference=f"Officer role in {company_number}"
                )
                builder.add_ownership_link(link)
                
                # Evidence generation for Companies House directorship
                detail = f"{officer['name']} appointed as {officer.get('role', 'officer')} of {company_name} (via Companies House)"
                builder.add_evidence(
                    EvidenceItem(
                        source="Companies House",
                        type="ownership_relationship",
                        detail=detail,
                        date=parse_date(officer.get("appointed_on")),
                        confidence=0.90
                    )
                )
            
            # Get PSCs (Persons of Significant Control)
            pscs = await companies_house.get_persons_of_significant_control(company_number)
            for psc in pscs:
                if psc["is_active"]:
                    psc_id = f"ch_psc_{company_number}_{psc['name'].replace(' ', '_')}"
                    psc_type = EntityType.person if "individual" in psc["type"] else EntityType.company
                    
                    psc_entity = OwnershipEntity(
                        entity_id=psc_id,
                        name=psc["name"],
                        type=psc_type,
                        description=f"PSC Type: {psc['type']}",
                        source_system="Companies House",
                        source_reference=f"PSC of {company_number}"
                    )
                    builder.add_entity(psc_entity)
                    
                    pct = psc.get("ownership_percentage") or 0.0
                    
                    # Add relationship
                    link = OwnershipLink(
                        from_entity_id=psc_id,
                        to_entity_id=f"ch_{company_number}",
                        ownership_percentage=pct,
                        link_type="ownership",
                        source="companies_house",
                        source_system="Companies House",
                        source_reference=f"PSC of {company_number}"
                    )
                    builder.add_ownership_link(link)
                    
                    # Evidence generation for Companies House PSC ownership
                    detail = f"{psc['name']} has significant control ({pct:.1f}% ownership) over {company_name} (via Companies House)"
                    builder.add_evidence(
                        EvidenceItem(
                            source="Companies House",
                            type="ownership_relationship",
                            detail=detail,
                            date=parse_date(psc.get("notified_on")),
                            confidence=0.95
                        )
                    )
                    
        except Exception as e:
            self.logger.debug(f"Error processing Companies House result: {e}")
    
    async def _process_edgar_result(
        self,
        builder: OwnershipGraphBuilder,
        company_result: Dict[str, Any]
    ) -> None:
        """Process SEC EDGAR API result and add to graph."""
        try:
            cik = company_result.get("cik")
            company_name = company_result.get("name")
            self.logger.info(f"Searching SEC EDGAR for: {company_name}")
            self.logger.info(f"Resolved CIK: {cik}")
            
            # Add company as entity
            company_entity = OwnershipEntity(
                entity_id=f"edgar_{cik}",
                name=company_name,
                type=EntityType.company,
                jurisdiction="US",
                registration_number=cik,
                source_system="SEC EDGAR",
                source_reference=f"CIK: {cik}"
            )
            builder.add_entity(company_entity)
            
            from collections import defaultdict
            
            # Helper to process a list of owners with group consolidation
            def process_owner_list(owners_list: List[Dict[str, Any]], filing_label: str):
                # Group owners by accession number
                filing_groups = defaultdict(list)
                for owner in owners_list:
                    acc_num = owner.get("accession_number")
                    filing_groups[acc_num].append(owner)
                
                for acc_num, group in filing_groups.items():
                    if not group:
                        continue
                    
                    # Filter to >= 5.0% ownership (already done in sec_edgar, but keep for safety)
                    filtered_group = [o for o in group if (o.get("ownership_percentage") or 0.0) >= 5.0]
                    if not filtered_group:
                        continue
                        
                    # Find maximum ownership percentage in this filing
                    max_pct = max(o.get("ownership_percentage") or 0.0 for o in filtered_group)
                    
                    # Find candidates with max_pct (allowing small floating point difference)
                    max_owners = [o for o in filtered_group if abs((o.get("ownership_percentage") or 0.0) - max_pct) < 0.01]
                    
                    persons = [o for o in max_owners if o.get("type") == "person"]
                    entities = [o for o in max_owners if o.get("type") == "entity"]
                    
                    consolidated = False
                    p_name_to_skip = None
                    c_name_to_skip = None
                    
                    if len(persons) == 1 and len(entities) == 1:
                        p_owner = persons[0]
                        c_owner = entities[0]
                        
                        p_name = p_owner.get("name", "Unknown")
                        c_name = c_owner.get("name", "Unknown")
                        
                        p_id = f"edgar_{cik}_{p_name.replace(' ', '_')}"
                        c_id = f"edgar_{cik}_{c_name.replace(' ', '_')}"
                        
                        p_name_to_skip = p_name
                        c_name_to_skip = c_name
                        
                        # Add Person node
                        p_entity = OwnershipEntity(
                            entity_id=p_id,
                            name=p_name,
                            type=EntityType.person,
                            description=f"Ultimate controller from Schedule {filing_label} filing",
                            source_system="SEC EDGAR",
                            source_reference=f"Filing: {acc_num}"
                        )
                        builder.add_entity(p_entity)
                        
                        # Add Company/Entity node
                        c_entity = OwnershipEntity(
                            entity_id=c_id,
                            name=c_name,
                            type=EntityType.company,
                            description=f"Parent entity from Schedule {filing_label} filing",
                            source_system="SEC EDGAR",
                            source_reference=f"Filing: {acc_num}"
                        )
                        builder.add_entity(c_entity)
                        
                        # Link Person -> Company (100.0% control link)
                        control_link = OwnershipLink(
                            from_entity_id=p_id,
                            to_entity_id=c_id,
                            ownership_percentage=100.0,
                            link_type="control",
                            source="sec_edgar",
                            date_recorded=p_owner.get("filing_date"),
                            source_system="SEC EDGAR",
                            source_reference=f"Filing: {acc_num}"
                        )
                        builder.add_ownership_link(control_link)
                        
                        # Link Company -> Target (max_pct ownership link)
                        target_link = OwnershipLink(
                            from_entity_id=c_id,
                            to_entity_id=f"edgar_{cik}",
                            ownership_percentage=max_pct,
                            link_type="ownership",
                            source="sec_edgar",
                            date_recorded=c_owner.get("filing_date"),
                            source_system="SEC EDGAR",
                            source_reference=f"Filing: {acc_num}"
                        )
                        builder.add_ownership_link(target_link)
                        
                        # Evidence for consolidation
                        detail = f"{p_name} controls {c_name}, which reported {max_pct:.1f}% beneficial ownership of {company_name} in Schedule {filing_label} filing"
                        builder.add_evidence(
                            EvidenceItem(
                                source="SEC EDGAR",
                                type="ownership_relationship",
                                detail=detail,
                                url=c_owner.get("source_url"),
                                date=parse_date(c_owner.get("filing_date")),
                                confidence=0.95
                            )
                        )
                        
                        consolidated = True
                        
                    # Process remaining/all entities in this filing
                    for owner in filtered_group:
                        owner_name = owner.get("name", "Unknown")
                        owner_id = f"edgar_{cik}_{owner_name.replace(' ', '_')}"
                        
                        # If consolidated, we already linked the person to the company, and company to target.
                        # Skip them from direct target ownership.
                        if consolidated and owner_name in (p_name_to_skip, c_name_to_skip):
                            continue
                            
                        # Add node
                        owner_entity = OwnershipEntity(
                            entity_id=owner_id,
                            name=owner_name,
                            type=EntityType.person if owner.get("type") == "person" else EntityType.company,
                            description=f"Beneficial owner from Schedule {filing_label} filing",
                            source_system="SEC EDGAR",
                            source_reference=f"Filing: {acc_num}"
                        )
                        builder.add_entity(owner_entity)
                        
                        # Link to Target
                        pct = owner.get("ownership_percentage") or 0.0
                        link = OwnershipLink(
                            from_entity_id=owner_id,
                            to_entity_id=f"edgar_{cik}",
                            ownership_percentage=pct,
                            link_type="ownership",
                            source="sec_edgar",
                            date_recorded=owner.get("filing_date"),
                            source_system="SEC EDGAR",
                            source_reference=f"Filing: {acc_num}"
                        )
                        builder.add_ownership_link(link)
                        
                        # Evidence
                        detail = f"{owner_name} reported {pct:.1f}% beneficial ownership of {company_name} in Schedule {filing_label} filing"
                        builder.add_evidence(
                            EvidenceItem(
                                source="SEC EDGAR",
                                type="ownership_relationship",
                                detail=detail,
                                url=owner.get("source_url"),
                                date=parse_date(owner.get("filing_date")),
                                confidence=0.95
                            )
                        )
            
            # Get beneficial owners from 13D filings
            owners_13d = await sec_edgar.get_beneficial_owners_13d(cik)
            process_owner_list(owners_13d, "13D")
                
            # Get beneficial owners from 13G filings
            owners_13g = await sec_edgar.get_beneficial_owners_13g(cik)
            process_owner_list(owners_13g, "13G")
                    
        except Exception as e:
            self.logger.debug(f"Error processing EDGAR result: {e}")

    
    async def _process_openownership_result(
        self,
        builder: OwnershipGraphBuilder,
        company_result: Dict[str, Any]
    ) -> None:
        """Process OpenOwnership API result and add to graph."""
        try:
            company_id = company_result.get("id")
            company_name = company_result.get("name")
            country = company_result.get("country")
            
            # Add company as entity
            company_entity = OwnershipEntity(
                entity_id=f"oo_{company_id}",
                name=company_name,
                type=EntityType.company,
                jurisdiction=country,
                registration_number=company_id,
                source_system="OpenOwnership",
                source_reference=f"ID: {company_id}"
            )
            builder.add_entity(company_entity)
            
            # Get beneficial owners
            owners = await openownership.get_beneficial_owners(company_id)
            for owner in owners:
                owner_id = f"oo_{owner.get('id', 'unknown')}"
                owner_type = EntityType.person if owner.get("type") == "person" else EntityType.company
                
                owner_entity = OwnershipEntity(
                    entity_id=owner_id,
                    name=owner.get("name", "Unknown"),
                    type=owner_type,
                    description=f"OpenOwnership type: {owner.get('type')}",
                    source_system="OpenOwnership",
                    source_reference=f"ID: {owner.get('id')}"
                )
                builder.add_entity(owner_entity)
                
                pct = owner.get("ownership_percentage") or 0.0
                link = OwnershipLink(
                    from_entity_id=owner_id,
                    to_entity_id=f"oo_{company_id}",
                    ownership_percentage=pct,
                    link_type="ownership",
                    source="openownership",
                    source_system="OpenOwnership",
                    source_reference=f"Filer: {owner.get('name')}"
                )
                builder.add_ownership_link(link)
                
                # Evidence generation for OpenOwnership relationship
                detail = f"{owner.get('name', 'Unknown')} owns {pct:.1f}% of {company_name} (via OpenOwnership)"
                builder.add_evidence(
                    EvidenceItem(
                        source="OpenOwnership",
                        type="ownership_relationship",
                        detail=detail,
                        confidence=0.75
                    )
                )
                    
        except Exception as e:
            self.logger.debug(f"Error processing OpenOwnership result: {e}")
    
    def _find_target_entity_id(
        self,
        builder: OwnershipGraphBuilder,
        fingerprint: EntityFingerprint
    ) -> str:
        """
        Find target entity ID in graph based on fingerprint.
        
        Args:
            builder: OwnershipGraphBuilder
            fingerprint: Entity fingerprint to match
            
        Returns:
            Entity ID of the target, or first company entity as fallback
        """
        # 1. Search by target ID format with exactly one underscore first
        for entity_id in builder.get_all_entities():
            if entity_id.count('_') == 1 and (entity_id.startswith("edgar_") or entity_id.startswith("ch_") or entity_id.startswith("oo_")):
                return entity_id

        # 2. Search by exact name match
        for entity_id, entity in builder.get_all_entities().items():
            if entity.name.lower() == fingerprint.canonical_name.lower():
                return entity_id
                
        # Fallback 1: Return first company entity as the target
        for entity_id, entity in builder.get_all_entities().items():
            if entity.type == EntityType.company:
                return entity_id
        
        # Fallback 2: Return first entity
        entities = builder.get_all_entities()
        if entities:
            return next(iter(entities.keys()))
        
        return "unknown"
    
    def _build_response(
        self,
        builder: OwnershipGraphBuilder,
        graph_json: Dict[str, Any],
        ubo_result: UBODetectionResult,
        risk_profile: OwnershipRiskProfile,
        fingerprint: EntityFingerprint
    ) -> OwnershipUnwindResponse:
        """
        Build comprehensive response object.
        
        Args:
            builder: Graph builder
            graph_json: Serialized graph
            ubo_result: UBO detection results
            risk_profile: Risk assessment
            fingerprint: Original entity fingerprint
            
        Returns:
            OwnershipUnwindResponse
        """
        # Convert UBO entities to response format
        ubos = [
            UBODetail(
                entity_id=u.entity_id,
                entity_name=u.entity_name,
                entity_type=u.entity_type.value,
                effective_ownership_percentage=u.effective_ownership_percentage,
                depth_from_target=u.depth_from_target,
                is_natural_person=u.is_natural_person,
                confidence_score=u.confidence_score,
                source_system=builder.get_graph().nodes.get(u.entity_id, {}).get("source_system"),
                source_reference=builder.get_graph().nodes.get(u.entity_id, {}).get("source_reference")
            )
            for u in ubo_result.ubos
        ]
        
        # Circular ownership details
        circular_detail = CircularOwnershipDetail(
            detected=ubo_result.has_circular_ownership,
            entity_count=len(ubo_result.circular_entities),
            entity_ids=ubo_result.circular_entities
        )
        
        return OwnershipUnwindResponse(
            ownership_graph=graph_json,
            ultimate_beneficial_owners=ubos,
            circular_ownership_detected=circular_detail,
            max_chain_depth=ubo_result.max_chain_depth,
            complexity_level=ubo_result.complexity_level,
            ownership_risk_score=risk_profile.overall_risk_score,
            risk_level=risk_profile.risk_level,
            key_concerns=risk_profile.key_concerns,
            entities_count=builder.get_node_count(),
            relationships_count=builder.get_edge_count(),
            evidence=self._build_evidence_dicts(ubo_result, risk_profile)
        )
    
    def _build_evidence(
        self,
        builder: OwnershipGraphBuilder,
        ubo_result: UBODetectionResult,
        risk_profile: OwnershipRiskProfile
    ) -> List[EvidenceItem]:
        """
        Build evidence items for the response, incorporating discovered relationships.
        
        Args:
            builder: Graph builder
            ubo_result: UBO detection results
            risk_profile: Risk assessment
            
        Returns:
            List of EvidenceItem objects
        """
        # Start with discovered relationships evidence from builder
        evidence_items = list(builder.evidence)
        
        # Evidence of UBO detection
        for ubo in ubo_result.ubos:
            evidence_items.append(EvidenceItem(
                source="ownership_unwind_agent",
                type="ubo_identification",
                detail=f"Identified {ubo.entity_name} as Ultimate Beneficial Owner "
                      f"with {ubo.effective_ownership_percentage:.1f}% ownership",
                confidence=ubo.confidence_score
            ))
        
        # Evidence of circular ownership
        if ubo_result.has_circular_ownership:
            evidence_items.append(EvidenceItem(
                source="ownership_unwind_agent",
                type="circular_ownership",
                detail=f"Circular ownership detected involving {len(ubo_result.circular_entities)} entities",
                confidence=1.0
            ))
        
        # Evidence of risk factors
        for risk_factor in risk_profile.risk_factors:
            evidence_items.append(EvidenceItem(
                source="ownership_unwind_agent",
                type="risk_factor",
                detail=f"{risk_factor.factor.value.upper()}: {risk_factor.description}",
                confidence=risk_factor.score
            ))
        
        return evidence_items
    
    def _build_evidence_dicts(
        self,
        ubo_result: UBODetectionResult,
        risk_profile: OwnershipRiskProfile
    ) -> List[Dict[str, Any]]:
        """
        Build evidence as dictionaries (for response data field).
        
        Returns:
            List of evidence dictionaries
        """
        evidence = []
        
        # UBO evidence
        for ubo in ubo_result.ubos:
            evidence.append({
                "type": "ubo_identification",
                "entity_name": ubo.entity_name,
                "ownership_percentage": ubo.effective_ownership_percentage,
                "confidence": ubo.confidence_score,
                "paths": len(ubo.ownership_paths)
            })
        
        # Complexity evidence
        evidence.append({
            "type": "complexity_assessment",
            "complexity_level": ubo_result.complexity_level,
            "max_chain_depth": ubo_result.max_chain_depth,
            "circular_ownership": ubo_result.has_circular_ownership
        })
        
        # Risk evidence
        evidence.append({
            "type": "risk_assessment",
            "overall_risk_score": risk_profile.overall_risk_score,
            "risk_level": risk_profile.risk_level,
            "risk_factor_count": len(risk_profile.risk_factors)
        })
        
        return evidence


# ──────────────────────────────────────────────────────────────────────────────
# Standalone Service (for non-agent usage)
# ──────────────────────────────────────────────────────────────────────────────

class OwnershipAnalysisService:
    """
    Standalone service for ownership analysis (non-BaseAgent usage).
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def analyze(self, entity_id: str) -> OwnershipUnwindResponse:
        """
        Analyze ownership structure for an entity using mock data (Phase 1 legacy compatibility).
        
        Args:
            entity_id: Target entity ID to analyze
            
        Returns:
            Complete ownership analysis
        """
        start_time = time.time()
        
        # Build graph
        builder = create_mock_ownership_graph()
        graph = builder.get_graph()
        
        # Detect UBOs
        detector = UBODetector(graph, confidence_threshold=0.5)
        ubo_result = detector.detect(entity_id)
        
        # Calculate risk
        risk_calc = OwnershipRiskCalculator(graph, ubo_result)
        risk_profile = risk_calc.calculate()
        
        # Serialize
        serializer = OwnershipGraphSerializer(graph)
        graph_json = serializer.to_dict()
        
        # Build response
        ubos = [
            UBODetail(
                entity_id=u.entity_id,
                entity_name=u.entity_name,
                entity_type=u.entity_type.value,
                effective_ownership_percentage=u.effective_ownership_percentage,
                depth_from_target=u.depth_from_target,
                is_natural_person=u.is_natural_person,
                confidence_score=u.confidence_score,
                source_system=graph.nodes.get(u.entity_id, {}).get("source_system"),
                source_reference=graph.nodes.get(u.entity_id, {}).get("source_reference")
            )
            for u in ubo_result.ubos
        ]
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        self.logger.info(f"Ownership analysis completed in {elapsed_ms}ms")
        
        return OwnershipUnwindResponse(
            ownership_graph=graph_json,
            ultimate_beneficial_owners=ubos,
            circular_ownership_detected=CircularOwnershipDetail(
                detected=ubo_result.has_circular_ownership,
                entity_count=len(ubo_result.circular_entities),
                entity_ids=ubo_result.circular_entities
            ),
            max_chain_depth=ubo_result.max_chain_depth,
            complexity_level=ubo_result.complexity_level,
            ownership_risk_score=risk_profile.overall_risk_score,
            risk_level=risk_profile.risk_level,
            key_concerns=risk_profile.key_concerns,
            entities_count=builder.get_node_count(),
            relationships_count=builder.get_edge_count(),
            evidence=[]
        )

    async def analyze_with_real_data(
        self,
        entity_name: str,
        sources: Optional[List[str]] = None
    ) -> OwnershipUnwindResponse:
        """
        Analyze ownership structure for a company name using real data sources.
        
        Args:
            entity_name: Target company name
            sources: Optional list of sources (default all)
            
        Returns:
            Complete ownership analysis response
        """
        start_time = time.time()
        
        # Build graph using real data sources via the agent implementation
        agent = OwnershipUnwindAgent()
        builder = await agent._build_ownership_graph(use_real_data=True, entity_name=entity_name)
        graph = builder.get_graph()
        
        # Detect target node id
        target_id = "unknown"
        # 1. Search by target ID format with exactly one underscore first
        for entity_id in builder.get_all_entities():
            if entity_id.count('_') == 1 and (entity_id.startswith("edgar_") or entity_id.startswith("ch_") or entity_id.startswith("oo_")):
                target_id = entity_id
                break

        if target_id == "unknown":
            for entity_id, entity in builder.get_all_entities().items():
                if entity.name.lower() == entity_name.lower():
                    target_id = entity_id
                    break
                    
        if target_id == "unknown":
            for entity_id, entity in builder.get_all_entities().items():
                if entity.type == EntityType.company:
                    target_id = entity_id
                    break
        if target_id == "unknown" and builder.get_all_entities():
            target_id = next(iter(builder.get_all_entities().keys()))
            
        # Detect UBOs
        detector = UBODetector(graph, confidence_threshold=0.5)
        ubo_result = detector.detect(target_id)
        
        # Calculate risk
        risk_calc = OwnershipRiskCalculator(graph, ubo_result)
        risk_profile = risk_calc.calculate()
        
        # Serialize
        serializer = OwnershipGraphSerializer(graph)
        graph_json = serializer.to_dict()
        
        # Build response
        ubos = [
            UBODetail(
                entity_id=u.entity_id,
                entity_name=u.entity_name,
                entity_type=u.entity_type.value,
                effective_ownership_percentage=u.effective_ownership_percentage,
                depth_from_target=u.depth_from_target,
                is_natural_person=u.is_natural_person,
                confidence_score=u.confidence_score,
                source_system=graph.nodes.get(u.entity_id, {}).get("source_system"),
                source_reference=graph.nodes.get(u.entity_id, {}).get("source_reference")
            )
            for u in ubo_result.ubos
        ]
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        self.logger.info(f"Real-data ownership analysis completed in {elapsed_ms}ms")
        
        return OwnershipUnwindResponse(
            ownership_graph=graph_json,
            ultimate_beneficial_owners=ubos,
            circular_ownership_detected=CircularOwnershipDetail(
                detected=ubo_result.has_circular_ownership,
                entity_count=len(ubo_result.circular_entities),
                entity_ids=ubo_result.circular_entities
            ),
            max_chain_depth=ubo_result.max_chain_depth,
            complexity_level=ubo_result.complexity_level,
            ownership_risk_score=risk_profile.overall_risk_score,
            risk_level=risk_profile.risk_level,
            key_concerns=risk_profile.key_concerns,
            entities_count=builder.get_node_count(),
            relationships_count=builder.get_edge_count(),
            evidence=[e.model_dump() for e in builder.evidence]
        )
