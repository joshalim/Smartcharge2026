# SmartCharge EV Management System - PRD

## Original Problem Statement
Build a full-stack web application for managing EV (Electric Vehicle) charging transactions with comprehensive admin features, payment integration, and OCPP compliance.

## User Personas
- **Admin**: Full access to all features, user management, pricing configuration
- **User**: Access to transactions, RFID balance management
- **Viewer**: Read-only access to reports and dashboards

## Core Requirements

### Implemented Features ✅
1. **Authentication & Authorization**
   - Role-based access control (Admin, User, Viewer)
   - JWT-based authentication

2. **User Management**
   - Create, edit, delete users
   - Import users from Excel
   - Phone number and WhatsApp notification toggle
   - RFID card integration per user profile

3. **Transaction Management**
   - Excel import for transactions
   - Transaction listing with filters
   - Cost calculation

4. **Payment Integration**
   - BOLD.CO integration (replaced PayU)
   - QR code charging flow
   - Payment status tracking

5. **Reports & Analytics** (Updated Dec 2025)
   - Dynamic charts (Line, Bar, Pie) using recharts
   - Comprehensive filters (date, account, station, connector, payment type/status)
   - PDF export with html2canvas + jspdf
   - CSV export functionality
   - Summary statistics and data tables

6. **Expenses Tracking** (Added Feb 2025)
   - Full CRUD for expense management
   - Fields: name, date, cost, reason
   - Search and date filtering
   - Dashboard integration with financial charts:
     - Monthly Income vs Expenses (Bar Chart)
     - Profit Trend & Margin (Line/Area Chart)
     - Income/Expense Distribution (Pie Chart)
   - Financial summary cards (Total Income, Expenses, Profit, Margin)

7. **Settings Management**
   - API key management for BOLD.CO, SendGrid, Twilio
   - QR code generator per connector
   - Webhook configuration (FullColombia)

8. **WhatsApp Notifications**
   - Twilio integration for messaging
   - Per-user notification toggle

### Pending/In Progress
1. **Database Migrations (P1)**
   - Need to implement Alembic for automated schema changes
   - Manual SQL migrations causing recurring issues

2. **User Phone Field Migration**
   - SQL: `ALTER TABLE users ADD COLUMN phone VARCHAR(50), ADD COLUMN whatsapp_enabled BOOLEAN DEFAULT FALSE;`

### Future Features
1. Bulk RFID card import from Excel/CSV
2. Export users to Excel (backend exists)
3. SendGrid email notifications
4. User transaction history view
5. BOLD.CO production activation

## Technical Architecture

### Frontend
- React 19
- Tailwind CSS + Shadcn/UI
- recharts for charts
- jspdf + html2canvas for PDF export
- qrcode.react for QR generation
- i18next for bilingual support (EN/ES)

### Backend
- FastAPI (Modular routes)
- SQLAlchemy 2.0 (Async)
- PostgreSQL database
- Twilio SDK for WhatsApp
- OCPP 1.6 via websockets

### Database
- PostgreSQL (deployed on user's Windows Server)
- **NOT MongoDB** - confirmed by user

## Known Issues
1. **Schema Drift**: Login breaks when models change without corresponding ALTER TABLE
2. **Preview Limitation**: Backend cannot run in preview (no PostgreSQL)

## Bug Fixes (Feb 2025)
- **User Import Crash**: Fixed database session management in import functions. Previously creating new sessions per row, causing connection pool exhaustion and app crash.
3. **User blocked**: psql password authentication failed for "evuser"

## File Structure
```
/app/
├── backend/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── transactions.py
│   │   ├── reports.py ← Updated
│   │   ├── settings.py
│   │   └── public_charge.py
│   ├── services/
│   │   ├── ocpp_server.py
│   │   └── whatsapp.py
│   └── migrations/
│       ├── add_bold_tables.sql
│       └── add_user_phone.sql
├── frontend/
│   └── src/
│       └── pages/
│           ├── Reports.js ← Updated
│           ├── Users.js
│           ├── Settings.js
│           └── QRCharge.js
└── memory/
    └── PRD.md
```

## Credentials
- Admin: admin@evcharge.com / admin123

## Last Updated
December 2025 - Reports page overhaul completed
