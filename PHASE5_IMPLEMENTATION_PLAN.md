# Phase 5: Game Mechanics & Inventory - Implementation Plan

**Status**: Planning Phase
**Target Completion**: 1-2 weeks
**Priority**: Complete partially-finished phase before new features

---

## Current State Analysis

### What We Have ✅
- ✅ **GameState Model** - Tracks session, organization, inventory, timeline, score
- ✅ **Inventory System** - Tools, access levels, credentials tracking
- ✅ **Basic Objectives** - `objectives_completed` and `objectives_failed` lists
- ✅ **System Model** - Systems with vulnerabilities, criticality, security controls
- ✅ **Threat Actor Model** - Name, motivation, sophistication, TTPs
- ✅ **Game Master Service** - AI-driven narrative and action processing
- ✅ **Game Orchestrator** - Session management, action processing

### What's Missing ❌
- ❌ **Automatic Objective Generation** - Objectives are manually defined
- ❌ **Dynamic Threat Responses** - Threats don't react to player actions
- ❌ **System State Tracking** - Systems can't be online/offline/compromised
- ❌ **Business Impact Calculation** - No cost/impact metrics
- ❌ **Resource Constraints** - Unlimited tool usage
- ❌ **Time Pressure** - No countdown timers or time-based escalation

---

## Implementation Phases

### PHASE A: Core Mechanics (Week 1) 🔥

#### Feature 1: Automatic Objective Generation
**Priority**: CRITICAL - Biggest time saver for users

**What**: Generate objectives automatically from scenario data
- Analyze vulnerabilities → Create mitigation objectives
- Analyze threat actors → Create detection objectives
- Analyze critical systems → Create protection objectives
- Match difficulty to player role and scenario type

**Implementation**:
1. **New Service**: `api/services/objective_generator.py`
   - `generate_objectives_from_scenario(organization, scenario_type, difficulty, player_role)`
   - Returns list of structured objectives with success criteria

2. **Objective Model Enhancement** (add to schemas.py):
   ```python
   class Objective(BaseModel):
       id: str
       description: str
       type: Literal["detect", "contain", "mitigate", "investigate", "protect", "report"]
       success_criteria: str
       time_limit_minutes: Optional[int] = None
       points: int = 25
       difficulty: Literal["easy", "medium", "hard"]
       related_systems: List[str] = []
       related_threats: List[str] = []
       hints: List[str] = []
   ```

3. **Update GameState** to use `List[Objective]` instead of `List[str]`

4. **Integration Points**:
   - `/game/start` - Generate objectives when starting game
   - `/scenarios/generate` - Optionally generate objectives with scenario
   - Scenario Editor - Show generated objectives, allow editing

**Estimated Time**: 2 days

**Files to Create/Modify**:
- NEW: `api/services/objective_generator.py` (~250 lines)
- MODIFY: `api/models/schemas.py` - Add Objective model
- MODIFY: `api/services/game_orchestrator.py` - Call objective generator
- MODIFY: `app/pages/2_War_Game.py` - Display structured objectives

---

#### Feature 2: System State Modifications
**Priority**: HIGH - Visual feedback and immersion

**What**: Track and update system status during gameplay
- Systems can be: `online`, `offline`, `compromised`, `recovering`, `patched`
- State changes affect available tools and actions
- Display system health in UI

**Implementation**:
1. **Update System Model** (in schemas.py):
   ```python
   class SystemState(BaseModel):
       system_id: str
       status: Literal["online", "offline", "compromised", "recovering", "patched"]
       health: int = 100  # 0-100
       last_update: datetime
       affected_services: List[str] = []

   class GameState(BaseModel):
       # ... existing fields ...
       system_states: Dict[str, SystemState] = {}  # system_id: state
   ```

2. **New Service**: `api/services/system_state_manager.py`
   - `update_system_state(game_state, system_id, new_status, reason)`
   - `get_affected_systems(action, game_state)`
   - `calculate_system_health(system, events)`
   - `check_system_availability(system_id, game_state)`

3. **Game Master Enhancement**:
   - Extract system state changes from AI responses
   - Update `game_state.system_states` based on actions
   - Include system status in narrative context

4. **UI Updates**:
   - Add system status dashboard in War Game page
   - Color-code systems (green/yellow/red)
   - Show affected services

**Estimated Time**: 3 days

**Files to Create/Modify**:
- NEW: `api/services/system_state_manager.py` (~200 lines)
- MODIFY: `api/models/schemas.py` - Add SystemState model
- MODIFY: `api/services/game_master_service.py` - Track state changes
- MODIFY: `app/pages/2_War_Game.py` - System status display (~100 lines)

---

#### Feature 3: Dynamic Threat Actor Responses
**Priority**: HIGH - Realism and challenge

**What**: Threats react to player actions dynamically
- If contained quickly → Threat retreats
- If ignored → Threat escalates (lateral movement, data exfiltration)
- If partially mitigated → Threat adapts (changes tactics)

**Implementation**:
1. **Update ThreatActor in GameState**:
   ```python
   class ThreatActorState(BaseModel):
       threat_actor_id: str
       status: Literal["active", "contained", "eliminated", "dormant"]
       current_tactics: List[str] = []
       systems_compromised: List[str] = []
       detection_level: int = 0  # 0-100, how aware they are of being detected
       aggression_level: int = 50  # 0-100, how aggressively they're acting

   class GameState(BaseModel):
       # ... existing fields ...
       threat_states: Dict[str, ThreatActorState] = {}
   ```

2. **New Service**: `api/services/threat_response_engine.py`
   - `evaluate_player_action(action, game_state)` → threat response
   - `escalate_threat(threat_actor, game_state)` → new events
   - `adapt_tactics(threat_actor, detected_actions)` → tactic changes
   - `generate_threat_event(threat_state, game_state)` → timeline event

3. **Game Master Integration**:
   - After each player action, evaluate threat response
   - Generate automatic escalation events based on time
   - Include threat state in AI context for realistic behavior

4. **Timeline Integration**:
   - Add automatic threat events every N minutes
   - Show escalation notifications
   - Track containment progress

**Estimated Time**: 3 days

**Files to Create/Modify**:
- NEW: `api/services/threat_response_engine.py` (~300 lines)
- MODIFY: `api/models/schemas.py` - Add ThreatActorState
- MODIFY: `api/services/game_master_service.py` - Process threat responses
- MODIFY: `api/services/game_orchestrator.py` - Periodic threat updates

---

### PHASE B: Advanced Polish (Week 2) ✨

#### Feature 4: Business Impact Calculations
**Priority**: MEDIUM - Adds context to scoring

**What**: Calculate and display business impact of incidents
- Downtime costs ($ per hour per system based on criticality)
- Data loss/exposure (records affected, compliance violations)
- Reputation damage (media coverage, customer trust)
- Recovery costs (forensics, remediation, legal)

**Implementation**:
1. **New Model**:
   ```python
   class BusinessImpact(BaseModel):
       downtime_cost: float = 0.0  # dollars
       downtime_hours: float = 0.0
       data_records_affected: int = 0
       data_exfiltrated_gb: float = 0.0
       compliance_violations: List[str] = []
       reputation_score: int = 100  # 0-100
       recovery_cost: float = 0.0
       total_cost: float = 0.0

   class GameState(BaseModel):
       # ... existing fields ...
       business_impact: BusinessImpact = BusinessImpact()
   ```

2. **New Service**: `api/services/business_impact_calculator.py`
   - `calculate_downtime_cost(system, duration_hours, organization)`
   - `calculate_data_loss(systems_compromised, organization)`
   - `calculate_reputation_impact(incident_severity, response_time)`
   - `update_impact(game_state, event)` → Update running totals

3. **UI Integration**:
   - Show business impact dashboard
   - Display costs in real-time
   - Final impact report at game end

**Estimated Time**: 2 days

**Files to Create/Modify**:
- NEW: `api/services/business_impact_calculator.py` (~150 lines)
- MODIFY: `api/models/schemas.py` - Add BusinessImpact model
- MODIFY: `app/pages/2_War_Game.py` - Business impact display

---

#### Feature 5: Time Pressure Mechanics
**Priority**: MEDIUM - Adds urgency and realism

**What**: Time-based scenario progression
- Countdown timers for objectives
- Automatic threat escalation over time
- Time-based scoring penalties
- "Golden hour" bonus for fast response

**Implementation**:
1. **Update Objective Model**:
   ```python
   class Objective(BaseModel):
       # ... existing fields ...
       time_limit_minutes: Optional[int] = None
       deadline: Optional[datetime] = None
       time_bonus_points: int = 0
   ```

2. **New Service**: `api/services/time_pressure_manager.py`
   - `check_deadlines(game_state)` → List of expired objectives
   - `calculate_time_bonus(objective, completion_time)`
   - `escalate_by_time(game_state)` → Auto-escalation events
   - `apply_time_penalties(game_state)`

3. **Game Orchestrator Enhancement**:
   - Background task to check time every minute
   - Auto-generate escalation events
   - Update UI with countdown timers

4. **UI Updates**:
   - Countdown timers next to objectives
   - Warning alerts for approaching deadlines
   - Time-based score modifiers

**Estimated Time**: 2 days

**Files to Create/Modify**:
- NEW: `api/services/time_pressure_manager.py` (~180 lines)
- MODIFY: `api/services/game_orchestrator.py` - Time-based checks
- MODIFY: `app/pages/2_War_Game.py` - Countdown timers display

---

#### Feature 6: Resource Constraints
**Priority**: LOW - Strategic depth (optional)

**What**: Limited tool usage and cooldowns
- Tools have limited uses (e.g., forensics toolkit: 3 uses)
- Cooldown periods (e.g., vulnerability scan: 10 min cooldown)
- Budget constraints for expensive operations
- Tool acquisition through gameplay

**Implementation**:
1. **Update Tool Model**:
   ```python
   class Tool(BaseModel):
       # ... existing fields ...
       uses_remaining: Optional[int] = None  # None = unlimited
       cooldown_minutes: int = 0
       last_used: Optional[datetime] = None
       cost: float = 0.0  # budget cost per use

   class GameState(BaseModel):
       # ... existing fields ...
       budget_remaining: float = 10000.0  # dollars
   ```

2. **New Service**: `api/services/resource_manager.py`
   - `check_tool_availability(tool, game_state)` → bool
   - `consume_tool_use(tool_name, game_state)`
   - `apply_cooldown(tool_name, duration, game_state)`
   - `check_budget(cost, game_state)` → bool

3. **Game Master Integration**:
   - Validate tool availability before actions
   - Deny actions if resources unavailable
   - Suggest alternatives

**Estimated Time**: 2 days

**Files to Create/Modify**:
- NEW: `api/services/resource_manager.py` (~150 lines)
- MODIFY: `api/models/schemas.py` - Update Tool model
- MODIFY: `api/services/game_master_service.py` - Resource checks
- MODIFY: `app/pages/2_War_Game.py` - Tool availability display

---

## Implementation Order (Prioritized)

### Week 1: Core Features
**Day 1-2**: Feature 1 - Automatic Objective Generation
**Day 3-5**: Feature 2 - System State Modifications
**Day 6-8**: Feature 3 - Dynamic Threat Responses

**Deliverable**: War games with auto-generated objectives, system health tracking, and adaptive threats

### Week 2: Polish & Enhancement
**Day 9-10**: Feature 4 - Business Impact Calculations
**Day 11-12**: Feature 5 - Time Pressure Mechanics
**Day 13-14**: Feature 6 - Resource Constraints (if time permits)

**Deliverable**: Complete game mechanics with business context, urgency, and strategic depth

---

## Success Criteria

### Must Have ✅
- [x] Objectives generated automatically from scenarios
- [x] Systems track state (online/offline/compromised)
- [x] Threats respond dynamically to player actions
- [x] All changes visible in UI

### Should Have ⭐
- [ ] Business impact calculations and display
- [ ] Time pressure with countdown timers
- [ ] Escalation based on time elapsed

### Nice to Have 💎
- [ ] Resource constraints and tool cooldowns
- [ ] Budget tracking
- [ ] Advanced tool acquisition mechanics

---

## Testing Plan

### Unit Tests
- Objective generator produces valid objectives
- System state transitions are logical
- Threat responses match player actions
- Business impact calculations are accurate
- Time pressure applies correctly

### Integration Tests
- Generate scenario → Auto-generate objectives → Start game
- Player action → System state change → UI update
- Player action → Threat responds → New timeline event
- Time elapses → Automatic escalation → Deadline expires

### Manual Testing
- Play complete war game with all features enabled
- Verify objectives are relevant to scenario
- Verify system states update correctly
- Verify threats escalate realistically
- Verify business impact makes sense

---

## Migration Strategy

### Backward Compatibility
- Existing game sessions without objectives still work
- GameState model extensions are optional
- Old scenarios work with new objective generation

### Data Migration
- Add `system_states` to existing sessions as empty dict
- Add `threat_states` to existing sessions
- Generate objectives for loaded old scenarios on-demand

---

## Documentation Updates

### User Documentation
- Update War Game guide with new mechanics
- Document objective types and success criteria
- Explain system health indicators
- Describe threat escalation behavior

### Developer Documentation
- API docs for new services
- Schema changes documented
- Integration points clearly described

---

## Risk Assessment

### Technical Risks
- **System state tracking** adds complexity to GameState
  - Mitigation: Keep state simple, use clear status enum

- **Threat responses** might feel repetitive
  - Mitigation: Variety in tactics, randomness, AI-generated narratives

- **Performance** with many automatic updates
  - Mitigation: Batch updates, optimize queries, cache calculations

### User Experience Risks
- **Too many objectives** overwhelming
  - Mitigation: Limit to 3-5 key objectives, rest are optional

- **Time pressure** too stressful
  - Mitigation: Make timers optional, adjustable difficulty

- **Resource constraints** frustrating
  - Mitigation: Make optional, start with generous limits

---

## Next Steps

1. ✅ **Review this plan** - Get approval on approach
2. **Create git branch** - `feature/phase5-game-mechanics`
3. **Start with Feature 1** - Objective generation (highest value)
4. **Iterate rapidly** - Small commits, frequent testing
5. **Update docs** - Keep PHASE5_COMPLETE.md updated

---

**Estimated Total Time**: 10-14 days
**Priority Order**: Features 1, 2, 3 (must have) → 4, 5 (should have) → 6 (nice to have)
**End Goal**: Feature-complete war gaming platform with realistic mechanics and professional polish
