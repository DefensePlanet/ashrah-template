# Decisions Log (Architecture/Process)

## 2025-08-10 Context Preservation Over Master Agent
- **Context:** Need to preserve Builder system knowledge between Claude Code sessions
- **Options considered:** 
  1. Full Master Agent with MCP server and analysis capabilities
  2. nano-agent integration with multi-model routing
  3. Simple context files with structured documentation
- **Decision:** Implement simple context preservation system with markdown files
- **Rationale:** 
  - Solves 90% of context loss problem with zero complexity
  - No additional infrastructure or costs required
  - Human-readable and version-controllable
  - Can evolve into smarter systems later if needed
- **Impact:** Created global/ context files, eliminates session context loss

## 2025-08-10 Defer nano-agent Integration  
- **Context:** Evaluated nano-agent framework for multi-model optimization
- **Options considered:**
  1. Immediate integration for cost/speed optimization
  2. Defer until proven need emerges
  3. Alternative multi-model solutions
- **Decision:** Defer nano-agent integration to Phase 2
- **Rationale:**
  - Builder system is production-ready, optimization is premature
  - Current Claude Code integration works well without pain points
  - Integration complexity could destabilize working system
  - Cost/speed optimization valuable but not urgent
- **Impact:** Focus remains on core value delivery, nano-agent bookmarked for later

## 2025-08-10 Test Environment Complete Isolation
- **Context:** Test capsules were contaminating production metrics and directories
- **Options considered:**
  1. Mixed environment with naming conventions
  2. Complete separation with production guards
  3. Separate testing instances
- **Decision:** Complete isolation with production write guards
- **Rationale:**
  - Clean separation prevents metric contamination
  - Production guards prevent accidental writes to production directories
  - Isolated testing environment ensures test integrity
- **Impact:** 18 test capsules moved to testing/, production guard implemented

## 2025-08-10 Lane Detection Priority System
- **Context:** Conflicts between capsule.json and requirements.yaml lane specification
- **Options considered:**
  1. requirements.yaml only
  2. capsule.json only  
  3. Priority system with fallbacks
- **Decision:** capsule.json > requirements.yaml > standard default
- **Rationale:**
  - capsule.json is more explicit and Builder-specific
  - requirements.yaml provides fallback for legacy capsules
  - standard default ensures safety for business-critical work
- **Impact:** Consistent lane detection across all Builder components

## 2025-08-09 Two-Lane Workflow Model
- **Context:** Need different quality standards for personal vs business automation
- **Options considered:**
  1. Single workflow for all projects
  2. Multiple specialized workflows per domain
  3. Two-lane system (fast/deep)
- **Decision:** Two-lane workflow with standard and standard
- **Rationale:**
  - Balances simplicity with appropriate quality standards
  - standard enables rapid personal automation
  - standard ensures business-grade validation
  - Clear mental model for users
- **Impact:** Core architectural pattern throughout Builder system

## 2025-08-09 Definition of Done (DoD) Integration
- **Context:** Need consistent quality gates for different project types
- **Options considered:**
  1. Universal DoD checklist
  2. Lane-specific DoD validation
  3. Project-specific DoD files
- **Decision:** Lane-specific DoD with automatic validation
- **Rationale:**
  - Different lanes require different quality standards
  - Automated validation reduces human error
  - Lane-aware prompt discovery enhances AI assistance
- **Impact:** DoD validation integrated throughout planner system

## 2025-08-08 Daily Audit Automation
- **Context:** Need consistent system health monitoring and maintenance
- **Options considered:**
  1. Manual system checks
  2. Comprehensive monitoring system
  3. Daily audit with LaunchAgent automation
- **Decision:** Daily audit system with automated scheduling
- **Rationale:**
  - Proactive issue detection prevents system degradation
  - LaunchAgent provides reliable macOS scheduling
  - Desktop notifications ensure visibility
  - Metrics refresh keeps dashboard current
- **Impact:** Automated daily health monitoring at 9:10 AM