"""
Risk Calculation Module

Calculates ownership risk scores based on graph structure, UBO characteristics,
and complexity factors.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
import networkx as nx
from shared.logger import get_logger
from .ubo_detector import UBODetectionResult

logger = get_logger(__name__)


class RiskFactor(str, Enum):
    """Risk factors in ownership structures."""
    circular_ownership = "circular_ownership"
    deep_chain = "deep_chain"
    multiple_ubos = "multiple_ubos"
    partial_ownership = "partial_ownership"
    unknown_entity = "unknown_entity"
    corporate_veil = "corporate_veil"
    jurisdiction_risk = "jurisdiction_risk"
    nominee_structure = "nominee_structure"


class RiskFactorDetail(BaseModel):
    """Individual risk factor with scoring."""
    factor: RiskFactor
    severity: str  # low, medium, high, critical
    score: float = Field(ge=0.0, le=1.0)
    description: str
    affected_entities: List[str] = Field(default_factory=list)


class OwnershipRiskProfile(BaseModel):
    """Complete risk assessment for ownership structure."""
    entity_id: str
    entity_name: str
    overall_risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Weighted average risk")
    risk_level: str = Field(default="low", description="low|medium|high|critical")
    risk_factors: List[RiskFactorDetail] = []
    key_concerns: List[str] = []
    mitigation_suggestions: List[str] = []
    
    class Config:
        use_enum_values = False


class OwnershipRiskCalculator:
    """
    Calculates comprehensive risk scores for ownership structures.
    
    Risk factors:
    1. Circular ownership (cycles) - high risk
    2. Chain depth - moderate risk
    3. Multiple UBOs with unclear primary - moderate risk
    4. Partial ownership - low-moderate risk
    5. Unknown entity types - moderate risk
    6. Corporate veil (many intermediaries) - moderate risk
    """
    
    # Risk weights for factors
    WEIGHTS = {
        "circular_ownership": 0.30,
        "deep_chain": 0.15,
        "multiple_ubos": 0.15,
        "partial_ownership": 0.10,
        "unknown_entity": 0.10,
        "corporate_veil": 0.15,
        "jurisdiction_risk": 0.05,
        "nominee_structure": 0.10,
    }
    
    # High-risk jurisdictions (for future enhancement)
    HIGH_RISK_JURISDICTIONS = {
        "VI", "BVI",  # Virgin Islands
        "KY",  # Cayman Islands
        "PA",  # Panama
        "AG",  # Antigua & Barbuda
        "BS",  # Bahamas
        "MU",  # Mauritius
        "SC",  # Seychelles
    }
    
    def __init__(self, graph: nx.DiGraph, ubo_result: UBODetectionResult):
        """
        Initialize risk calculator.
        
        Args:
            graph: NetworkX DiGraph of ownership relationships
            ubo_result: UBODetectionResult from UBO detector
        """
        self.graph = graph
        self.ubo_result = ubo_result
        self.logger = get_logger(self.__class__.__name__)
    
    def calculate(self) -> OwnershipRiskProfile:
        """
        Calculate comprehensive ownership risk profile.
        
        Returns:
            OwnershipRiskProfile with detailed risk assessment
        """
        risk_profile = OwnershipRiskProfile(
            entity_id=self.ubo_result.target_entity_id,
            entity_name=self.ubo_result.target_entity_name
        )
        
        # Evaluate each risk factor
        risk_factors = []
        scores_by_weight = {}
        
        # 1. Circular ownership
        circular_factor = self._assess_circular_ownership()
        if circular_factor:
            risk_factors.append(circular_factor)
            scores_by_weight[circular_factor.factor.value] = circular_factor.score
        
        # 2. Chain depth
        depth_factor = self._assess_chain_depth()
        if depth_factor:
            risk_factors.append(depth_factor)
            scores_by_weight[depth_factor.factor.value] = depth_factor.score
        
        # 3. Multiple UBOs
        ubo_factor = self._assess_ubo_concentration()
        if ubo_factor:
            risk_factors.append(ubo_factor)
            scores_by_weight[ubo_factor.factor.value] = ubo_factor.score
        
        # 4. Partial ownership
        partial_factor = self._assess_partial_ownership()
        if partial_factor:
            risk_factors.append(partial_factor)
            scores_by_weight[partial_factor.factor.value] = partial_factor.score
        
        # 5. Unknown entities
        unknown_factor = self._assess_unknown_entities()
        if unknown_factor:
            risk_factors.append(unknown_factor)
            scores_by_weight[unknown_factor.factor.value] = unknown_factor.score
        
        # 6. Corporate veil (chain complexity)
        veil_factor = self._assess_corporate_veil()
        if veil_factor:
            risk_factors.append(veil_factor)
            scores_by_weight[veil_factor.factor.value] = veil_factor.score
        
        # 7. Jurisdiction risk
        jurisdiction_factor = self._assess_jurisdiction_risk()
        if jurisdiction_factor:
            risk_factors.append(jurisdiction_factor)
            scores_by_weight[jurisdiction_factor.factor.value] = jurisdiction_factor.score
        
        # 8. Nominee structures
        nominee_factor = self._assess_nominee_structures()
        if nominee_factor:
            risk_factors.append(nominee_factor)
            scores_by_weight[nominee_factor.factor.value] = nominee_factor.score
        
        risk_profile.risk_factors = risk_factors
        
        # Calculate weighted overall score
        overall_score = self._calculate_weighted_score(scores_by_weight)
        risk_profile.overall_risk_score = overall_score
        risk_profile.risk_level = self._determine_risk_level(overall_score)
        
        # Generate concerns and suggestions
        risk_profile.key_concerns = self._generate_concerns(risk_factors)
        risk_profile.mitigation_suggestions = self._generate_suggestions(risk_factors)
        
        self.logger.info(
            f"Risk assessment for {self.ubo_result.target_entity_name}: "
            f"score={overall_score:.2f}, level={risk_profile.risk_level}"
        )
        
        return risk_profile
    
    def _assess_circular_ownership(self) -> Optional[RiskFactorDetail]:
        """Assess risk from circular/cyclical ownership."""
        if not self.ubo_result.has_circular_ownership:
            return None
        
        affected_count = len(self.ubo_result.circular_entities)
        
        return RiskFactorDetail(
            factor=RiskFactor.circular_ownership,
            severity="critical",
            score=0.95,  # Very high risk
            description=f"Circular ownership detected involving {affected_count} entities. "
                       f"Creates complexity and potential regulatory violations.",
            affected_entities=self.ubo_result.circular_entities
        )
    
    def _assess_chain_depth(self) -> Optional[RiskFactorDetail]:
        """Assess risk from deep ownership chains."""
        depth = self.ubo_result.max_chain_depth
        
        if depth <= 1:
            return None  # Direct ownership is low risk
        
        if depth <= 2:
            severity = "low"
            score = 0.25
            description = "Moderate ownership chain depth (2 levels)"
        elif depth <= 3:
            severity = "medium"
            score = 0.45
            description = f"Deep ownership chain ({depth} levels) may obscure UBO"
        elif depth <= 4:
            severity = "high"
            score = 0.65
            description = f"Very deep ownership chain ({depth} levels) creates significant UBO obscurity"
        else:
            severity = "critical"
            score = 0.85
            description = f"Extremely deep chain ({depth} levels) - likely intentional obscuration"
        
        return RiskFactorDetail(
            factor=RiskFactor.deep_chain,
            severity=severity,
            score=score,
            description=description
        )
    
    def _assess_ubo_concentration(self) -> Optional[RiskFactorDetail]:
        """Assess risk from unclear or multiple UBO situations."""
        ubo_count = len(self.ubo_result.ubos)
        
        if ubo_count == 0:
            return RiskFactorDetail(
                factor=RiskFactor.multiple_ubos,
                severity="high",
                score=0.70,
                description="No clear UBO identified - unable to establish beneficial ownership"
            )
        elif ubo_count == 1:
            return None  # Single clear UBO is optimal
        else:
            # Multiple UBOs - assess concentration
            ownership_percentages = [u.effective_ownership_percentage for u in self.ubo_result.ubos]
            max_ownership = max(ownership_percentages)
            
            if max_ownership >= 80:
                severity = "low"
                score = 0.15
                description = f"Multiple UBOs but {max_ownership:.1f}% owned by primary"
            elif max_ownership >= 50:
                severity = "medium"
                score = 0.40
                description = f"Multiple UBOs with no clear primary (largest: {max_ownership:.1f}%)"
            else:
                severity = "high"
                score = 0.65
                description = f"Fragmented ownership among {ubo_count} UBOs - unclear control"
            
            return RiskFactorDetail(
                factor=RiskFactor.multiple_ubos,
                severity=severity,
                score=score,
                description=description,
                affected_entities=[u.entity_id for u in self.ubo_result.ubos]
            )
    
    def _assess_partial_ownership(self) -> Optional[RiskFactorDetail]:
        """Assess risk from less-than-100% ownership."""
        has_partial = any(
            u.effective_ownership_percentage < 100
            for u in self.ubo_result.ubos
        )
        
        if not has_partial:
            return None
        
        avg_ownership = sum(u.effective_ownership_percentage for u in self.ubo_result.ubos) / len(self.ubo_result.ubos) if self.ubo_result.ubos else 0
        
        return RiskFactorDetail(
            factor=RiskFactor.partial_ownership,
            severity="medium",
            score=0.40,
            description=f"Partial ownership structure (avg: {avg_ownership:.1f}%) - "
                       f"indicates shared control or incomplete beneficiary disclosure"
        )
    
    def _assess_unknown_entities(self) -> Optional[RiskFactorDetail]:
        """Assess risk from unknown or poorly documented entities."""
        unknown_count = 0
        affected_entities = []
        
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            node_type = node_data.get("type", "unknown")
            node_name = node_data.get("name", "Unknown")
            
            if node_type == "unknown" or not node_name:
                unknown_count += 1
                affected_entities.append(node_id)
        
        if unknown_count == 0:
            return None
        
        score = min(unknown_count * 0.15, 0.60)
        severity = "high" if unknown_count > 2 else "medium"
        
        return RiskFactorDetail(
            factor=RiskFactor.unknown_entity,
            severity=severity,
            score=score,
            description=f"{unknown_count} entities with unknown type or missing information",
            affected_entities=affected_entities
        )
    
    def _assess_corporate_veil(self) -> Optional[RiskFactorDetail]:
        """Assess risk from many intermediary entities."""
        total_nodes = self.graph.number_of_nodes()
        avg_depth = self.ubo_result.max_chain_depth
        
        # Ratio of intermediaries to actual depth
        # Higher intermediaries per depth level suggests deliberate obscuration
        if total_nodes > 0 and avg_depth > 0:
            intermediary_ratio = total_nodes / avg_depth
            
            if intermediary_ratio < 2:
                return None
            
            if intermediary_ratio < 3:
                severity = "low"
                score = 0.20
            elif intermediary_ratio < 5:
                severity = "medium"
                score = 0.40
                description = f"Complex corporate structure ({total_nodes} entities, {avg_depth} depth levels)"
            else:
                severity = "high"
                score = 0.60
                description = f"Heavy corporate veil ({total_nodes} entities for {avg_depth} depth levels) - " \
                            f"suggests deliberate UBO obscuration"
                return RiskFactorDetail(
                    factor=RiskFactor.corporate_veil,
                    severity=severity,
                    score=score,
                    description=description
                )
        
        return None
    
    def _assess_jurisdiction_risk(self) -> Optional[RiskFactorDetail]:
        """
        Assess risk based on entity jurisdictions.
        
        Flags high-risk jurisdictions known for lack of transparency and beneficial ownership disclosure:
        - British Virgin Islands (BVI)
        - Cayman Islands (KY)
        - Panama (PA)
        - Seychelles (SC)
        - Marshall Islands (MH)
        - Cook Islands (CK)
        
        These are commonly used for opacity structures.
        """
        opacity_entities = []
        opacity_jurisdictions = set()
        
        # Opacity jurisdiction codes (ISO 3166-1 alpha-2 and custom codes)
        OPACITY_JURISDICTIONS = {
            "VI",  # US Virgin Islands
            "VG",  # British Virgin Islands
            "KY",  # Cayman Islands
            "PA",  # Panama
            "SC",  # Seychelles
            "MH",  # Marshall Islands
            "CK",  # Cook Islands
            "BM",  # Bermuda
            "KN",  # Saint Kitts and Nevis
            "AG",  # Antigua and Barbuda
            "BS",  # Bahamas
            "BZ",  # Belize
            "MU",  # Mauritius
            "AE",  # UAE (Dubai)
            "SG",  # Singapore
            "HK",  # Hong Kong
        }

        # Substrings to search for in case full names are provided
        OPACITY_NAMES = {
            "BRITISH VIRGIN ISLANDS", "BVI", "VIRGIN ISLANDS, BRITISH",
            "CAYMAN ISLANDS", "CAYMAN",
            "PANAMA",
            "SEYCHELLES",
            "MARSHALL ISLANDS", "MARSHALL",
            "COOK ISLANDS",
            "BERMUDA",
            "SAINT KITTS AND NEVIS", "ST KITTS",
            "ANTIGUA AND BARBUDA", "ANTIGUA",
            "BAHAMAS",
            "BELIZE",
            "MAURITIUS",
            "UNITED ARAB EMIRATES", "UAE", "DUBAI",
            "SINGAPORE",
            "HONG KONG",
        }
        
        # Check each entity for opacity jurisdictions
        for node_id in self.graph.nodes():
            jurisdiction = self.graph.nodes[node_id].get("jurisdiction", "")
            if not jurisdiction:
                continue
                
            jurisdiction_upper = str(jurisdiction).upper().strip()
            
            # Support both 2-letter codes and full country names
            is_opacity = (
                jurisdiction_upper in OPACITY_JURISDICTIONS or 
                jurisdiction_upper in self.HIGH_RISK_JURISDICTIONS or
                any(name in jurisdiction_upper for name in OPACITY_NAMES)
            )
            
            if is_opacity:
                opacity_entities.append(node_id)
                opacity_jurisdictions.add(jurisdiction_upper)
        
        if not opacity_entities:
            return None
        
        # Score based on number and prominence of opacity jurisdictions
        entity_count = len(opacity_entities)
        jurisdiction_count = len(opacity_jurisdictions)
        
        # Higher risk if multiple opacity jurisdictions involved
        if jurisdiction_count >= 3:
            severity = "critical"
            score = 0.85
            description = f"Entities in {jurisdiction_count} opacity jurisdictions ({', '.join(sorted(opacity_jurisdictions))}) " \
                         f"- classic UBO obscuration pattern. Jurisdictions known for lack of beneficial ownership transparency."
        elif jurisdiction_count >= 2:
            severity = "high"
            score = 0.65
            description = f"Entities in {jurisdiction_count} opacity jurisdictions ({', '.join(sorted(opacity_jurisdictions))}) " \
                         f"- elevated risk of intentional UBO obscuration."
        elif entity_count >= 2:
            severity = "high"
            score = 0.50
            description = f"{entity_count} entities in opacity jurisdictions ({', '.join(sorted(opacity_jurisdictions))}) " \
                         f"- elevated transparency risk."
        else:
            severity = "medium"
            score = 0.30
            description = f"Entity in opacity jurisdiction ({', '.join(sorted(opacity_jurisdictions))}) " \
                         f"- limited beneficial ownership disclosure requirements."
        
        return RiskFactorDetail(
            factor=RiskFactor.jurisdiction_risk,
            severity=severity,
            score=score,
            description=description,
            affected_entities=opacity_entities
        )
    
    
    def _assess_nominee_structures(self) -> Optional[RiskFactorDetail]:
        """Assess risk from potential nominee structures."""
        # Nominee indicators: person owns multiple companies with no other relationships
        nominee_score = 0.0
        potential_nominees = []
        
        for person_node in [n for n in self.graph.nodes() 
                           if self.graph.nodes[n].get("type") == "person"]:
            successors = list(self.graph.successors(person_node))
            predecessors = list(self.graph.predecessors(person_node))
            
            # Nominee indicators:
            # - Person owns multiple companies
            # - Person has no predecessors (no one owns them)
            # - Companies are shell-like (no other relationships)
            if len(successors) >= 2 and len(predecessors) == 0:
                nominee_score = max(nominee_score, 0.30)
                potential_nominees.append(person_node)
        
        if nominee_score == 0:
            return None
        
        return RiskFactorDetail(
            factor=RiskFactor.nominee_structure,
            severity="medium",
            score=nominee_score,
            description=f"Potential nominee structure detected - individuals owning multiple entities",
            affected_entities=potential_nominees
        )
    
    def _calculate_weighted_score(self, scores_by_factor: Dict[str, float]) -> float:
        """
        Calculate weighted overall risk score.
        
        Args:
            scores_by_factor: Dict mapping factor name to score
            
        Returns:
            Weighted score (0.0-1.0)
        """
        if not scores_by_factor:
            return 0.0
        
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for factor_name, score in scores_by_factor.items():
            weight = self.WEIGHTS.get(factor_name, 0.0)
            weighted_sum += score * weight
            weight_sum += weight
        
        # Normalize by actual weights used
        if weight_sum > 0:
            return min(weighted_sum / weight_sum, 1.0)
        else:
            return 0.0
    
    def _determine_risk_level(self, score: float) -> str:
        """Convert numerical score to risk level."""
        if score < 0.25:
            return "low"
        elif score < 0.50:
            return "medium"
        elif score < 0.75:
            return "high"
        else:
            return "critical"
    
    def _generate_concerns(self, risk_factors: List[RiskFactorDetail]) -> List[str]:
        """Generate key concerns from risk factors."""
        concerns = []
        
        for factor in risk_factors:
            if factor.severity in ["high", "critical"]:
                concerns.append(f"??  {factor.factor.value.upper()}: {factor.description}")
        
        return concerns
    
    def _generate_suggestions(self, risk_factors: List[RiskFactorDetail]) -> List[str]:
        """Generate mitigation suggestions."""
        suggestions = []
        
        factor_types = {f.factor.value for f in risk_factors}
        
        if "circular_ownership" in factor_types:
            suggestions.append("Investigate circular ownership for regulatory violations")
            suggestions.append("Consider restructuring to clarify control and beneficial ownership")
        
        if "deep_chain" in factor_types:
            suggestions.append("Trace ownership to final beneficial owner before proceeding")
        
        if "multiple_ubos" in factor_types:
            suggestions.append("Clarify which entity has primary control and decision-making authority")
        
        if "corporate_veil" in factor_types:
            suggestions.append("Request detailed organizational charts and parent company documentation")
        
        if "jurisdiction_risk" in factor_types:
            suggestions.append("Conduct enhanced due diligence on offshore entities")
        
        if "nominee_structure" in factor_types:
            suggestions.append("Verify nominee status and identify true beneficial owner")
        
        return suggestions
