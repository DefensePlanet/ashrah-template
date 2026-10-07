# Builder System Demo Capsules

**Version:** 1.0  
**Last Updated:** 2025-08-11  
**Purpose:** Low-effort, high-demo-value capsules for pipeline validation

---

## 🎯 **Selection Criteria**

**Low Effort:**
- ≤4 hours development time
- Minimal external dependencies  
- Uses existing Builder templates/agents
- Straightforward requirements

**High Demo Value:**
- Showcases Builder's core capabilities
- Demonstrates lane differences (fast vs deep)
- Validates agent routing and MCP integration
- Produces tangible, shareable output

---

## 🤖 **Automation Pack Demos**

### **1. Instagram Carousel Generator** ⭐ **TOP PRIORITY**
**Effort:** 2-3 hours | **Lane:** standard | **Agent:** automation-specialist

**What it does:**
- Reads CSV data (products, tips, quotes, etc.)
- Generates Instagram carousel images using template
- Auto-posts to Instagram via API or saves for manual upload
- Logs success/failure for each post

**Demo Value:**
- Shows CSV → Visual Content pipeline  
- Demonstrates n8n workflow automation
- Real social media output people can use
- Perfect standard validation (quick iteration, minimal docs)

**Implementation:**
```bash
python3 tools/create_role_pack.py automation instagram-carousel standard
# Auto-routes to automation-specialist with n8n + AppleScript tools
# CSV input → n8n workflow → Instagram API → Posted carousels
```

### **2. Daily Standup Aggregator**
**Effort:** 1-2 hours | **Lane:** standard | **Agent:** automation-specialist

**What it does:**  
- Scrapes Slack/Discord messages from team channels
- Summarizes daily progress updates
- Generates formatted standup report
- Emails/posts summary to project channel

**Demo Value:**
- Real workplace automation utility
- Shows text processing + communication integration
- Validates API integration capabilities

### **3. macOS Productivity Dashboard**  
**Effort:** 3-4 hours | **Lane:** standard | **Agent:** automation-specialist

**What it does:**
- Tracks app usage, screen time, focus sessions
- Integrates with Calendar for meeting analysis  
- Generates daily/weekly productivity insights
- Creates AppleScript shortcuts for common tasks

**Demo Value:**
- Personal utility everyone can use
- Showcases macOS automation capabilities
- Demonstrates data collection + visualization

---

## 🌐 **Web Development Pack Demos**

### **4. One-Sentence Website Generator** ⭐ **TOP PRIORITY**
**Effort:** 3-4 hours | **Lane:** standard | **Agent:** frontend-specialist

**What it does:**
- Takes single sentence description of desired website
- Generates complete static site with shadcn/ui components
- Deploys to Vercel/Netlify with custom domain
- Includes responsive design, SEO basics, contact form

**Demo Value:**
- "Magic" user experience (sentence → live website)
- Shows AI-powered content generation
- Demonstrates full deployment pipeline
- Perfect for non-technical users

**Implementation:**
```bash
python3 tools/create_role_pack.py webdev sentence-site frontend standard
# Input: "I need a portfolio website for my photography business"
# Output: Live website at custom domain with gallery, contact, about pages
```

### **5. Local Business Landing Page**
**Effort:** 2-3 hours | **Lane:** standard | **Agent:** frontend-specialist + security-auditor

**What it does:**
- Takes business info (name, services, location, hours)
- Generates professional landing page with booking/contact forms
- Includes local SEO optimization, Google Maps integration
- Security hardened, performance optimized

**Demo Value:**
- Real business value (immediately usable)
- Shows standard vs standard differences
- Demonstrates security audit integration
- Validates full DoD process

### **6. Personal Dashboard Aggregator**
**Effort:** 4 hours | **Lane:** standard | **Agent:** frontend-specialist + backend-architect

**What it does:**
- Aggregates data from multiple APIs (weather, news, calendar, fitness)
- Creates personalized dashboard with widgets
- Real-time updates, customizable layout
- Mobile-responsive with PWA capabilities

**Demo Value:**
- Shows full-stack capabilities  
- Demonstrates API integration complexity
- Personal utility with broad appeal

---

## 🍎 **Apple Apps Pack Demos**

### **7. Menu Bar System Monitor**
**Effort:** 3-4 hours | **Lane:** standard | **Agent:** macos-specialist + security-auditor  

**What it does:**
- Lives in macOS menu bar with minimal footprint
- Shows system stats (CPU, memory, disk, network)
- Customizable alerts and notifications
- App Store ready with proper sandboxing

**Demo Value:**
- Native macOS utility everyone needs
- Shows App Store deployment pipeline
- Demonstrates security audit integration
- Perfect standard validation

### **8. iOS Expense Tracker**
**Effort:** 4+ hours | **Lane:** standard | **Agent:** ios-specialist + test-automator

**What it does:**
- Simple expense tracking with categories
- Receipt photo capture and OCR
- iCloud sync between devices
- Widget support for quick entry

**Demo Value:**
- Real-world iOS app utility
- Shows mobile development capabilities
- Demonstrates testing automation
- App Store submission ready

---

## 🔗 **Cross-Pack Integration Demos**

### **9. Social Media Command Center** ⭐ **ADVANCED DEMO**
**Effort:** 6-8 hours | **Lane:** standard | **Multi-agent:** automation + web + security

**What it does:**
- Web dashboard for managing multiple social accounts
- Automated posting schedules via n8n workflows  
- Content generation from RSS/news feeds
- Analytics dashboard with engagement metrics

**Demo Value:**
- Shows multi-agent collaboration
- Demonstrates complex workflow orchestration
- Real business application
- Tests parallel capsule capabilities

### **10. Personal Assistant Ecosystem**
**Effort:** 8+ hours | **Lane:** standard | **Multi-agent:** automation + apple + web

**What it does:**
- macOS/iOS apps for task management and reminders
- Web dashboard for family/team coordination
- Automated workflows for common tasks
- Voice integration with Shortcuts app

**Demo Value:**
- Comprehensive system demonstration
- Shows all role packs working together
- High personal utility value
- Tests full Builder pipeline

---

## 📊 **Implementation Priority Matrix**

| Capsule | Effort | Demo Value | Agent Coverage | Priority |
|---------|--------|------------|----------------|----------|
| Instagram Carousel | Low | High | automation-specialist | **🔥 P0** |
| One-Sentence Website | Low | High | frontend-specialist | **🔥 P0** | 
| Menu Bar Monitor | Medium | High | macos-specialist | **⚡ P1** |
| Daily Standup | Low | Medium | automation-specialist | **⚡ P1** |
| Business Landing Page | Medium | High | multi-agent | **⚡ P1** |
| Personal Dashboard | High | Medium | multi-agent | P2 |
| iOS Expense Tracker | High | Medium | ios-specialist | P2 |
| Productivity Dashboard | Medium | Medium | automation-specialist | P2 |
| Social Media Center | Very High | Very High | multi-agent | P3 |
| Assistant Ecosystem | Very High | Very High | multi-agent | P3 |

---

## 🚀 **Recommended Build Sequence**

### **Phase 1: Core Validation (Week 1)**
1. **Instagram Carousel Generator** - Validates automation pack + standard
2. **One-Sentence Website** - Validates web pack + AI integration
3. **Menu Bar Monitor** - Validates apple pack + standard

### **Phase 2: DoD Validation (Week 2)**  
4. **Business Landing Page** - Tests standard DoD process
5. **Daily Standup Aggregator** - Additional automation validation
6. **Personal Dashboard** - Full-stack web validation

### **Phase 3: Advanced Integration (Week 3+)**
7. **iOS Expense Tracker** - Mobile development pipeline
8. **Social Media Command Center** - Multi-agent coordination
9. **Personal Assistant Ecosystem** - Complete system validation

---

## 📋 **Success Metrics per Demo**

### **Technical Metrics**
- **Creation Time**: Template → working prototype
- **Agent Routing Accuracy**: Correct specialist assignment  
- **MCP Grant Validation**: No excessive permissions
- **DoD Compliance**: Lane-appropriate quality gates

### **Business Metrics**  
- **User Value**: Could someone actually use this?
- **Demo Impact**: Does it showcase Builder capabilities?
- **Shareability**: Can we show this to others confidently?
- **Learning Value**: What did we learn about Builder?

### **System Metrics**
- **Memory Usage**: MCP server performance
- **Context Persistence**: Session-to-session continuity
- **Error Handling**: Graceful degradation
- **Event Logging**: Complete observability

---

These demo capsules provide a comprehensive validation path for Builder System capabilities while producing genuinely useful outputs that demonstrate real-world value.