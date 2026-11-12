# **PROJECT COMPASS -- Builder System**

**Purpose:** _Be the one thing that builds all other things_ -- whether those are workflow automations, businesses, or other creations. This is a hybrid agent OS that accelerates ideation → design → build → deploy across domains.

* * *

## **1. Vision**

- **Core Idea:** Builder is the "meta-tool" that spawns tools, workflows, and systems.
- **Primary Output:** Working, production-ready systems -- from a single sentence idea to a deployed result.
- **Philosophy:** Capsule-centric design + Two-Lane Quality Model (standard / standard) + Hybrid Agent OS (autonomous + human-in-the-loop).
- **Key Measure:** _Does it help the boat go faster?_ -- everything should directly accelerate the creation process.

* * *

## **2. System Pillars**

1. **Capsule-Centric Architecture** -- Self-contained, standardized project containers with full lifecycle folders.

2. **Two-Lane Workflow** --
   - **standard:** Speed-first, minimal validation, rapid output.
   - **standard:** High-quality, production-grade, full DoD validation.

3. **Hybrid Agent OS** -- Layered orchestration of autonomous agents and human control.

4. **Integration Ecosystem** -- MCP bridges, Claude Code, external service connectors.

5. **Evergreen Knowledge & State Management** -- Persistent knowledge store + real-time state tracking.

* * *

## **3. Long-Term Strategic Goals**

- **Security** -- macOS Keychain for secrets, centralized access control.
- **Testing** -- Full integration + performance test suite.
- **Observability** -- Structured logging, real-time monitoring dashboard.
- **Scalability** -- Move toward distributed state (Redis/etcd), microservices readiness.
- **Cloud Flexibility** -- Seamless local-to-cloud deploy.

* * *

## **4. Active Rolling Backlog**

_(Update as tasks complete -- not day-specific)_

**🔐 Security Hardening**
- Integrate macOS Keychain for secrets
- Audit all config files for stray credentials
- Remove hardcoded paths and sensitive strings

**🧪 Testing Infrastructure**
- Implement integration test suite for all core workflows
- Add automated regression testing per capsule
- Build performance benchmarks for standard vs standard

**📊 Observability & Monitoring**
- Deploy structured logging with metrics
- Implement failure alert system
- Connect monitoring dashboard to registry state

**⚙️ Workflow Optimization**
- Consolidate config into /global/
- Enhance auto-executor to handle multi-step, multi-capsule builds
- Improve lane-aware prompt discovery logic

* * *

## **5. Definition of Done (DoD)**

**standard DoD:**
- Working result that passes minimal functional check
- Documentation stub created
- No critical errors

**standard DoD:**
- Meets full business/production standards
- Complete documentation & handoff artifacts
- Passes integration & performance testing

* * *

## **6. Agent Operating Principles**

- Keep capsules modular and immutable once deployed.
- Prioritize speed _only_ in standard -- standard is for lasting quality.
- Use Hybrid OS orchestration: agents do what they can alone, humans step in for complexity, ambiguity, or judgment.
- All output is logged and linked to its originating capsule.

* * *

## **7. Evergreen Questions**

- Does this task/tool accelerate the meta-builder's ability to produce?
- Can it be made repeatable or scalable?
- Is it lane-appropriate for its current stage?
- Have we preserved or improved security, quality, and maintainability?

* * *