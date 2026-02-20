# Phase 4: Enhanced Safety & Policies - Implementation Plan

**Status**: 🚧 In Progress
**Start Date**: 2025-11-04
**Target Completion**: 2 weeks
**Priority**: HIGH - Critical for enterprise deployment and compliance

---

## Overview

Phase 4 enhances the existing content policy system with comprehensive safety mechanisms, audit logging, content filtering, and compliance tracking. This is essential for enterprise deployment, regulatory compliance, and safe multi-user environments.

---

## Current State Analysis

### What We Have ✅
- ✅ **ContentPolicyService** - Basic policy checking with 4 levels
- ✅ **4 Policy Levels** - Defensive, Educational, Advanced, Unrestricted
- ✅ **LLM-based Content Checking** - `check_content()` method
- ✅ **Policy Configuration** - Allowed/blocked categories per level
- ✅ **Basic API Endpoints** - `/content-policy/check`, `/content-policy/policies`

### What's Missing ❌
- ❌ **Pre-Action Content Checking** - Check player actions before processing
- ❌ **Post-Generation Validation** - Validate AI-generated content
- ❌ **Audit Logging System** - Track all policy checks and violations
- ❌ **Content Filtering** - Detect sensitive info, credentials, exploit code
- ❌ **Policy Violation Handler** - Automated response to violations
- ❌ **Compliance Tracking** - Reports and metrics
- ❌ **Policy Configuration UI** - Settings page integration

---

## Implementation Plan

### Feature 1: Pre-Action Content Checking (Days 1-2) 🔥

**Goal**: Check all player actions before they are processed by the game master

**Why Important**: Prevents policy violations before they enter the system, reducing risk and improving user experience.

#### 1.1 Action Filter Service
**File**: `api/services/action_filter_service.py` (~200 lines)

**Functionality**:
- `check_action(action: str, policy_level: str) -> ActionCheckResult`
- Pattern-based quick checks (regex for common violations)
- LLM-based semantic analysis for complex cases
- Configurable strictness levels
- Fast response times (<500ms for 90% of cases)

**Quick Check Patterns**:
```python
SENSITIVE_PATTERNS = {
    "credentials": [r"password\s*[:=]\s*\S+", r"api[_-]?key\s*[:=]\s*\S+"],
    "exploit_code": [r"shellcode", r"payload.*exec", r"eval\("],
    "pii": [r"\b\d{3}-\d{2}-\d{4}\b", r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"],
    "destructive": [r"rm\s+-rf", r"drop\s+database", r"format\s+c:"]
}
```

#### 1.2 Game Orchestrator Integration
**File**: `api/services/game_orchestrator.py` (modify)

**Changes**:
- Add pre-action filtering before `game_master.process_action()`
- Return user-friendly messages for blocked actions
- Log all filtering decisions
- Track filter effectiveness metrics

#### 1.3 API Models
**File**: `api/models/schemas.py` (add)

```python
class ActionCheckResult(BaseModel):
    """Result of action content check."""
    is_allowed: bool
    reason: Optional[str] = None
    violations: List[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    suggested_alternative: Optional[str] = None
```

---

### Feature 2: Post-Generation Validation (Days 3-4)

**Goal**: Validate all AI-generated content before returning to users

**Why Important**: Ensures AI responses comply with policy, prevents leakage of sensitive patterns, maintains training quality.

#### 2.1 Content Validator Service
**File**: `api/services/content_validator_service.py` (~250 lines)

**Functionality**:
- `validate_narrative(narrative: str, policy_level: str) -> ValidationResult`
- `validate_scenario(organization: Organization, policy_level: str) -> ValidationResult`
- `sanitize_content(content: str, violations: List[str]) -> str`
- Pattern detection for sensitive content
- LLM-based validation for context
- Auto-sanitization with redaction

**Validation Checks**:
1. **Credential Patterns**: Passwords, API keys, tokens
2. **Exploit Code**: Shell commands, payloads, malicious scripts
3. **PII Detection**: SSNs, emails, phone numbers, addresses
4. **Sensitive Info**: Internal IPs, real company names, real CVEs (if policy level doesn't allow)
5. **Policy Compliance**: Check against policy's blocked categories

#### 2.2 Integration Points
**Files to Modify**:
- `api/services/game_master_service.py` - Validate narratives before returning
- `api/services/scenario_orchestrator.py` - Validate scenarios after generation
- `api/services/objective_generator.py` - Validate objectives

**Pattern**:
```python
# After generating content
validation_result = await content_validator.validate_narrative(narrative, policy_level)
if not validation_result.is_safe:
    if validation_result.can_sanitize:
        narrative = content_validator.sanitize_content(narrative, validation_result.violations)
    else:
        # Regenerate or return error
        raise ContentPolicyViolation(validation_result.reason)
```

---

### Feature 3: Audit Logging System (Days 5-6) 📝

**Goal**: Comprehensive logging of all policy checks, violations, and safety events

**Why Important**: Compliance requirements, incident investigation, policy refinement, user accountability.

#### 3.1 Audit Log Service
**File**: `api/services/audit_log_service.py` (~300 lines)

**Functionality**:
- `log_policy_check(check_type, content_hash, result, metadata)`
- `log_violation(violation_type, severity, content_hash, action_taken, user_id)`
- `log_content_filter(filter_type, matched_patterns, policy_level)`
- `get_audit_logs(filters, start_date, end_date) -> List[AuditLog]`
- `generate_compliance_report(period) -> ComplianceReport`

**Storage**: JSON files with daily rotation (upgrade to database in Phase 8)

#### 3.2 Audit Log Models
**File**: `api/models/schemas.py` (add)

```python
class AuditLog(BaseModel):
    """Audit log entry for policy checks and violations."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: Literal["policy_check", "violation", "filter", "sanitization"]
    severity: Literal["info", "warning", "error", "critical"]
    policy_level: str
    content_hash: str  # SHA256 hash for privacy
    result: str  # "allowed", "blocked", "sanitized"
    violations: List[str] = Field(default_factory=list)
    action_taken: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ComplianceReport(BaseModel):
    """Compliance report for a time period."""
    period_start: datetime
    period_end: datetime
    total_checks: int
    total_violations: int
    violation_rate: float
    violations_by_type: Dict[str, int]
    violations_by_severity: Dict[str, int]
    policy_level_distribution: Dict[str, int]
    top_violation_patterns: List[Dict[str, Any]]
```

#### 3.3 Integration
- Add audit logging to all policy check points
- Add audit logging to all content filtering
- Add audit logging to violation handling

---

### Feature 4: Content Filtering System (Days 7-9) 🔍

**Goal**: Detect and filter sensitive information, credentials, and exploit code

**Why Important**: Prevents accidental exposure of real credentials, protects against real-world attacks, ensures training remains educational.

#### 4.1 Content Filter Service
**File**: `api/services/content_filter_service.py` (~350 lines)

**Functionality**:
- `detect_credentials(content: str) -> List[CredentialMatch]`
- `detect_pii(content: str) -> List[PIIMatch]`
- `detect_exploit_code(content: str) -> List[ExploitMatch]`
- `detect_sensitive_info(content: str) -> List[SensitiveMatch]`
- `redact_content(content: str, matches: List[Match]) -> str`

**Filter Categories**:

1. **Credentials Detection**:
   - API keys (AWS, Azure, OpenAI, GitHub, etc.)
   - Passwords in various formats
   - OAuth tokens
   - SSH keys
   - Database connection strings
   - JWT tokens

2. **PII Detection**:
   - Social Security Numbers
   - Email addresses
   - Phone numbers
   - Physical addresses
   - Credit card numbers
   - Passport numbers

3. **Exploit Code Detection**:
   - Shell commands (rm -rf, format, etc.)
   - SQL injection patterns
   - XSS payloads
   - Command injection
   - Shellcode patterns
   - Reverse shell commands

4. **Sensitive Information**:
   - Internal IP addresses
   - Real company names (configurable allow-list)
   - Real CVE IDs with active exploits
   - Production URLs

**Redaction Strategy**:
- `[REDACTED-CREDENTIAL]`
- `[REDACTED-PII]`
- `[REDACTED-EXPLOIT]`
- `[REDACTED-SENSITIVE]`

#### 4.2 Filter Configuration
**File**: `api/models/schemas.py` (add)

```python
class FilterConfig(BaseModel):
    """Content filter configuration."""
    enable_credential_detection: bool = True
    enable_pii_detection: bool = True
    enable_exploit_detection: bool = True
    enable_sensitive_detection: bool = True
    redaction_style: Literal["remove", "mask", "replace"] = "mask"
    custom_patterns: Dict[str, List[str]] = Field(default_factory=dict)
    allowlist: List[str] = Field(default_factory=list)
```

---

### Feature 5: Policy Violation Handler (Days 10-11)

**Goal**: Automated handling of policy violations with appropriate responses

**Why Important**: Consistent violation handling, user education, escalation management, system security.

#### 5.1 Violation Handler Service
**File**: `api/services/violation_handler_service.py` (~200 lines)

**Functionality**:
- `handle_violation(violation: PolicyViolation) -> ViolationResponse`
- `escalate_violation(violation_history: List[PolicyViolation])`
- `notify_administrators(violation: PolicyViolation)`
- `get_violation_metrics(user_id: Optional[str])`

**Violation Levels**:
1. **Low** (Informational):
   - Log only
   - Show warning to user
   - Continue operation

2. **Medium** (Warning):
   - Log with audit
   - Block action
   - Show educational message
   - Suggest alternative

3. **High** (Serious):
   - Log with audit
   - Block action
   - Alert user
   - Notify session owner
   - Track repeat violations

4. **Critical** (Severe):
   - Log with full audit
   - Block action and session
   - Alert administrators
   - Require policy review
   - Consider account restrictions

#### 5.2 Violation Response Models
```python
class PolicyViolation(BaseModel):
    """Policy violation record."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: Literal["low", "medium", "high", "critical"]
    violation_type: str
    content_hash: str
    policy_level: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    action_taken: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ViolationResponse(BaseModel):
    """Response to a policy violation."""
    action: Literal["allow", "warn", "block", "escalate"]
    message: str
    educational_content: Optional[str] = None
    suggested_alternative: Optional[str] = None
    requires_review: bool = False
```

---

### Feature 6: Compliance Tracking & Reports (Days 12-13) 📊

**Goal**: Track compliance metrics and generate reports for auditing

**Why Important**: Regulatory requirements (SOC2, ISO 27001), customer trust, policy effectiveness measurement.

#### 6.1 Compliance Tracker Service
**File**: `api/services/compliance_tracker_service.py` (~250 lines)

**Functionality**:
- `track_policy_usage(session_id, policy_level, duration)`
- `track_violation_resolution(violation_id, resolution)`
- `generate_daily_report() -> ComplianceReport`
- `generate_monthly_report() -> ComplianceReport`
- `export_compliance_data(format: Literal["json", "csv"]) -> bytes`

**Metrics Tracked**:
1. **Policy Usage**:
   - Sessions by policy level
   - Average session duration by policy
   - User distribution across policies

2. **Violation Metrics**:
   - Total violations by type
   - Violation rate over time
   - Repeat violators
   - Resolution times

3. **Filter Effectiveness**:
   - Total filters applied
   - False positive rate
   - Content sanitization rate

4. **Compliance Status**:
   - Policy adherence rate
   - Audit log completeness
   - User training completion (future)

#### 6.2 Report Generation
**Formats**:
- JSON export for programmatic access
- CSV export for spreadsheet analysis
- HTML reports for viewing (future)
- PDF reports for management (future)

---

### Feature 7: Settings UI Integration (Day 14)

**Goal**: Add policy configuration to Settings page

**Why Important**: User control, policy customization, compliance configuration.

#### 7.1 Settings Page Updates
**File**: `app/pages/3_Settings.py` (modify)

**New Section**: "Content Policy & Safety"

**Controls**:
1. **Default Policy Level** - Dropdown (defensive/educational/advanced/unrestricted)
2. **Enable Pre-Action Filtering** - Toggle
3. **Enable Post-Generation Validation** - Toggle
4. **Content Filter Configuration**:
   - Enable credential detection
   - Enable PII detection
   - Enable exploit detection
   - Enable sensitive info detection
5. **Audit Logging**:
   - Enable audit logging
   - Audit log retention days
6. **Violation Handling**:
   - Violation severity thresholds
   - Administrator email for alerts
7. **Compliance Reporting**:
   - Generate daily reports
   - Export compliance data

#### 7.2 New API Endpoints
**File**: `api/routers/content_policy.py` (expand)

```
GET  /content-policy/config          - Get current configuration
POST /content-policy/config          - Update configuration
GET  /content-policy/audit-logs      - Get audit logs (paginated)
GET  /content-policy/compliance-report - Get compliance report
POST /content-policy/export          - Export compliance data
GET  /content-policy/violations      - Get violations (admin)
```

---

## Testing Strategy

### Unit Tests
- Test pattern matching for all filter types
- Test policy check logic
- Test audit log creation
- Test violation handling flows

### Integration Tests
- Test pre-action filtering in game flow
- Test post-generation validation in scenario creation
- Test audit logging across all services
- Test compliance report generation

### End-to-End Tests
- Generate scenario with different policy levels
- Try various actions that should be blocked
- Verify audit logs are created
- Generate compliance reports
- Test Settings UI updates

### Performance Tests
- Pre-action check latency (<500ms target)
- Post-generation validation overhead
- Audit log write performance
- Report generation time

---

## Success Metrics

### Functional
- ✅ 100% of actions checked before processing
- ✅ 100% of AI-generated content validated
- ✅ All policy checks logged
- ✅ All violations handled appropriately
- ✅ Compliance reports available

### Performance
- ✅ <500ms average pre-action check time
- ✅ <2s post-generation validation time
- ✅ <100ms audit log write time
- ✅ <5s compliance report generation

### Quality
- ✅ <5% false positive rate for filters
- ✅ 0 false negatives for critical violations
- ✅ 100% audit log completeness
- ✅ Full Settings UI integration

---

## Files to Create (7 new files)

1. `api/services/action_filter_service.py` (~200 lines)
2. `api/services/content_validator_service.py` (~250 lines)
3. `api/services/audit_log_service.py` (~300 lines)
4. `api/services/content_filter_service.py` (~350 lines)
5. `api/services/violation_handler_service.py` (~200 lines)
6. `api/services/compliance_tracker_service.py` (~250 lines)
7. `api/utils/pattern_matcher.py` (~150 lines) - Shared regex patterns

**Total New Code**: ~1,700 lines

---

## Files to Modify (5 files)

1. `api/models/schemas.py` - Add new models
2. `api/routers/content_policy.py` - Add new endpoints
3. `api/services/game_orchestrator.py` - Add pre-action filtering
4. `api/services/game_master_service.py` - Add post-generation validation
5. `app/pages/3_Settings.py` - Add policy configuration UI

**Total Modifications**: ~500 lines

---

## Timeline

| Days | Feature | Status |
|------|---------|--------|
| 1-2 | Pre-Action Content Checking | 📋 Planned |
| 3-4 | Post-Generation Validation | 📋 Planned |
| 5-6 | Audit Logging System | 📋 Planned |
| 7-9 | Content Filtering System | 📋 Planned |
| 10-11 | Policy Violation Handler | 📋 Planned |
| 12-13 | Compliance Tracking & Reports | 📋 Planned |
| 14 | Settings UI Integration | 📋 Planned |

**Estimated Total**: 14 days (~2 weeks)

---

## Dependencies

### Python Packages (may need to add):
- `regex` - Advanced pattern matching
- `validators` - Email/URL validation
- `python-dateutil` - Date handling for reports

### Existing Services:
- LLMProviderFactory - For semantic analysis
- ContentPolicyService - Base policy definitions
- Logger - For audit logging

---

## Risk Assessment

### High Risk
- **Performance Impact**: Pre-action checking adds latency
  - *Mitigation*: Quick pattern checks first, LLM only if needed

- **False Positives**: Blocking legitimate actions
  - *Mitigation*: Configurable strictness, allow-lists, user feedback

### Medium Risk
- **Storage Growth**: Audit logs can grow large
  - *Mitigation*: Daily rotation, configurable retention, compression

- **Pattern Maintenance**: Regex patterns need updates
  - *Mitigation*: Centralized pattern file, easy configuration

### Low Risk
- **UI Complexity**: Many new settings
  - *Mitigation*: Sensible defaults, clear documentation

---

## Post-Phase 4 Benefits

✅ **Enterprise Ready**: SOC2/ISO 27001 compliance support
✅ **User Safety**: Prevents accidental violations
✅ **Audit Trail**: Complete logging for investigations
✅ **Risk Management**: Early detection and blocking of violations
✅ **Customer Trust**: Demonstrates security commitment
✅ **Policy Flexibility**: Configurable for different use cases
✅ **Metrics & Insights**: Data-driven policy refinement

---

**Created**: 2025-11-04
**Status**: Ready to implement
**Next Step**: Start with Feature 1 (Pre-Action Content Checking)
