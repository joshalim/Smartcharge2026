# EV Charging Transaction Management - PRD

## Original Problem Statement
Build a full-stack web application for managing EV (Electric Vehicle) charging transactions with:
- Excel import for transaction data
- Custom pricing per connector/account
- Role-based access control
- Colombian Pesos (COP) currency
- Bilingual interface (English/Spanish)
- OCPP 1.6 integration
- Remote control commands
- PDF invoicing
- Reports with charts
- RFID card management with PayU top-up
- 3rd party invoicing webhook API
- Admin settings page for integrations
- Email notifications for low balance
- User grouping for pricing rules
- User import from Excel/CSV

## Core Features

### 1. Authentication & Authorization
- JWT-based authentication
- Three roles: Admin, User, Viewer
- Role-based route protection
- **Password change functionality** for all users via Settings > Account tab
- Demo credentials removed from login page for security (Feb 2026)

### 2. User Management ✅
- Create new users (Admin only)
- Edit user details (name, email, password)
- Delete users
- Role management
- **RFID integrated into User** - Each user has one RFID card (Feb 2026)
  - RFID Card Number (unique)
  - RFID Balance (COP)
  - RFID Status (active/inactive/blocked)
  - Top-up balance functionality
- **User Import from Excel/CSV** ✅ (Jan 2026)
  - Supports .xlsx, .xls, .csv files
  - Columns: Name, Email, Role (optional), RFID Card Number, RFID Balance
  - Default password: ChangeMeNow123!

### 3. Pricing Groups ✅ (Added Jan 2026)
- Create/Edit/Delete pricing groups
- Custom connector pricing per group (CCS2, CHADEMO, J1772)
- **Connector pricing step: 50 COP** (allows 2450, 2550, etc.)
- **Drag-and-drop user assignment** using @dnd-kit library
- Each user can belong to only one group
- Group pricing takes precedence over default pricing
- API endpoints:
  - GET/POST /api/pricing-groups
  - GET/PATCH/DELETE /api/pricing-groups/{id}
  - GET/POST/DELETE /api/pricing-groups/{id}/users/{user_id}

### 4. Pricing Rules ✅
- Per-account, per-connector pricing configuration
- API endpoints:
  - GET/POST /api/pricing
  - DELETE /api/pricing/{id}

### 5. Settings Page ✅
**Three configuration tabs:**
- **PayU Colombia**: API Key, API Login, Merchant ID, Account ID, Test Mode toggle
- **SendGrid Email**: API Key, Sender Email/Name, Enable/Disable, Test email button
- **Invoice Webhook**: URL, API Key, Enable/Disable, Test webhook, Payload preview

### 6. RFID Card Management ✅
- Create/Edit/Delete RFID cards
- Per-card low balance threshold (default $10,000 COP)
- Manual top-up with preset amounts
- PayU Colombia online top-up
- Transaction history log
- Email notification when balance falls below threshold

### 7. OCPP Monitoring ✅
- OCPP 1.6 endpoint support (HTTP-based)
- Remote Control with Start/Stop buttons
- RFID card validation (min $5k balance)
- Auto balance deduction on session end
- Triggers email if balance drops below threshold

### 8. Invoice Webhook API ✅
- Configurable webhook URL
- Full transaction details on completion
- API key authentication
- Delivery logs
- Test webhook functionality

### 9. Dashboard, Transactions, Reports, Chargers
- All previously implemented features

## Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI, i18next, axios, @dnd-kit (drag-and-drop)
- **Backend**: FastAPI (Python), PyJWT, Pydantic, SQLAlchemy, asyncpg, openpyxl, reportlab, httpx, sendgrid
- **Database**: PostgreSQL 16
- **Payment**: PayU Colombia (sandbox)
- **Email**: SendGrid

## API Endpoints Summary

### Users
- GET/POST /api/users - List and create users
- PATCH/DELETE /api/users/{id} - Update and delete users
- **POST /api/users/import** - Import users from Excel/CSV

### Pricing
- GET/POST /api/pricing - List and create pricing rules
- DELETE /api/pricing/{id} - Delete pricing rule

### Pricing Groups
- GET/POST /api/pricing-groups - List and create groups
- GET/PATCH/DELETE /api/pricing-groups/{id} - Single group operations
- GET/POST/DELETE /api/pricing-groups/{id}/users/{user_id} - User assignment

### Settings
- GET/POST /api/settings/payu - PayU configuration
- GET/POST /api/settings/sendgrid - SendGrid configuration
- POST /api/settings/sendgrid/test - Test email

### Authentication
- POST /api/auth/login - User login
- POST /api/auth/register - User registration
- GET /api/auth/me - Get current user
- **POST /api/auth/change-password** - Change password for current user

### RFID Cards
- GET/POST /api/rfid-cards - List and create cards
- GET/PATCH/DELETE /api/rfid-cards/{id} - Single card operations
- POST /api/rfid-cards/{id}/topup - Top up balance
- GET /api/rfid-cards/{id}/history - Transaction history

## Credentials
- Admin: `admin@evcharge.com` / `admin123`

## Deployment

### Windows Server 2016
- Use `start-backend.bat` for manual testing
- Use `install-services.bat` for automatic service installation
- Frontend must be rebuilt when `REACT_APP_BACKEND_URL` changes
- **Important**: Use server IP address (not localhost) for network access

### Key Files
- `backend/start-backend.bat` - Manual backend startup script
- `backend/service-backend.bat` - Windows service wrapper
- `install-services.bat` - Automatic service installer
- `backend/.env` - Must contain `DATABASE_TYPE=postgresql`

## Known Limitations
- OCPP 1.6 is simulated via REST endpoints (not WebSocket)
- PayU is in sandbox mode by default
- SendGrid requires configuration before emails work

## Completed Work (Feb 2026)
1. ✅ Pricing Groups feature with drag-and-drop UI
2. ✅ User Import from Excel/CSV with group assignment
3. ✅ Excel import case-insensitive column handling
4. ✅ Download Template button for user import
5. ✅ Installation instructions (Docker + Ubuntu + Windows Server 2016)
6. ✅ **Mass deletion of selected transactions** (Bulk Delete)
7. ✅ Database migration: MongoDB → PostgreSQL
8. ✅ Windows Server startup scripts
9. ✅ Connector pricing step reduced to 50 COP
10. ✅ Fixed pricing rules and pricing groups API endpoints
11. ✅ **P0 Bug Fix**: db_adapter.py handles MongoDB-style operators ($ne, $gt, $in, etc.) - User updates now work correctly
12. ✅ **P1 Bug Fix**: Charger creation form includes required charger_id field
13. ✅ **P1 Bug Fix**: OCPP status endpoint working (OCPPSession model mapped correctly)
14. ✅ **P1 Bug Fix**: OCPP.js frontend charger.connectors compatibility fix
15. ✅ **Critical Fix**: Added missing database models (Settings, PayUPayment, PayUWebhookLog, OCPPBoot, OCPPTransaction, InvoiceWebhookConfig, InvoiceWebhookLog)
16. ✅ **Critical Fix**: MODEL_MAP updated with 'pricing' → PricingRule alias and all new collections
17. ✅ **Critical Fix**: db_adapter.py returns proper DeleteResult/UpdateResult objects with attribute access
18. ✅ **P2 COMPLETE**: Backend refactored - Monolithic server.py (2435 lines) split into 11 modular route files
19. ✅ **P2 COMPLETE**: Replaced db_adapter.py with direct SQLAlchemy calls in all routes
20. ✅ **P3 COMPLETE**: Export users to Excel/CSV
21. ✅ **P3 COMPLETE**: Export transactions to Excel/CSV
22. ✅ **P3 COMPLETE**: Export RFID cards to Excel/CSV
23. ✅ **P3 COMPLETE**: Bulk RFID card import from Excel/CSV
24. ✅ **P1 COMPLETE**: Full OCPP 1.6 WebSocket implementation on port 9000
25. ✅ **P3 COMPLETE**: Email templates customization with SendGrid integration
26. ✅ **ENHANCEMENT**: Real-time WebSocket updates to frontend dashboard for live OCPP status
27. ✅ **SECURITY**: Demo credentials removed from login page (Feb 7, 2026)
28. ✅ **FEATURE**: Password change functionality added to Settings > Account tab (Feb 7, 2026)
29. ✅ **P0 BUG FIX**: Excel import made more flexible - only requires: TxID, Station, Connector, Account, Start Time, End Time, Meter value(kW.h). All other columns ignored. (Feb 7, 2026)
30. ✅ **FEATURE**: Transaction CRUD - Manual add, edit, delete individual transactions (Feb 7, 2026)
31. ✅ **REFACTOR**: RFID combined into Users - Each user now has integrated RFID card fields (Feb 7, 2026)
32. ✅ **FEATURE**: Excel import rebuilt - Client-side parsing with SheetJS, sends JSON to backend (Feb 7, 2026)
33. ✅ **FEATURE**: QR Code Charging - Public page for users to scan QR, select connector, choose amount, and pay via BOLD.CO (Feb 7, 2026)
34. ✅ **FEATURE**: QR Code Generator - Settings page shows QR codes with download buttons + copyable URLs for each charger's connectors (CCS2, CHADEMO, J1772) (Feb 7, 2026)
35. ✅ **INTEGRATION**: Replaced PayU with BOLD.CO payment gateway - Supports Credit Cards, PSE, Bancolombia, Nequi (Feb 7, 2026)

## Backend Architecture
- `/app/backend/server.py` - Main FastAPI application (~200 lines)
- `/app/backend/routes/` - 12 modular route files:
  - `auth.py` - Authentication (login, register, JWT)
  - `users.py` - User CRUD + import
  - `chargers.py` - Charger management
  - `transactions.py` - Transaction CRUD + import + bulk delete
  - `pricing.py` - Pricing rules and groups
  - `rfid.py` - RFID card management + import
  - `dashboard.py` - Statistics
  - `ocpp.py` - OCPP REST API + WebSocket frontend updates
  - `settings.py` - PayU, SendGrid configuration
  - `export.py` - Excel/CSV exports
  - `email.py` - Email templates management
  - `public_charge.py` - QR code charging flow + PayU integration
- `/app/backend/services/` - Business logic:
  - `ocpp_server.py` - OCPP 1.6 WebSocket central system
  - `email_service.py` - SendGrid email service with templates

## OCPP 1.6 Implementation
- WebSocket server on port 9000
- URL: `ws://localhost:9000/ocpp/1.6/{charger_id}`
- Supported messages: BootNotification, Heartbeat, StatusNotification, Authorize, StartTransaction, StopTransaction, MeterValues
- Remote commands: RemoteStartTransaction, RemoteStopTransaction, Reset, UnlockConnector, ChangeAvailability
- Simulation endpoints for testing without real hardware

## Email Templates
- 4 default templates: low_balance, transaction_complete, welcome, password_reset
- Variable substitution using {{variable_name}} syntax
- Template preview and customization via API
- Requires SendGrid API key in settings to send emails

## Real-time Frontend Features
- **useOCPPWebSocket hook** - Custom React hook for WebSocket connection with auto-reconnect
- **OCPPLiveStatus component** - Dashboard widget showing:
  - WebSocket connection status (Connected/Disconnected)
  - Online chargers count
  - Active sessions count
  - Charging now count
  - Live event feed
- **OCPP page enhancements**:
  - "Live Updates Active" badge with pulsing indicator
  - WebSocket label on Online Chargers card
  - Live event notifications for charger connect/disconnect and transaction start/stop
  - Reduced polling interval (30s fallback instead of 5s)

## Upcoming/Future Tasks
- Implement Alembic for database migrations (to prevent recurring schema drift issues)
- Bulk RFID card import from Excel/CSV
- Export users to Excel button

## QR Code Charging Feature
**How it works:**
1. Admin goes to Settings > QR Codes tab
2. Each charger shows 3 URLs - one for each connector type (CCS2, CHADEMO, J1772)
3. Copy the URL and generate a QR code using any QR generator
4. Display the QR code on the charger's screen for that connector

**URL Format:** `https://your-domain.com/charge/{charger_id}?connector={connector_type}`

**User Flow:**
1. User scans QR code with phone
2. Opens the charging page with connector pre-selected
3. Chooses amount (preset or custom)
4. Optionally enters email, phone, vehicle plate
5. Clicks "Start Charging" → Redirects to PayU
6. Completes payment → Returns to result page
7. Transaction is recorded and charge session starts

**BOLD.CO Integration:**
- Uses BOLD.CO Colombia payment link API
- Requires only API Key (Llave de Identidad) in Settings > BOLD.CO
- Supports Credit Cards, PSE, Botón Bancolombia, Nequi
- Payment links expire in 24 hours
- Webhook for payment status updates

**Backend Endpoints:**
- `GET /api/public/charger/{charger_id}` - Get charger info (no auth)
- `GET /api/public/pricing` - Get connector pricing (no auth)
- `POST /api/public/start-charge` - Create charging session (no auth)
- `GET /api/public/session/{session_id}` - Get session status (no auth)
- `POST /api/public/bold-webhook` - BOLD.CO callback (no auth)
- `GET /api/public/bold-callback` - BOLD.CO redirect callback (no auth)

## Potential Enhancements
1. **Email template persistence** - Save custom templates to database
2. **OCPP 2.0 support** - Upgrade to newer protocol
3. **Real-time dashboard** - WebSocket updates for live stats
4. **Multi-language email templates** - Spanish/English versions
5. **Invoice PDF generation** - Detailed transaction receipts
6. **Mobile app integration** - REST API for mobile clients
