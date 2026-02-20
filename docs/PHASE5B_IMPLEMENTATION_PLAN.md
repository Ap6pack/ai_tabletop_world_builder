# Phase 5B: Enhanced Game Mechanics Polish - Implementation Plan

**Phase**: 5B - Game Mechanics Polish
**Goal**: Add business impact, time pressure, and resource constraints to create realistic, high-stakes training scenarios
**Estimated Time**: 2-3 weeks
**Dependencies**: Phase 5A (Objectives, System States, Threat Responses)

---

## Overview

Phase 5B enhances the core game mechanics from Phase 5A by adding:
1. **Business Impact Calculations** - Financial consequences of incidents
2. **Time Pressure Mechanics** - Countdown timers and escalation
3. **Resource Constraints** - Cooldowns, budgets, and action limits
4. **Advanced Multi-Stage Campaigns** - Sophisticated threat progressions

These features transform the training from tactical exercises into strategic decision-making scenarios that mirror real-world incident response pressures.

---

## Feature Breakdown

### Feature 1: Business Impact Calculations (Priority: High)

**Goal**: Calculate and display financial/operational impact of security incidents

**Estimated Time**: 2-3 days

#### Implementation Tasks

**1.1 Business Impact Service** (`api/services/business_impact_service.py` - ~350 lines)
- [ ] Create `BusinessImpactService` class
- [ ] Implement downtime cost calculations
  - Revenue loss per hour based on organization size
  - Industry-specific multipliers (finance 3x, healthcare 2.5x, retail 2x)
  - System criticality factors (critical 5x, high 3x, medium 1.5x)
- [ ] Implement data loss impact calculations
  - Records compromised × value per record
  - Data classification multipliers (restricted 10x, confidential 5x)
  - Recovery costs (forensics, notification, credit monitoring)
- [ ] Implement compliance violation tracking
  - GDPR fines (€20M or 4% revenue)
  - HIPAA fines ($50k per violation)
  - PCI-DSS fines ($5k-$100k per month)
  - SOX penalties (up to $5M)
- [ ] Implement reputation damage simulation
  - Customer churn (5-20% based on severity)
  - Stock price impact (simulated)
  - Brand recovery costs
- [ ] Add cumulative impact tracking
  - Total financial loss
  - Total downtime hours
  - Total records compromised
  - Compliance penalties

**1.2 Impact Models** (add to `api/models/schemas.py`)
- [ ] Create `BusinessImpact` model
  ```python
  class BusinessImpact(BaseModel):
      downtime_cost: float  # $ per hour
      data_loss_cost: float  # Total data breach cost
      compliance_penalties: Dict[str, float]  # Framework: penalty
      reputation_damage: float  # Brand/customer impact
      total_cost: float  # Cumulative
      impact_description: str  # Human-readable
  ```
- [ ] Create `ImpactEvent` model
  ```python
  class ImpactEvent(BaseModel):
      timestamp: datetime
      event_type: Literal["downtime", "data_loss", "compliance", "reputation"]
      system_id: Optional[str]
      cost: float
      description: str
  ```

**1.3 GameState Integration**
- [ ] Add `business_impact` field to `GameState`
- [ ] Add `impact_events` list to `GameState`
- [ ] Update `Game Orchestrator` to calculate impact on state changes

**1.4 UI Dashboard** (`app/pages/2_War_Game.py` - ~150 lines)
- [ ] Create "Business Impact" section
- [ ] Display real-time cost counter
- [ ] Show breakdown by category (downtime, data loss, compliance, reputation)
- [ ] Add impact timeline
- [ ] Color-code severity (🟢 <$100k, 🟡 $100k-$1M, 🔴 >$1M)
- [ ] Show cost per minute ticker

**1.5 Testing**
- [ ] Create `test_business_impact.py` (150 lines)
- [ ] Test downtime calculations
- [ ] Test data loss calculations
- [ ] Test compliance penalties
- [ ] Test reputation damage
- [ ] Test cumulative tracking
- [ ] Test industry multipliers
- [ ] Test system criticality factors

**Deliverables**:
- `api/services/business_impact_service.py` (350 lines)
- `test_business_impact.py` (150 lines)
- Updated `GameState` model with impact tracking
- Business Impact dashboard in War Game UI (150 lines)

---

### Feature 2: Time Pressure Mechanics (Priority: High)

**Goal**: Add countdown timers and automatic escalation to create urgency

**Estimated Time**: 2-3 days

#### Implementation Tasks

**2.1 Time Pressure Service** (`api/services/time_pressure_service.py` - ~300 lines)
- [ ] Create `TimePressureService` class
- [ ] Implement countdown timer management
  - Objective-specific timers
  - Global incident timer
  - Critical action windows (e.g., "ransomware spreading in 30 min")
- [ ] Implement automatic escalation
  - Threat aggression increases over time
  - Systems degrade if not addressed (health -10% per 5 minutes)
  - New vulnerabilities exploited automatically
- [ ] Implement time-based scoring multipliers
  - Early response bonus (2x points if <10 min)
  - Speed penalty (0.5x points if >60 min)
  - Critical window bonus (3x if within window)
- [ ] Add "golden hour" mechanics
  - First 60 minutes critical for containment
  - Exponential cost increase after golden hour
- [ ] Implement pause/resume functionality
  - Allow training pauses
  - Track actual response time vs training time

**2.2 Timer Models** (add to `api/models/schemas.py`)
- [ ] Create `Timer` model
  ```python
  class Timer(BaseModel):
      id: str
      name: str
      duration_seconds: int
      remaining_seconds: int
      started_at: datetime
      expires_at: datetime
      is_critical: bool = False
      on_expiry_event: str  # Description of what happens
  ```
- [ ] Create `EscalationRule` model
  ```python
  class EscalationRule(BaseModel):
      trigger_time_minutes: int
      action: Literal["threat_escalate", "system_degrade", "spread", "alert"]
      target_id: Optional[str]
      severity_increase: int
  ```

**2.3 GameState Integration**
- [ ] Add `timers` list to `GameState`
- [ ] Add `escalation_rules` list to `GameState`
- [ ] Add `game_started_at` timestamp
- [ ] Add `time_multiplier` for scoring
- [ ] Update `Game Orchestrator` to check timers on every action

**2.4 UI Integration** (`app/pages/2_War_Game.py` - ~120 lines)
- [ ] Add "Active Timers" section
- [ ] Display countdown with visual urgency (🟢 >30min, 🟡 10-30min, 🔴 <10min)
- [ ] Add timer expiration alerts
- [ ] Show time elapsed since incident start
- [ ] Add pause/resume button
- [ ] Show time-based score multiplier

**2.5 Auto-Escalation Engine**
- [ ] Create background timer checking (async)
- [ ] Implement automatic threat escalation at intervals
- [ ] Implement automatic system degradation
- [ ] Generate timeline events for escalations

**2.6 Testing**
- [ ] Create `test_time_pressure.py` (150 lines)
- [ ] Test timer creation and countdown
- [ ] Test expiration handling
- [ ] Test automatic escalation
- [ ] Test scoring multipliers
- [ ] Test pause/resume
- [ ] Test golden hour mechanics

**Deliverables**:
- `api/services/time_pressure_service.py` (300 lines)
- `test_time_pressure.py` (150 lines)
- Updated `GameState` with timers and escalation
- Timer dashboard in War Game UI (120 lines)

---

### Feature 3: Resource Constraints (Priority: Medium)

**Goal**: Add cooldowns, budgets, and action limits for realistic resource management

**Estimated Time**: 2-3 days

#### Implementation Tasks

**3.1 Resource Manager Service** (`api/services/resource_manager_service.py` - ~320 lines)
- [ ] Create `ResourceManagerService` class
- [ ] Implement tool usage cooldowns
  - SIEM query cooldown: 2 minutes
  - Forensics analysis cooldown: 10 minutes
  - System restart cooldown: 5 minutes
  - Network scan cooldown: 3 minutes
- [ ] Implement action point system
  - Each action costs points (1-5 based on complexity)
  - Points regenerate over time (1 point per 2 minutes)
  - Max points based on role (SOC Analyst: 10, CISO: 15)
- [ ] Implement budget tracking
  - Starting budget based on organization size
  - Tool acquisition costs
  - External consultant costs
  - System recovery costs
- [ ] Implement staff availability
  - Limited concurrent actions
  - "All hands on deck" emergency mode
  - Fatigue penalties after prolonged incidents
- [ ] Add resource exhaustion consequences
  - Forced delays when out of points
  - Budget overruns flagged to management
  - Staff burnout impacts effectiveness

**3.2 Resource Models** (add to `api/models/schemas.py`)
- [ ] Create `ResourcePool` model
  ```python
  class ResourcePool(BaseModel):
      action_points: int
      max_action_points: int
      points_per_minute: float
      budget_remaining: float
      budget_total: float
      staff_available: int
      tools_on_cooldown: Dict[str, datetime]  # tool: available_at
  ```
- [ ] Create `ActionCost` model
  ```python
  class ActionCost(BaseModel):
      points: int
      budget: float
      cooldown_seconds: int
      requires_staff: int
  ```

**3.3 GameState Integration**
- [ ] Add `resource_pool` field to `GameState`
- [ ] Add `resource_history` for tracking
- [ ] Update `Game Orchestrator` to check resources before actions

**3.4 UI Integration** (`app/pages/2_War_Game.py` - ~100 lines)
- [ ] Add "Resources" sidebar section
- [ ] Display action points meter
- [ ] Display budget remaining
- [ ] Show tools on cooldown with timers
- [ ] Display staff availability
- [ ] Add "insufficient resources" warnings

**3.5 Cooldown Management**
- [ ] Track last usage timestamp per tool
- [ ] Calculate cooldown remaining
- [ ] Block actions if tool on cooldown
- [ ] Generate UI warnings for unavailable tools

**3.6 Testing**
- [ ] Create `test_resource_manager.py` (130 lines)
- [ ] Test action point deduction and regeneration
- [ ] Test budget tracking
- [ ] Test tool cooldowns
- [ ] Test staff availability
- [ ] Test resource exhaustion handling
- [ ] Test role-based resource limits

**Deliverables**:
- `api/services/resource_manager_service.py` (320 lines)
- `test_resource_manager.py` (130 lines)
- Updated `GameState` with resource tracking
- Resource dashboard in War Game UI (100 lines)

---

### Feature 4: Advanced Multi-Stage Threat Campaigns (Priority: Medium)

**Goal**: Create sophisticated, multi-phase attack scenarios

**Estimated Time**: 2-3 days

#### Implementation Tasks

**4.1 Campaign Manager Service** (`api/services/campaign_manager_service.py` - ~350 lines)
- [ ] Create `CampaignManagerService` class
- [ ] Implement campaign stage definitions
  - Stage 1: Initial Access (phishing, exploit)
  - Stage 2: Reconnaissance (network mapping, credential harvesting)
  - Stage 3: Lateral Movement (spread to other systems)
  - Stage 4: Privilege Escalation (gain admin access)
  - Stage 5: Data Exfiltration or Impact (achieve objective)
- [ ] Implement stage progression logic
  - Automatic progression based on time
  - Conditional progression based on player actions
  - Branching campaigns based on detection level
- [ ] Add campaign success/failure conditions
  - Success if threat reaches Stage 5
  - Failure if detected early and contained
  - Partial success if some data exfiltrated
- [ ] Implement adaptive campaigns
  - Change tactics if detected
  - Accelerate if undetected
  - Pivot to alternative objectives
- [ ] Add campaign intelligence gathering
  - Track what player knows
  - Reveal information progressively
  - Hint at next stage

**4.2 Campaign Models** (add to `api/models/schemas.py`)
- [ ] Create `ThreatCampaign` model
  ```python
  class ThreatCampaign(BaseModel):
      id: str
      name: str
      threat_actor_id: str
      current_stage: int
      total_stages: int
      stage_descriptions: List[str]
      progression_conditions: List[str]
      started_at: datetime
      completed: bool = False
  ```
- [ ] Create `CampaignStage` model
  ```python
  class CampaignStage(BaseModel):
      stage_number: int
      name: str
      description: str
      duration_minutes: int
      systems_targeted: List[str]
      ttps_used: List[str]
      detection_difficulty: Literal["easy", "medium", "hard"]
  ```

**4.3 GameState Integration**
- [ ] Add `active_campaigns` list to `GameState`
- [ ] Update `ThreatResponseEngine` to check campaign stages
- [ ] Add campaign events to incident timeline

**4.4 UI Integration** (`app/pages/2_War_Game.py` - ~130 lines)
- [ ] Add "Threat Campaign" section
- [ ] Display campaign progress bar
- [ ] Show current stage and next stage
- [ ] Add campaign intelligence summary
- [ ] Display TTPs being used
- [ ] Show campaign timeline

**4.5 Campaign Templates**
- [ ] Create ransomware campaign template
  - Stage 1: Phishing email
  - Stage 2: Credential theft
  - Stage 3: Lateral movement
  - Stage 4: Admin access
  - Stage 5: Encrypt and ransom
- [ ] Create APT espionage campaign
- [ ] Create insider threat campaign
- [ ] Create supply chain attack campaign

**4.6 Testing**
- [ ] Create `test_campaign_manager.py` (140 lines)
- [ ] Test campaign initialization
- [ ] Test stage progression
- [ ] Test branching logic
- [ ] Test adaptive behavior
- [ ] Test campaign completion
- [ ] Test multiple concurrent campaigns

**Deliverables**:
- `api/services/campaign_manager_service.py` (350 lines)
- `test_campaign_manager.py` (140 lines)
- 4 campaign templates
- Updated `GameState` with campaign tracking
- Campaign dashboard in War Game UI (130 lines)

---

## Integration Plan

### Game Orchestrator Updates

**File**: `api/services/game_orchestrator.py`

1. [ ] Integrate `BusinessImpactService`
   - Calculate impact on system state changes
   - Track cumulative costs
2. [ ] Integrate `TimePressureService`
   - Check timers on every action
   - Trigger escalation events
3. [ ] Integrate `ResourceManagerService`
   - Validate resource availability before actions
   - Deduct resources on action execution
4. [ ] Integrate `CampaignManagerService`
   - Initialize campaigns on game start
   - Progress campaigns based on time/actions

### War Game UI Updates

**File**: `app/pages/2_War_Game.py`

1. [ ] Add Business Impact dashboard (150 lines)
2. [ ] Add Timer/Urgency section (120 lines)
3. [ ] Add Resource Management sidebar (100 lines)
4. [ ] Add Threat Campaign tracker (130 lines)
5. [ ] Update action handler to check resources
6. [ ] Add real-time updates for timers

**Total UI Addition**: ~500 lines

---

## Testing Strategy

### Unit Tests
- [ ] `test_business_impact.py` (150 lines) - 10 tests
- [ ] `test_time_pressure.py` (150 lines) - 10 tests
- [ ] `test_resource_manager.py` (130 lines) - 8 tests
- [ ] `test_campaign_manager.py` (140 lines) - 9 tests

**Total**: 570 lines, 37 tests

### Integration Tests
- [ ] Create `test_phase5b_integration.py` (200 lines)
  - Test business impact during gameplay
  - Test timer expiration effects
  - Test resource exhaustion scenarios
  - Test campaign progression
  - Test combined feature interactions

### End-to-End Tests
- [ ] Test complete war game with all Phase 5B features
- [ ] Verify financial impacts accumulate correctly
- [ ] Verify timers trigger escalations
- [ ] Verify resource constraints block actions
- [ ] Verify campaigns progress realistically

---

## Documentation Updates

### Documentation to Update
1. [ ] `ROADMAP.md` - Mark Phase 5B complete
2. [ ] `CHANGELOG.md` - Add v0.7.0 entry
3. [ ] `PROJECT_SUMMARY.md` - Update status and metrics
4. [ ] `PHASE5B_COMPLETE.md` - Create completion document
5. [ ] `README.md` - Update features list

---

## Success Metrics

### Code Metrics
- **Target Lines**: ~1,820 lines of production code
  - 350 lines: Business Impact Service
  - 300 lines: Time Pressure Service
  - 320 lines: Resource Manager Service
  - 350 lines: Campaign Manager Service
  - 500 lines: UI enhancements
- **Test Lines**: ~770 lines
- **Test Coverage**: 100% (37+ tests passing)

### Feature Metrics
- Business impact tracking for all system changes
- Countdown timers for urgent objectives
- Resource pools with regeneration
- Multi-stage threat campaigns (4+ templates)

### User Experience
- Realistic financial consequences visible
- Time pressure creates urgency
- Resource management adds strategic depth
- Campaigns feel like real threat actor behavior

---

## Timeline

### Week 1 (Days 1-5)
- **Days 1-2**: Feature 1 (Business Impact)
- **Days 3-4**: Feature 2 (Time Pressure)
- **Day 5**: Feature 3 start (Resource Constraints)

### Week 2 (Days 6-10)
- **Day 6**: Feature 3 complete
- **Days 7-8**: Feature 4 (Campaign Manager)
- **Day 9**: Integration and testing
- **Day 10**: Documentation and polish

### Week 3 (Days 11-14) - Buffer
- **Days 11-12**: End-to-end testing
- **Day 13**: Bug fixes and polish
- **Day 14**: Final documentation and release

---

## Risk Mitigation

### Technical Risks
1. **Performance**: Timer checks on every action
   - Mitigation: Async timer service, check only active timers
2. **Complexity**: Multiple interacting systems
   - Mitigation: Clear service boundaries, comprehensive tests
3. **UI Clutter**: Too many dashboards
   - Mitigation: Collapsible sections, priority-based display

### Scope Risks
1. **Feature Creep**: Additional mechanics
   - Mitigation: Stick to 4 core features, defer enhancements
2. **Testing Time**: 37+ tests to write
   - Mitigation: Write tests alongside features, not after

---

## Next Steps After Phase 5B

### Option A: Phase 6 - Analytics & AAR
- After Action Review generation
- Performance dashboards
- Decision analysis
- Training recommendations

### Option B: Continue Phase 5 Polish
- Advanced reporting features
- Multiplayer support
- Saved game states
- Custom difficulty settings

---

**Plan Created**: 2025-11-04
**Estimated Completion**: 2-3 weeks
**Dependencies**: Phase 5A complete ✅, Phase 4 complete ✅
**Status**: Ready to begin implementation
