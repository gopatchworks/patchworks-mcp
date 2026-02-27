# Patchworks Product Documentation Knowledge Base

---

## 1. Getting Started

**Source:** https://doc.wearepatchworks.com/product-documentation/getting-started/getting-started-introduction

After registering and logging into the Patchworks dashboard, users can begin syncing data between business systems using two approaches: the traditional services method or the newer process flows system.

**User Timeline Distinction:**
- Accounts created before July 2023 use services and may optionally upgrade to process flows by contacting their Customer Success Manager or emailing customersuccess@wearepatchworks.com
- Accounts created after July 2023 automatically use process flows

### Process Flows
Process flows represent an advanced tool for defining flexible data exchange workflows between connector instances. The system employs a drag-and-drop interface where users position shapes on a canvas and configure them according to their requirements. The documentation recommends consulting the Patchworks quickstart guide for foundational knowledge, followed by reviewing the dedicated process flows section for comprehensive details.

### Services (Legacy)
Existing customers familiar with the legacy approach use services to exchange data between system connectors. Those preferring to continue with this method can reference the services documentation section rather than migrating to process flows.

### Sub-Topics
- Core subscription tiers
- Key concepts & terminology
- Multi-language support
- Patchworks quickstart guide
- Patchworks infrastructure

---

## 2. Registration

**Source:** https://doc.wearepatchworks.com/product-documentation/registration/registering-for-a-patchworks-account

Upon registering, users receive a dashboard instance with complete access during a 14-day trial period.

### Registration Process

1. **Request a trial account** by clicking the provided link to access Patchworks' free trial offer page.
2. **Submit request details** by completing the trial request form with necessary information.
3. **Schedule a meeting** with the Patchworks Sales team to book an available time slot.
4. **Enter contact information** by completing a form with company details. The email provided becomes the Patchworks point of contact for the company.

### After Registration
Following the sales team meeting, a trial account is provisioned and login credentials are sent to the registered email address. By default, this account has admin-level permissions.

User accounts within Patchworks are assigned roles that determine dashboard access levels, which may vary based on the active subscription tier.

### Multi-Company Profiles
Patchworks partners managing multi-company profiles may add linked company profiles after their primary company profile is established.

### Additional Registration Topics
- Password control
- Two-factor authentication (2FA)
- SSO (Single Sign-On)
- Azure AD / Entra
- Okta
- PingOne

---

## 3. Core Subscription Tiers

**Source:** https://doc.wearepatchworks.com/product-documentation/getting-started/core-subscription-tiers

Patchworks offers multiple subscription tiers designed to accommodate different organizational needs, ranging from basic functionality to advanced data flow capabilities.

### Available Tiers

| Tier | Description |
|------|-------------|
| **Trial** | 15-day free period with complete feature access following account registration |
| **Blueprint Store** | For users accessing pre-built blueprints exclusively; access is primarily read-only |
| **Standard** | Full access to standard features; advanced capabilities are view-only; limited connectors/flows |
| **Professional** | Full access to standard and advanced features; higher limits for connectors and flows |
| **Custom** | Comprehensive access with customized limits tailored to specific organizational requirements |

### Key Feature Allowances

| Feature | Trial | Blueprint Store | Standard | Professional | Custom |
|---------|-------|-----------------|----------|--------------|--------|
| Deployed connectors | 2 | Read-only | 2 | 4 | Custom |
| Active process flows | 2 | Limited | 10 | 20 | Custom |
| Monthly operations | 10,000 | 150,000 | 250,000 | 500,000 | Custom |
| Concurrent flows | 1 | 10 | 10 | 20 | 30+ |
| Webhooks/minute | 2 | Limited | 0 | 120 | 120+ |

### Advanced Features
Professional and certain Standard users (with add-ons) access: cache management, de-duplication, custom scripts, webhooks, event connectors, and the Patchworks API.

### Bolt-On Enhancements
Organizations can purchase additional capabilities including advanced features, connector additions, process flow expansions, webhook capacity increases, callback functionality, partner features, and enhanced rate limits.

### Allowance Refresh Cycles
Monthly allowances reset at the calendar month's beginning, while daily allowances reset every 24 hours.

---

## 4. Patchworks Quickstart Guide

**Source:** https://doc.wearepatchworks.com/product-documentation/getting-started/patchworks-quickstart-guide

Patchworks offers two implementation paths for new clients:
1. **Custom integrations** with Patchworks team assistance for tailored solutions
2. **Self-serve integrations** through the Patchworks dashboard

### Step 1: Registration
Users can register at https://app.wearepatchworks.com/register using either Google sign-in or username/password credentials.

**Partner Note:** Patchworks partners managing multiple company profiles should have the partner features bolt-on enabled, allowing creation of separate company profiles for managed organizations.

### Step 2: Company Setup
Standalone companies require no additional setup. Organizations needing to manage linked companies (with partner features enabled) can establish separate company profiles from their primary account.

### Step 3: User Setup
Initial registration creates an admin account by default. Admin users can create additional team member accounts with either:
- **Admin privileges** for creating and managing process flows
- **User permissions** for view-only access

### Step 4: Flow Setup
Two approaches exist for creating process flows:

**Auto Setup via Blueprints:** A blueprint includes everything needed to sync data between two systems -- connectors, instances, process flows, scripts, and cross-reference lookups. Blueprints purchased from the Patchworks store come with installation instructions and are ready for testing and deployment.

**Manual Setup:** Organizations manually add connectors, instances, flows, scripts, and lookups. The Patchworks marketplace offers prebuilt components available for installation or customization. Organizations lacking prebuilt connectors can use the connector builder to develop custom solutions.

### Step 5: Day-to-Day Management
Active process flows execute automatically according to defined trigger settings. Users can alternatively run a process flow manually, with instant feedback and real-time logging. Detailed run logs provide complete data oversight and can be reviewed retrospectively.

---

## 5. Company Setup (Company Profiles)

**Source:** https://doc.wearepatchworks.com/product-documentation/company-management/about-company-profiles

Upon creating a Patchworks account, your organization receives a company profile where you can access and update foundational organizational information including name and contact details, plus manage user accounts.

The individual who initially registers the company automatically receives administrator access to the dashboard -- this is the highest level of access that can be associated with a company profile.

For agencies or partner organizations managing multiple company accounts, the functionality operates differently -- consult the dedicated Multi-company profiles documentation for specifics.

### Sub-Topics
- Accessing your company profile
- Adding & managing company profile banners
- Multi-company profiles
- Company insights

---

## 6. Users, Roles & Permissions

**Source:** https://doc.wearepatchworks.com/product-documentation/users-roles-and-permissions/roles-and-permissions-summary

### Core Concept
The Patchworks platform implements a role-based access control system with four user roles: **Administrator**, **Manager**, **User**, and **Read-only**. A critical principle: "tier trumps role" -- meaning subscription tier determines actual feature availability regardless of assigned permissions.

### Role Assignment
New account registrants automatically receive the Administrator role, with authority to create additional users and assign roles. Typically one administrator per organization; multiple administrator accounts require support approval.

### Permission Framework

**Company Management:**
- Administrators control company profile name and deletion
- Administrators and Managers can update contact information and manage banner messages
- All four roles can view company profiles

**User Administration:**
- Administrators and Managers create and manage users with lower roles
- Only Patchworks Support can create Administrator-level accounts or promote/demote Administrator users
- Managers cannot create other Manager accounts -- only Administrators can
- All roles can enable/disable their own multi-factor authentication

**Marketplace & Resources:**
- Administrators and Managers install blueprints, connectors, and process flows
- Only Administrators build blueprints
- All roles can browse marketplace content

**Process Flows & Development:**
- Administrators and Managers exclusively create, modify, and delete process flows
- Administrators and Managers enable/deploy flows
- All roles can view existing flows

**Data Management:**
- Administrators and Managers manage custom scripts, cross-reference lookups, and caches
- All roles can view these resources

**API Access:**
- Administrators and Managers generate and manage API keys
- All roles can access the API itself

### Additional User Management Topics
- Viewing all users for your company profile
- Creating a new user account for your company profile
- Updating general details for an existing user account
- Updating the role for an existing user account
- Triggering a password reset for another user
- Managing your own user account
- Managing team members & users for multi-company profiles

---

## 7. Marketplace

**Source:** https://doc.wearepatchworks.com/product-documentation/marketplace/the-patchworks-marketplace

### Overview
The Patchworks marketplace functions as a centralized hub where users can discover and deploy various pre-built resources to enhance their dashboard integration capabilities.

### Available Resources
The marketplace offers five main categories of installable resources:
- Connectors
- Process flows
- Custom scripts
- Cross-reference lookups
- Blueprints

### How to Access
1. Sign into the Patchworks dashboard at app.wearepatchworks.com/login
2. Select "marketplace" from the left navigation menu

### Additional Features
Users with appropriate permissions can access a private marketplace option for personalized resources.

### Sub-Topics
- Marketplace blueprints
- Marketplace connectors
- Marketplace process flows
- Marketplace scripts
- Marketplace cross-reference lookups
- The notification centre
- Public marketplace submissions (apps/blueprints and connectors)
- Private marketplaces (accessing, uploading resources)

---

## 8. Blueprints

**Source:** https://doc.wearepatchworks.com/product-documentation/blueprints

### Core Concepts
A blueprint includes everything needed to sync data between two systems. All connectors used in process flows are installed with the blueprint. Prior to installation, you can choose to add required connector instances or install the connectors and add instances later. To use connectors in process flows, you must add an instance of each -- this is where you provide authentication credentials for the associated third-party system.

### Blueprint Installation
Once installed, all blueprint components (connectors, process flows, scripts, etc.) are added to the relevant area of your Patchworks dashboard. When a blueprint is installed, its process flows are disabled and set to a draft status. When ready, you should enable and deploy any process flows that you want to use.

Blueprints are added to your dashboard marketplace within 24 hours of purchase. Your Patchworks subscription tier determines the number of process flows and connectors that you can deploy.

### Available Pre-Built Blueprints
- Lightspeed X-Series & Shopify
- SEKO Logistics & Shopify
- Shopify & Brightpearl (15+ process flows covering locations, products, orders, inventory, fulfillment, payments, pricing)
- Shopify & Descartes Peoplevox
- Shopify & NetSuite (13+ process flows, 6-stage installation guide)
- Shopify & Virtualstock Supplier (8-stage installation guide)
- Veeqo & TikTok

### Blueprint Management
- Private blueprint management (creation, installation, updates, versions, deletion)
- Blueprint rollout procedures

---

## 9. Connectors & Instances

**Source:** https://doc.wearepatchworks.com/product-documentation/connectors-and-instances/connectors-and-instances-introduction

### Connectors
A connector is a generic integration of a third-party business system/application. It contains everything needed "under the hood" (endpoints, authentication methods, etc.) to sync data from/to the associated application. When you install a connector, you are installing a package of generic configuration and setup. You only need to install a given connector once. After that, you can add as many instances of it as you need for use in your process flows.

The Patchworks development team maintains all prebuilt connectors in the marketplace. If you have installed a connector, updates may become available in the marketplace -- you can decide if/when you apply them.

### Instances
An instance is the mechanism used to configure a connector for your own use in process flows. Instances are added to process flows via the connection shape. Every instance requires authentication credentials that allow you to access the associated third-party application. An instance of a connector is unique to your company, personalized with your own credentials and settings.

Typically, you will create one instance for each set of credentials that you have for a given connector that you want to use in process flows.

### The Relationship
If you update an installed connector, that update is applied to all associated instances automatically.

### Practical Examples
- **Simple setup**: One UK Shopify store syncing orders to NetSuite requires one Shopify connector instance and one NetSuite connector instance
- **Complex setup**: Three Shopify stores (UK, EU, US) each with separate credentials require three Shopify connector instances but only one NetSuite connector instance

### Event Connectors
Event connectors are a different sort of connector, used to configure listeners for message brokers such as RabbitMQ.

### Prebuilt Connectors
The documentation lists over 150 prebuilt connectors covering major platforms across e-commerce, logistics, marketing, accounting, and communication categories (Shopify, BigCommerce, Adobe Commerce, NetSuite, etc.).

### Connector Management
- Accessing, installing, updating, and removing connectors
- Instance management: accessing, adding, updating, and removing instances

---

## 10. Process Flows

**Source:** https://doc.wearepatchworks.com/product-documentation/process-flows

### Overview
In their simplest form, process flows receive data from one third-party application and send it to another, perhaps with data manipulation in between. Process flows allow you to build highly complex flows with multiple routes and conditions.

### Key Components

**Trigger:** Every process flow starts with a trigger that determines when the flow should run. Trigger options are defined using the trigger shape. When a new process flow is created, a trigger shape is added with an hourly schedule by default. Trigger shapes cannot be moved or deleted, but settings can be changed.

**Data Source:** A data source is defined by adding a connection shape and selecting a connector instance and endpoint.

**Filters:** Optional refinement layer using the filter shape to narrow the payload before further processing.

**Custom Scripts:** Advanced custom coding capability for complex payload manipulation using the script shape. Typically unnecessary for standard integrations.

**Field Mappings:** Maps source data fields to destination locations with optional transformation functions or custom scripts for value manipulation.

**Data Destination:** Specifies the receiving application with installed connectors and configured instances.

### The Process Flow Canvas
The canvas is where you build and test process flows visually. This is where you define if, when, what, and how data is synced.

### Process Flow Shapes

**Standard shapes:** assert, branch, connector, filter, map, notify, route, split, trigger, flow control

**Advanced shapes:** cache, de-dupe, script, callback

### Dynamic Variables
- Payload variables
- Metadata variables
- Flow variables -- provide the ability to define variables at the process flow level and reference them throughout the entire flow

### Transform Functions
Extensive coverage of transformation capabilities including array, date, number, string, and other functions for field mapping, plus specialized functions like cache lookup, boolean casting, and custom transformations.

### Management & Operations
- Deployment strategies (with/without virtual environments)
- Flow enablement and configuration
- Process flow labels and duplication
- Error handling and logging
- Cross-reference lookup integration
- Email notifications for failed process flow runs

### Process Flow Versioning
Process flows support three version states: draft, deployed, and inactive.

### Troubleshooting
- Common issues like editing problems, runtime failures
- Large payload handling
- Webhook connector errors
- System offline scenarios

---

## 11. Virtual Environments

**Source:** https://doc.wearepatchworks.com/product-documentation/virtual-environments/about-virtual-environments

### Core Concept
Virtual environments enable enterprises to manage multiple stores and brands within a single Patchworks account without duplicating process flows across testing, staging, and production environments.

### The Problem Addressed
Organizations operating multiple storefronts face significant management challenges. For example, an international retailer with five country-specific Shopify stores (each requiring sandbox and live versions) would need 10 connector instances. Combined with five essential process flows, this creates 50 separate flows requiring individual updates.

### The Solution
Rather than maintaining duplicate flows, users create "master" process flows and apply environment-specific overrides through virtual environments. Each virtual environment is configured with the required overrides so components get replaced during deployment.

### Configurable Replacements
Virtual environments support overrides for:
- Connector instances
- Data pools
- Cross-reference lookups
- Scripts
- Company caches
- Flow variables
- Flow queue priority

### Deployment at Scale
Single flows deploy directly from the canvas, while multiple flows benefit from "packages" that bundle process flow versions with target environments, enabling batch deployments in one operation.

### Flow Versioning with Virtual Environments
- A process flow will only ever have ONE draft version
- Only ONE version of a process flow can be deployed to a given virtual environment
- Multiple versions of the same process flow can be deployed to different virtual environments
- A flow version can be deployed to a single virtual environment, to multiple virtual environments, or to no virtual environment

### Availability
The feature is included across all subscription tiers, with a default allowance of two virtual environments. Additional environments require contacting the sales team.

---

## 12. General Settings

**Source:** https://doc.wearepatchworks.com/product-documentation/general-settings/general-settings-introduction

As a company administrator, you have access to various general settings for managing your organization's profile.

### Audit Logs
The audit logs feature captures significant activities and changes within your company's dashboard. Users holding client admin credentials can access these logs to investigate historical events.

**Accessing:** Navigate to settings menu on the left sidebar and select the audit logs option.

**Event Organization:** Events are organized chronologically by date with color-coded headers:
- **Green**: Items added or created
- **Orange**: Items modified
- **Red**: Items removed

**Searching:** A search function allows locating specific entries by person's name, keywords, or ID numbers.

### Notification Groups
Additional configuration for notification management is available under this section.

---

## 13. Connector Builder

**Source:** https://doc.wearepatchworks.com/product-documentation/developer-hub/connector-builder

### Overview
Patchworks enables users to install and utilize prebuilt connectors from its marketplace. However, the platform also provides a connector builder for scenarios where no prebuilt solution exists -- such as integrating custom in-house systems or non-eCommerce applications.

The connector builder allows you to build your own connectors, which can then be used in exactly the same way as the prebuilt connectors found in the Patchworks marketplace. Custom-built connectors remain private to your organization.

### Target Audience
This tool is designed for individuals with API and data structure knowledge who want to integrate applications without requiring coding expertise. If you are comfortable working with APIs and data structures, you can use the connector builder to integrate any application with an API.

### Postman Importer
For those familiar with Postman, the platform offers a Postman importer feature that can automatically generate connectors from existing collections, which can then be customized as needed.

### Documentation Structure
- Accessing the connector builder
- Building your own connector (includes authentication methods such as SOAP authentication, OAuth, etc.)
- Maintaining your own connectors

---

## 14. Custom Scripting

**Source:** https://doc.wearepatchworks.com/product-documentation/developer-hub/custom-scripting

### Overview
Patchworks facilitates data integration between source and destination systems through field mappings and transformation functions. When standard tools prove insufficient, the platform offers custom scripting capabilities for advanced data manipulation.

### Integrated Development Environment
The custom script editor includes IntelliSense and AI assistance. The AI integration knows about expected keys and value types (payload, variables, meta, etc.), so generated scripts will be in a form that is ready to use in process flows.

### Implementation Methods

**1. Process Flow Integration:**
- Script shapes (executing scripts at any workflow point)
- Map shapes (applying script transforms to fields before destination mapping)

**2. Connector Setup:**
- Endpoint pagination scripting
- Pre and post-authentication scripts
- Pre and post-request scripts

### Supported Programming Languages
- C# 8.0
- Go (1.18 & 1.23)
- Rust 1.8.2
- JavaScript (Node 18)
- PHP (8.1 & 8.2)
- Python 3
- Ruby 3

### Available Libraries
The platform includes language-specific packages such as jsrsasign for JavaScript, requests for Python, phpseclib for PHP, and System.Xml.ReaderWriter for C#. Additional libraries can be embedded or requested from support.

---

## 15. Patchworks API

**Source:** https://doc.wearepatchworks.com/product-documentation/developer-hub/patchworks-api

### Introduction
Patchworks functions as an API-driven platform aligned with MACH Alliance principles. Every dashboard action corresponds to an API request. The Core API is accessible through a public Postman collection for developers.

### Access Requirements
API availability depends on your subscription tier within Patchworks Core's service levels.

### Documentation Sections
1. **Core API Postman collection** -- The public collection for API requests
2. **Core API spotlights** -- Featured API information and use cases
3. **Core API general information** -- Foundational details about the Core API

---

## 16. Patchworks MCP (Model Context Protocol)

**Source:** https://doc.wearepatchworks.com/product-documentation/developer-hub/patchworks-mcp

### Introduction
The Patchworks MCP server enables AI assistants like Claude, Gemini, or ChatGPT to interact with Patchworks directly. Users can triage issues, generate reports, and execute flows using natural language. This capability benefits merchants, partners, and developers by transforming integration workflows.

### What is an MCP Server?
MCP (Model Context Protocol) represents an open protocol enabling secure, standardized connections between AI assistants and external data sources or tools.

An MCP server functions as a bridge between your AI assistant and business systems like Patchworks, providing real-time data access and action capabilities with controlled permissions. The architecture involves:
- **Client-server model**: AI agents (clients) make requests to MCP servers
- **Tools and resources**: Servers expose tools (get flow runs, summarize failures, triage issues) and resources (documentation, databases)
- **Extended capabilities**: AI agents use these elements to expand functionality beyond core language understanding

### Pre-loaded Tools
After local installation, users can access ten pre-loaded tools supporting:
- Data tracking through the platform
- Automating customer inquiries like "Where is my order?"
- Rapid report generation from logs
- Error identification requiring intervention
- Instant access to logs and payloads
- Advanced root cause analysis
- Direct flow triggering
- System-level tools including "List all flows," "Summarise failed run," and "Download payloads"

### Example Use Cases

| Team | Use Case |
|------|----------|
| Customer Support | Show me all failed Shopify to NetSuite flows from last night and explain why |
| Operations | Re-run failed flows from yesterday |
| Development | Give me payload samples going into Order Flow X |

### Key Benefits
- **AI-ready iPaaS**: Integrations become conversational and intelligent
- **Faster troubleshooting**: Automate triage and identify solutions
- **Customizable**: Add tools alongside pre-loaded options
- **Safe & secure**: Per-tenant isolation, role-based access, auditable tool calls
- **Future-proof**: Works with Claude, Gemini, ChatGPT, and MCP-compatible clients

### Implementation Options
Patchworks MCP is available for local installation immediately. A hosted solution is currently in development.

Product documentation can also be integrated with AI assistants via a separate MCP server resource.

---

## 17. Stockr

**Source:** https://doc.wearepatchworks.com/product-documentation/patchworks-bolt-ons/stockr/stockr-overview

### Introduction
Stockr functions as a Patchworks tool designed to manage inventory across multiple Shopify stores that share a common stock pool. The system maintains real-time synchronization of stock levels across all connected stores as orders arrive. When inventory for any item becomes depleted, all linked stores receive simultaneous updates, preventing overselling situations.

The platform is offered as an add-on service for Patchworks.

### Stockr Dashboards
Users of Stockr receive access to a unique URL providing multiple views within a DataDog dashboard interface.

Through the Patchworks dashboard, users can access the Stockr summary feature, which offers comprehensive visibility of processed transactions and associated expenses across specified date ranges. Users have the option to export transaction data when needed.

---

## URL Reference Guide

The correct URL structure for Patchworks documentation is `https://doc.wearepatchworks.com/product-documentation/{section}/{page}`.

| Topic | Correct URL |
|-------|-------------|
| Getting Started | /product-documentation/getting-started/getting-started-introduction |
| Quickstart Guide | /product-documentation/getting-started/patchworks-quickstart-guide |
| Subscription Tiers | /product-documentation/getting-started/core-subscription-tiers |
| Registration | /product-documentation/registration/registering-for-a-patchworks-account |
| Company Profiles | /product-documentation/company-management/about-company-profiles |
| Users & Roles | /product-documentation/users-roles-and-permissions/roles-and-permissions-summary |
| Marketplace | /product-documentation/marketplace/the-patchworks-marketplace |
| Blueprints | /product-documentation/blueprints |
| Connectors & Instances | /product-documentation/connectors-and-instances/connectors-and-instances-introduction |
| Process Flows | /product-documentation/process-flows |
| First Process Flow | /product-documentation/process-flows/building-process-flows/approaching-your-first-process-flow |
| Virtual Environments | /product-documentation/virtual-environments/about-virtual-environments |
| General Settings | /product-documentation/general-settings/general-settings-introduction |
| Connector Builder | /product-documentation/developer-hub/connector-builder |
| Custom Scripting | /product-documentation/developer-hub/custom-scripting |
| Patchworks API | /product-documentation/developer-hub/patchworks-api |
| Patchworks MCP | /product-documentation/developer-hub/patchworks-mcp |
| Stockr | /product-documentation/patchworks-bolt-ons/stockr/stockr-overview |

---

# Creating Process Flows via MCP

## Flow Creation Methods

The Patchworks MCP server provides two methods for creating process flows:

1. **create_process_flow_from_prompt** - Natural language flow creation (simpler, less control)
2. **create_process_flow_from_json** - Full JSON structure import (complete control, recommended)

## Method 1: create_process_flow_from_json (Recommended)

This method requires a complete flow export structure. Use this when you need full control over the flow definition.

### Required JSON Structure

The flow import JSON must contain these **five required top-level keys**:

```json
{
  "metadata": { ... },
  "flow": { ... },
  "systems": [],
  "scripts": [],
  "dependencies": []
}
```

### Minimal Working Example

Here's a minimal flow with just a trigger that runs hourly:

```json
{
  "metadata": {
    "company_name": "Your Company Name",
    "flow_name": "Your Flow Name",
    "exported_at": "2026-02-17T14:30:00+00:00",
    "exported_by": "your-identifier",
    "import_summary": {
      "setup_required": {
        "connectors_needing_config": 0,
        "auth_implementations_needing_credentials": 0,
        "variables_needing_values": 0
      },
      "dependencies": [],
      "imported_resources": {
        "systems_imported": 0,
        "flow_steps": 1,
        "endpoints": 0,
        "connectors": 0
      },
      "next_steps": []
    }
  },
  "flow": {
    "name": "Your Flow Name",
    "description": "Description of what this flow does",
    "is_enabled": false,
    "versions": [
      {
        "flow_name": "Your Flow Name",
        "flow_priority": 3,
        "iteration": 1,
        "status": "Draft",
        "is_deployed": false,
        "is_editable": true,
        "has_callback_step": false,
        "steps": [
          {
            "id": 1,
            "type": "trigger",
            "name": "Trigger",
            "description": "Default hourly trigger",
            "config": {
              "schedule_type": "cron",
              "cron_expression": "0 * * * *"
            },
            "position": {
              "x": 100,
              "y": 100
            }
          }
        ],
        "connections": []
      }
    ]
  },
  "systems": [],
  "scripts": [],
  "dependencies": []
}
```

### Key Structure Requirements

#### 1. metadata (Required)

Must contain:
- `company_name` (string) - Name of the company
- `flow_name` (string) - Name of the flow
- `exported_at` (string) - ISO 8601 timestamp
- `exported_by` (string) - Identifier of creator
- `import_summary` (object) - Summary of import requirements
  - `setup_required` (object) - Configuration needs
    - `connectors_needing_config` (integer)
    - `auth_implementations_needing_credentials` (integer)
    - `variables_needing_values` (integer)
  - `dependencies` (array) - Flow dependencies
  - `imported_resources` (object) - Resource counts
    - `systems_imported` (integer)
    - `flow_steps` (integer)
    - `endpoints` (integer)
    - `connectors` (integer)
  - `next_steps` (array) - Setup instructions

#### 2. flow (Required)

Must contain:
- `name` (string) - Flow name
- `description` (string) - Flow description
- `is_enabled` (boolean) - Whether flow is enabled
- `versions` (array) - Array of flow versions, each containing:
  - `flow_name` (string) - Name of the flow
  - `flow_priority` (integer) - Priority 1-5 (1 is highest)
  - `iteration` (integer) - Version iteration number
  - `status` (string) - "Draft" or deployment status
  - `is_deployed` (boolean) - Deployment status
  - `is_editable` (boolean) - Edit permissions
  - `has_callback_step` (boolean) - Whether flow has callbacks
  - `steps` (array) - **Required: At least one step**
    - Each step must have: `id`, `type`, `name`, `position`, and type-specific `config`
  - `connections` (array) - Connections between steps (can be empty)

#### 3. systems (Required)

Array of connector system configurations. Can be empty `[]` for simple flows.

#### 4. scripts (Required)

Array of custom scripts. Can be empty `[]` for flows without custom scripts.

#### 5. dependencies (Required)

Array of flow dependencies. Can be empty `[]` for flows without dependencies.

### Common Step Types

- `trigger` - Flow trigger (schedule, webhook, event)
- `connector` - Data source or destination connector
- `map` - Field mapping between source and destination
- `filter` - Filter data based on conditions
- `script` - Custom script execution
- `branch` - Conditional branching logic
- `route` - Route data to different paths
- `split` - Split data into batches
- `cache` - Cache management
- `de-dupe` - Data de-duplication

### Priority Levels

- **1** - Highest priority
- **2** - High priority
- **3** - Normal priority (default)
- **4** - Low priority
- **5** - Lowest priority

### Cron Schedule Examples

- `0 * * * *` - Every hour at minute 0
- `*/15 * * * *` - Every 15 minutes
- `0 0 * * *` - Daily at midnight
- `0 0 * * 0` - Weekly on Sunday at midnight
- `0 0 1 * *` - Monthly on the 1st at midnight
- `0 */6 * * *` - Every 6 hours
- `0 9 * * 1-5` - Weekdays at 9 AM

## Method 2: create_process_flow_from_prompt

Creates a basic flow skeleton from a natural language description.

### Usage Example

```
Prompt: "create a process flow for Shopify to NetSuite orders"
Priority: 3 (default)
Schedule: "0 * * * *" (hourly)
Enable: false (default)
```

This method is simpler but provides less control over the flow structure. For production flows or complex requirements, use `create_process_flow_from_json` instead.

## Important Notes

- All five top-level keys (`metadata`, `flow`, `systems`, `scripts`, `dependencies`) **must be present**, even if arrays are empty
- The `metadata.import_summary` structure is required for validation
- Each flow must have at least one version in the `versions` array
- Each version must have at least one step in the `steps` array
- Step IDs must be unique within the flow
- Position coordinates (x, y) determine where shapes appear on the canvas
- Flows are created in "Draft" status by default (not enabled)
- After creation, flows can be further configured in the Patchworks dashboard

## Getting Flow Export Structure

To see a complete flow structure:
1. Use `get_all_flows` to list available flows
2. Export an existing flow from the Patchworks dashboard
3. Use that export as a template for creating new flows via JSON