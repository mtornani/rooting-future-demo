# Rooting Future Strategy Engine
## User Manual v6.0.0-alpha

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation](#3-installation)
4. [License Activation](#4-license-activation)
5. [AI Configuration](#5-ai-configuration)
6. [Generating a Strategic Plan](#6-generating-a-strategic-plan)
7. [Viewing the Plan (WebApp)](#7-viewing-the-plan-webapp)
8. [Exporting the Plan](#8-exporting-the-plan)
9. [Sharing the Plan](#9-sharing-the-plan)
10. [Settings](#10-settings)
11. [Troubleshooting](#11-troubleshooting)
12. [FAQ](#12-faq)
13. [Support](#13-support)

---

## 1. Introduction

**Rooting Future Strategy Engine** is an artificial intelligence software designed to generate professional strategic plans for football/soccer clubs.

### What the Software Does

- Analyzes club data (name, category, city, competitors)
- Automatically generates a complete strategic plan using 6 specialized AI agents
- Produces scientific content with industry benchmarks
- Exports to professional formats (PDF, DOCX, HTML)
- Enables secure sharing with external stakeholders

### The 6 AI Agents

| Agent | Specialization |
|-------|----------------|
| Sporting | Technical sector, first team, methodologies |
| Structural | Infrastructure, facilities, logistics |
| Marketing | Communication, brand, sponsorships |
| Social | Community, social responsibility, territory |
| Financial | Budget, economic sustainability, investments |
| Coordinator | Strategic synthesis and overall coherence |

---

## 2. System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Operating System | Windows 10/11 (64-bit) |
| RAM | 4 GB |
| Disk Space | 500 MB |
| Connection | Internet required |
| Browser | Chrome, Firefox, Edge (recent version) |

### Recommended Requirements

| Component | Recommended |
|-----------|-------------|
| RAM | 8 GB |
| Connection | Fiber or stable 4G |
| Screen | 1920x1080 or higher |

---

## 3. Installation

### Step 1: Extract Files

1. Download `RootingFuture_v6.0.0-alpha.zip`
2. Right-click on the ZIP file
3. Select **"Extract All..."**
4. Choose a destination folder (e.g., `C:\RootingFuture`)
5. Click **"Extract"**

### Step 2: Launch the Application

1. Open the extracted folder
2. Double-click on `RootingFuture_Alpha.exe`
3. If Windows shows a security warning:
   - Click **"More info"**
   - Click **"Run anyway"**

### Step 3: Wait for Startup

- The application takes 5-10 seconds to start
- Your browser will automatically open to `http://localhost:5000`
- You'll see the **Activation** page

> **Note**: Don't close the black terminal window that appears. It's the application server.

---

## 4. License Activation

On first launch, you must activate your license to use the software.

### Step 1: Copy the Machine Code

On the activation page, you'll see a **Machine Code (HWID)** in the format:
```
XXXX-XXXX-XXXX-XXXX
```

1. Click on the code to copy it
2. Send it to your Rooting Future representative

### Step 2: Receive the License Key

Your representative will send you:
- A **license key** in the format `XXXXXX-XXXXXX-XXXXXX-XXXXXX`
- The license **duration** (e.g., 365 days)

### Step 3: Activate

1. Enter your **email**
2. Enter the **license key** received
3. (Optional) Enter the **duration in days**
4. Click **"Activate License"**

If the data is correct, you'll be redirected to the Dashboard.

### What Happens After Activation

- An account is automatically created with your email
- You receive **10 credits** to generate plans
- The license is saved locally

---

## 5. AI Configuration

Before generating plans, you must configure the AI provider.

### Access Settings

1. From the Dashboard, click the **gear icon** (⚙️) in the top right
2. Or go directly to `http://localhost:5000/settings`

### Option A: Google Gemini (Recommended)

1. Go to https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the generated key (starts with `AIza...`)
5. In Rooting Future Settings:
   - Select **"Google Gemini"** as provider
   - Paste the API Key in the field
   - Click **"Test Connection"**
   - If green, click **"Save Settings"**

### Option B: OpenRouter (Free Alternative)

1. Go to https://openrouter.ai/keys
2. Create a free account
3. Generate an API Key (starts with `sk-or-v1-...`)
4. In Rooting Future Settings:
   - Select **"OpenRouter"** as provider
   - Paste the API Key
   - Select a **free model**:
     - Gemini 2.0 Flash (free) - recommended
     - DeepSeek V3 (free)
     - Llama 4 Maverick (free)
     - Qwen3 235B (free)
   - Click **"Test Connection"**
   - If green, click **"Save Settings"**

---

## 6. Generating a Strategic Plan

### Step 1: Start Generation

1. From the Dashboard, click **"New Plan"**
2. Or go to `http://localhost:5000/new-plan`

### Step 2: Fill in Club Data

| Field | Description | Example |
|-------|-------------|---------|
| Club Name | Official club name | Manchester United FC |
| City | Main headquarters | Manchester |
| Category | Competition level | Premier League |
| Competitors | Rival clubs (max 10) | Liverpool, Chelsea, Arsenal |

### Step 3: Start Generation

1. Click **"Generate Strategic Plan"**
2. Wait for completion (1-2 minutes)
3. You'll see a progress bar with steps:
   - Data analysis
   - Section generation (6 agents)
   - Final synthesis
   - Saving

### Step 4: View the Result

Upon completion, you'll be redirected to the **Plan WebApp** with:
- All sections navigable from the side menu
- Buttons to export in various formats
- Sharing option

---

## 7. Viewing the Plan (WebApp)

The WebApp is the interactive interface for viewing the generated plan.

### Navigation

- **Left sidebar**: list of sections
- **Search bar**: search keywords in the plan
- **Center section**: content of the selected section

### Plan Sections

1. **Executive Summary** - Strategic overview
2. **Situational Analysis** - Current club status
3. **Technical-Sporting Area** - First team and methodologies
4. **Youth Sector** - Academy and training
5. **Infrastructure** - Facilities and structures
6. **Marketing and Communication** - Brand and sponsors
7. **Social Area** - Community and territory
8. **Financial Sustainability** - Budget and investments
9. **Operational Plan** - Timeline and milestones
10. **KPIs and Metrics** - Success indicators
11. **Risk Management** - Risk analysis
12. **Conclusions** - Summary and next steps

### Scientific Data

Each section includes **Data Points** with:
- 📊 **Value**: numerical or qualitative data
- 📈 **Benchmark**: comparison with category average
- 🎯 **Reliability**: confidence level (High/Medium/Low)
- 📚 **Source**: bibliographic reference

> **Reliability Tooltip**: hover over the "?" to understand what the levels mean.

---

## 8. Exporting the Plan

### Available Formats

| Format | Description | Recommended Use |
|--------|-------------|-----------------|
| **PDF** | Professional formatted document | Presentations, printing |
| **DOCX** | Editable Microsoft Word | Subsequent modifications |
| **HTML** | Standalone web page | Digital archive |
| **One-Pager** | 1-page summary | Quick pitch |

### How to Export

1. From the plan WebApp, click the button for the desired format
2. Wait for generation (PDF takes 5-10 seconds)
3. The file will download automatically

### Format Notes

- **PDF**: Requires internet connection (uses Chromium for rendering)
- **DOCX**: Editable, maintains basic formatting
- **HTML**: Includes all styles, viewable offline
- **One-Pager**: Ideal for quick executive summary

---

## 9. Sharing the Plan

You can share the plan with external stakeholders (presidents, sponsors, investors) without them needing an account.

### Creating a Sharing Link

1. From the plan WebApp, click **"Share Plan"**
2. Configure the options:

| Option | Description |
|--------|-------------|
| Expiration | 7, 30, 90, or 365 days |
| Password | (Optional) Password protection |
| Download Permissions | Enable/disable file download |

3. Click **"Generate Link"**
4. Copy the generated link and send it

### Managing Shares

- From the WebApp, **"Active Links"** section
- You can see: views, creation date, expiration
- You can **revoke** a link at any time

### Security

- Links are random UUIDs (not guessable)
- Password is hashed (SHA-256)
- Revocation is immediate and irreversible
- Expired links are no longer accessible

---

## 10. Settings

Access settings by clicking the gear (⚙️) from the Dashboard.

### AI Configuration

| Field | Description |
|-------|-------------|
| AI Provider | Gemini or OpenRouter |
| API Key | Your personal key |
| Model | (OpenRouter only) Model to use |

### License Status

View:
- Associated email
- Activation date
- License expiration
- Remaining days

### Saving

Click **"Save Settings"** after each change.

---

## 11. Troubleshooting

### Application Won't Start

**Cause**: Windows Defender or antivirus blocking the exe.

**Solution**:
1. Open Windows Defender
2. Go to "Virus & threat protection"
3. Click "Protection history"
4. Find RootingFuture and click "Allow"

### "API Key Missing" Error

**Cause**: You haven't configured the AI provider.

**Solution**:
1. Go to Settings
2. Enter your API Key (Gemini or OpenRouter)
3. Click "Test Connection"
4. Save

### "License Expired" Error

**Cause**: The license has passed its expiration date.

**Solution**:
1. Contact your representative for renewal
2. You'll receive a new license key
3. Reinstall or contact support

### Slow Generation (>3 minutes)

**Cause**: Slow connection or overloaded AI provider.

**Solution**:
1. Check your internet connection
2. Try a different provider (Gemini ↔ OpenRouter)
3. Try again at a different time

### PDF Won't Generate

**Cause**: Playwright/Chromium not installed.

**Solution**:
1. Make sure you have internet connection
2. Use DOCX export as an alternative
3. Restart the application

### Blank Page in Browser

**Cause**: Server hasn't started yet.

**Solution**:
1. Wait 10 seconds
2. Refresh the page (F5)
3. Verify the terminal window is open

---

## 12. FAQ

### How many plans can I generate?

Depends on available credits. Each plan costs 1 credit. You start with 10 credits and can request more from your representative.

### Can I edit generated plans?

Yes, by exporting in DOCX format you can edit everything with Microsoft Word or compatible software.

### Is club data saved online?

No. All data is saved **locally** on your computer in the `rooting_future.db` file. No data is sent to external servers except AI APIs for generation.

### Can I use the software offline?

No. Internet connection is required for:
- Generating plans (requires AI API)
- Generating PDFs (requires Chromium)

### Is the license transferable?

No. The license is bound to computer hardware (HWID). If you change PCs, you'll need to request a new license.

### What happens if the license expires?

You can continue to view and export already generated plans. You cannot generate new plans until you renew.

### Can I install on multiple computers?

Each computer requires a separate license because the HWID is unique.

### Are competitors analyzed online?

No. The competitors entered only serve as context for the AI. No automatic web research is performed in the alpha version.

---

## 13. Support

### Contacts

- **Email**: support@rootingfuture.com
- **License Representative**: Your commercial contact

### Reporting a Bug

When reporting a problem, include:
1. Problem description
2. Steps to reproduce
3. Screenshot (if possible)
4. Contents of `logs/` folder (if present)

### Requesting Features

Send suggestions to support@rootingfuture.com with subject "Feature Request".

---

## Appendix: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + F` | Search in plan |
| `Esc` | Close modal windows |
| `↑ / ↓` | Navigate between sections |

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 6.0.0-alpha | Feb 2026 | First public alpha release |

---

*Manual updated: February 7, 2026*
*Rooting Future Strategy Engine - All rights reserved*
