# Scenario Editor Guide

## Overview

The Scenario Editor allows you to fully customize AI-generated scenarios before starting war games. This gives you complete control over your training content.

## Accessing the Editor

After generating a scenario in the **Scenario Builder**, click the **"✏️ Customize Scenario"** button.

## Editor Tabs

### 1. 🏢 Organization
Customize basic organization details:
- **Name**: Company/organization name
- **Industry**: Financial, Healthcare, Tech, etc.
- **Size**: Small, Medium, Large, Enterprise
- **Security Posture**: Weak, Developing, Mature, Advanced
- **Description**: Full organization description

### 2. 🏬 Departments
Manage business departments:
- **Edit**: Name, description, business function, data classification
- **Add**: Create new departments with custom details
- **Delete**: Remove departments you don't need
- Each department links to systems

### 3. 💻 Systems
Manage IT infrastructure:
- **Edit**: System name, type, OS, criticality level
- **Add**: Create servers, workstations, databases, cloud services, etc.
- **Delete**: Remove unnecessary systems
- **Types**: server, workstation, database, web-application, cloud-service, network-device
- **Criticality**: low, medium, high, critical

### 4. 🔓 Vulnerabilities
Customize security weaknesses:
- **Edit**: Name, description, severity, CVE ID, exploitability
- **Add**: Create custom vulnerabilities
- **Delete**: Remove vulnerabilities
- **Severity**: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low
- **CVE Support**: Optional CVE ID field

### 5. 👤 Threat Actors
Manage adversaries:
- **Edit**: Name, description, motivation, sophistication
- **TTPs**: Edit tactics, techniques, procedures (one per line)
- **Add**: Create custom threat actors
- **Delete**: Remove threat actors
- **Motivations**: financial, espionage, hacktivism, nation-state, insider
- **Sophistication**: low → nation-state

### 6. 🎯 Game Objectives
Define training goals:
- **Edit**: Modify objective descriptions
- **Add**: Create custom objectives
- **Delete**: Remove objectives
- **Suggested Objectives**: 8 pre-written objectives for quick setup
  - Identify initial infection vector
  - Contain threat within 30 minutes
  - Preserve critical systems
  - Collect forensic evidence
  - And more...

## Workflow

### Basic Flow
1. **Generate** a scenario in Scenario Builder
2. **Customize** in Scenario Editor
3. **Save & Start War Game**

### Advanced Flow
1. Generate base scenario
2. **Customize** extensively (add/remove/edit all elements)
3. **Save & Continue** to review
4. **Start War Game** when ready
5. Or **Revert All Changes** if needed

## Action Buttons

- **↩️ Revert All Changes**: Reset to original AI-generated scenario
- **💾 Save & Continue**: Save changes and stay in editor
- **🎮 Save & Start War Game**: Save and immediately begin playing
- **❌ Cancel**: Discard changes and return to Scenario Builder

## Tips

### Making Small Changes
- Edit just what you need (e.g., change org name)
- Save that tab
- Start the war game

### Creating Custom Scenarios
- Start with AI-generated base
- Delete unwanted elements
- Add your own departments/systems/vulnerabilities
- Define specific learning objectives
- Save and play

### Reusing Scenarios
- Customize once
- Save via Scenario Builder
- Load and re-customize for different training sessions

### Objectives Best Practices
- Keep objectives specific and measurable
- Mix technical and procedural objectives
- Include time-based objectives for urgency
- Add communication/escalation objectives

## Integration with War Game

Customized scenarios work seamlessly with the war game:
- **Objectives** appear in the sidebar during gameplay
- **Threat Actors** drive AI Game Master behavior
- **Vulnerabilities** influence incident scenarios
- **Systems** provide realistic context
- **Departments** affect scope and impact

## Examples

### Example 1: Focus on Specific Vulnerability
1. Generate healthcare scenario
2. Go to Vulnerabilities tab
3. Delete unrelated vulnerabilities
4. Keep only ransomware-related CVEs
5. Add custom objective: "Prevent patient data encryption"
6. Start game focused on ransomware response

### Example 2: Custom Organization
1. Generate base scenario
2. Organization tab: Change to your actual company name
3. Departments tab: Match your real org structure
4. Systems tab: Add your actual critical systems
5. Objectives tab: Add company-specific goals
6. Train on realistic scenario

### Example 3: Simplified Training
1. Generate complex scenario
2. Delete half the departments
3. Remove low-severity vulnerabilities
4. Keep only 1-2 threat actors
5. Set 3 basic objectives
6. Easier scenario for beginners

## Keyboard Shortcuts

- **Enter**: Submit forms
- **Tab**: Navigate between fields
- **Escape**: Cancel form input

## Data Persistence

- Changes saved to session state (temporary)
- Click "Save & Continue" or "Save & Start War Game" to persist
- Original scenario preserved until you save
- Can revert at any time before saving

## Future Enhancements

Coming soon:
- Export/Import custom scenarios
- Scenario templates library
- Collaboration (share customizations)
- Version control for scenarios
- AI-assisted customization suggestions

---

**Need Help?** Return to Scenario Builder or check the sidebar tips in the editor.
