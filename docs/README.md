# 📚 Documentation Index

Welcome to the Comprehensive Portfolio Management Platform documentation. This platform delivers complete automation for portfolio management with IBKR integration, Singapore timezone scheduling, and production-ready deployment.

## 🎯 **Project Overview**

This platform achieves **4 core goals** with 100% completion:
1. ✅ **Daily Automated Portfolio Updates** - IBKR standard Excel exports with SharePoint/Email integration
2. ✅ **Order Generation System** - Model portfolio-based order creation with CSV output
3. ✅ **Market Data Platform Separation** - Role-based access control with caching system
4. ✅ **Singapore Timezone Scheduling** - Fully automated daily operations at 6:00/6:30 AM SGT

## 📋 **Documentation Structure**

### 🚀 **Getting Started**
- **[Main README](../README.md)** - Project overview, quick start, and feature summary
- **[Installation Guide](installation.md)** - Step-by-step setup and configuration
- **[Quick Start Tutorial](quick-start.md)** - Get running in 5 minutes

### ⏰ **Automation & Scheduling** 
- **[📋 Scheduler Guide](SCHEDULER_GUIDE.md)** - **COMPLETE** Singapore timezone automation
  - Installation and deployment options (systemd, daemon, cron)
  - Daily workflow automation (6:00 AM market data, 6:30 AM portfolio)
  - Production-ready daemon management
  - Troubleshooting and monitoring
  - Email notifications and error handling

### 📊 **Portfolio Management**
- **[Portfolio Service Guide](portfolio-service.md)** - Multi-account downloads and IBKR integration
- **[IBKR Standard Format](ibkr-format.md)** - Summary/Matrix sheet specifications
- **[Asset Class Mapping](asset-class-mapping.md)** - Universe data integration and classification
- **[Cached Pricing System](cached-pricing.md)** - Offline operations with market data cache

### 🔐 **Security & Access Control**
- **[Role-Based Permissions](role-based-permissions.md)** - Portfolio Manager vs Trade Assistant roles
- **[IBKR Profile Management](ibkr-profiles.md)** - User type configuration and API access
- **[Security Best Practices](security.md)** - Environment variables and credential management

### 🔄 **Integration Services**
- **[SharePoint Integration](sharepoint-integration.md)** - Automated OneDrive uploads with date organization
- **[Email Service](email-service.md)** - Office 365 SMTP integration with HTML templates
- **[Market Data Service](market-data-service.md)** - Caching system and Trade Assistant operations

### 📱 **CLI Reference**
- **[Complete CLI Guide](cli-reference.md)** - All 15+ command-line tools
- **[Scheduler Commands](scheduler-commands.md)** - start-scheduler, scheduler-status, test-scheduler
- **[Portfolio Commands](portfolio-commands.md)** - download-positions-ibkr, download-positions-cached
- **[Order Generation](order-generation.md)** - generate-orders with model portfolios
- **[System Management](system-management.md)** - test-integrations, market-data-status

### 🛠️ **Deployment & Operations**
- **[Production Deployment](production-deployment.md)** - systemd service, daemon scripts
- **[Configuration Management](configuration.md)** - app.yaml, universe data, model portfolios  
- **[Monitoring & Logging](monitoring.md)** - Status checking, log analysis, performance tuning
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

### 🏗️ **Architecture & Development**
- **[System Architecture](architecture.md)** - Service layers, data flow, integration patterns
- **[API Documentation](api.md)** - Service interfaces, data models, method signatures
- **[Data Models](data-models.md)** - Pydantic schemas, validation rules, type safety
- **[Testing Guide](testing.md)** - Unit tests, integration tests, validation procedures

### 💼 **Business Workflows**
- **[Daily Workflow](daily-workflow.md)** - Automated morning routines and processes
- **[Model Portfolios](model-portfolios.md)** - GTAA B301, Peace of Mind B101 configurations
- **[Order Processing](order-processing.md)** - Deposit, withdrawal, rebalancing scenarios
- **[Client Management](client-management.md)** - Multi-account handling and reporting

## 🎯 **Key Features by Documentation**

### Automation Features
| Feature | Documentation | Status |
|---------|---------------|--------|
| Singapore Timezone Scheduling | [SCHEDULER_GUIDE.md](SCHEDULER_GUIDE.md) | ✅ Complete |
| Daily Automated Updates | [daily-workflow.md](daily-workflow.md) | ✅ Complete |
| Error Handling & Notifications | [SCHEDULER_GUIDE.md](SCHEDULER_GUIDE.md) | ✅ Complete |
| Production Daemon Management | [production-deployment.md](production-deployment.md) | ✅ Complete |

### Portfolio Management Features
| Feature | Documentation | Status |
|---------|---------------|--------|
| IBKR Standard Excel Format | [ibkr-format.md](ibkr-format.md) | ✅ Complete |
| Multi-Account Downloads | [portfolio-service.md](portfolio-service.md) | ✅ Complete |
| Asset Class Mapping | [asset-class-mapping.md](asset-class-mapping.md) | ✅ Complete |
| Cached Pricing System | [cached-pricing.md](cached-pricing.md) | ✅ Complete |

### Integration Features  
| Feature | Documentation | Status |
|---------|---------------|--------|
| SharePoint Auto-Upload | [sharepoint-integration.md](sharepoint-integration.md) | ✅ Complete |
| Email Notifications | [email-service.md](email-service.md) | ✅ Complete |
| Role-Based Access Control | [role-based-permissions.md](role-based-permissions.md) | ✅ Complete |
| Market Data Caching | [market-data-service.md](market-data-service.md) | ✅ Complete |

## 🚀 **Quick Navigation by Use Case**

### 👤 **I'm a Portfolio Manager**
- Start here: **[Main README](../README.md)** → **[Quick Start](quick-start.md)**
- Daily operations: **[Daily Workflow](daily-workflow.md)**  
- Portfolio downloads: **[Portfolio Commands](portfolio-commands.md)**
- Order generation: **[Order Generation](order-generation.md)**

### 🔧 **I'm a System Administrator**  
- Start here: **[Production Deployment](production-deployment.md)**
- Automation setup: **[SCHEDULER_GUIDE.md](SCHEDULER_GUIDE.md)**
- Monitoring: **[Monitoring & Logging](monitoring.md)**
- Troubleshooting: **[Troubleshooting Guide](troubleshooting.md)**

### 👨‍💻 **I'm a Developer**
- Start here: **[System Architecture](architecture.md)**
- API reference: **[API Documentation](api.md)**
- Testing: **[Testing Guide](testing.md)**
- Contributing: **[Development Guide](development.md)**

### 🎯 **I'm Setting Up Market Data**
- Start here: **[Market Data Service](market-data-service.md)**
- Caching system: **[Cached Pricing System](cached-pricing.md)**
- Role configuration: **[Role-Based Permissions](role-based-permissions.md)**

## 📊 **Documentation Status**

| Section | Coverage | Last Updated |
|---------|----------|--------------|
| **Core Features** | 100% Complete | 2025-09-06 |
| **Scheduler System** | 100% Complete | 2025-09-06 |
| **CLI Reference** | 100% Complete | 2025-09-06 |
| **Integration Guides** | 100% Complete | 2025-09-06 |
| **Deployment Guides** | 100% Complete | 2025-09-06 |
| **API Documentation** | In Progress | TBD |
| **Advanced Configurations** | In Progress | TBD |

## 🤝 **Contributing to Documentation**

We welcome contributions to improve our documentation:

1. **Identify gaps**: Missing information or unclear sections
2. **Submit improvements**: Create pull requests with documentation updates  
3. **Follow standards**: Use consistent formatting and structure
4. **Add examples**: Include practical code examples and use cases

### Documentation Standards
- **Clear headings**: Use descriptive section titles
- **Code examples**: Include working code snippets
- **Screenshots**: Add visual guides where helpful
- **Cross-references**: Link related documentation sections
- **Keep updated**: Maintain accuracy with latest features

## 📞 **Getting Help**

- **📋 Start with**: [SCHEDULER_GUIDE.md](SCHEDULER_GUIDE.md) for comprehensive setup
- **🔍 Search issues**: Check existing GitHub issues for known problems
- **💬 Ask questions**: Create new GitHub issues for support
- **📧 System alerts**: Automated email notifications for operational issues

---

**Last Updated**: 2025-09-06  
**Platform Version**: v2.0 - Complete Automation Platform  
**Documentation Maintainer**: GenSpark AI Developer Team