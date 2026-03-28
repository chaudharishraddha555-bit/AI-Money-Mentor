# AI Money Mentor - Product Requirements Document

## Original Problem Statement
Build a real-world deployable fintech web app called "AI Money Mentor" with:
- User Registration/Login with personal, financial, bank details, Aadhaar and PAN card details
- FIRE (Financial Independence, Retire Early) Calculator and Path Planner
- Money Health Score dashboard
- Couples Finance Planner
- Life Event Financial Advisor
- Tax Wizard
- Mutual Fund Portfolio X-ray
- AI Chat Feature for financial advice

## User Personas
1. **Young Professionals (25-35)**: First-time investors seeking FIRE planning
2. **Couples**: Partners managing joint finances
3. **Tax-conscious Users**: Individuals optimizing tax savings
4. **Investors**: Users tracking mutual fund portfolios

## Core Requirements (Static)
- JWT-based authentication
- Dark theme UI
- Responsive design
- MongoDB database
- Rule-based AI chat

## What's Been Implemented (March 2026)

### Backend APIs
- POST /api/auth/register - User registration
- POST /api/auth/login - User login with JWT
- GET /api/auth/me - Get current user
- PUT /api/auth/profile - Update profile
- POST /api/fire - FIRE calculator
- GET /api/health-score - Money health score
- POST /api/chat - AI chat
- CRUD /api/couples - Couples planner
- CRUD /api/life-events - Life events
- POST /api/tax-wizard - Tax calculator
- CRUD /api/mf-portfolio - MF portfolio

### Frontend Pages
- Landing Page with hero section
- Login/Signup with multi-step form
- Dashboard with bento grid layout
- FIRE Planner with charts
- Couples Planner
- Life Events
- Tax Wizard
- MF Portfolio X-ray
- Profile management
- AI Chat widget

## Prioritized Backlog

### P0 (Critical) - DONE
- [x] User authentication
- [x] FIRE calculator
- [x] Money health score
- [x] Dashboard

### P1 (High Priority) - DONE
- [x] Tax wizard
- [x] MF portfolio
- [x] Couples planner
- [x] Life events
- [x] AI chat

### P2 (Medium Priority) - TODO
- [ ] Real MF data integration
- [ ] Goal-based SIP calculator
- [ ] Expense categorization charts
- [ ] PDF report export
- [ ] Bank account linking

### P3 (Nice to Have) - TODO
- [ ] Email notifications
- [ ] Mobile app
- [ ] Multi-currency support
- [ ] Investment recommendations AI

## Next Tasks
1. Integrate real mutual fund API (RapidAPI or MFU)
2. Add goal-based investment planner
3. Implement expense tracking with categories
4. Add financial report generation
