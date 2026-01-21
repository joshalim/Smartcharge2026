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
- Demo credentials shown on login page

### 2. User Management ✅
- Create new users (Admin only)
- Edit user details (name, email, password)
- Delete users
- Role management
- **NEW: User Import from Excel/CSV** ✅ (Jan 2026)
  - Supports .xlsx, .xls, .csv files
  - Columns: Name, Email, Role (optional), Group (optional)
  - Auto-assigns pricing groups if specified
  - Default password: ChangeMeNow123!

### 3. Pricing Groups ✅ (Added Jan 2026)
- Create/Edit/Delete pricing groups
- Custom connector pricing per group (CCS2, CHADEMO, J1772)
- **Drag-and-drop user assignment** using @dnd-kit library
- Each user can belong to only one group
- Group pricing takes precedence over default pricing
- API endpoints:
  - GET/POST /api/pricing-groups
  - GET/PATCH/DELETE /api/pricing-groups/{id}
  - GET/POST/DELETE /api/pricing-groups/{id}/users/{user_id}

### 4. Settings Page ✅
**Three configuration tabs:**
- **PayU Colombia**: API Key, API Login, Merchant ID, Account ID, Test Mode toggle
- **SendGrid Email**: API Key, Sender Email/Name, Enable/Disable, Test email button
- **Invoice Webhook**: URL, API Key, Enable/Disable, Test webhook, Payload preview

### 5. RFID Card Management ✅
- Create/Edit/Delete RFID cards
- Per-card low balance threshold (default $10,000 COP)
- Manual top-up with preset amounts
- PayU Colombia online top-up
- Transaction history log
- Email notification when balance falls below threshold

### 6. OCPP Monitoring ✅
- OCPP 1.6 endpoint support (HTTP-based)
- Remote Control with Start/Stop buttons
- RFID card validation (min $5k balance)
- Auto balance deduction on session end
- Triggers email if balance drops below threshold

### 7. Invoice Webhook API ✅
- Configurable webhook URL
- Full transaction details on completion
- API key authentication
- Delivery logs
- Test webhook functionality

### 8. Dashboard, Transactions, Reports, Chargers, Pricing
- All previously implemented features

## Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI, i18next, axios, @dnd-kit (drag-and-drop)
- **Backend**: FastAPI (Python), PyJWT, Pydantic, openpyxl, reportlab, httpx, sendgrid
- **Database**: MongoDB
- **Payment**: PayU Colombia (sandbox)
- **Email**: SendGrid

## API Endpoints Summary

### Users
- GET/POST /api/users - List and create users
- PATCH/DELETE /api/users/{id} - Update and delete users
- **POST /api/users/import** - Import users from Excel/CSV

### Pricing Groups
- GET/POST /api/pricing-groups - List and create groups
- GET/PATCH/DELETE /api/pricing-groups/{id} - Single group operations
- GET/POST/DELETE /api/pricing-groups/{id}/users/{user_id} - User assignment

### Settings
- GET/POST /api/settings/payu - PayU configuration
- GET/POST /api/settings/sendgrid - SendGrid configuration
- POST /api/settings/sendgrid/test - Test email

### RFID Cards
- GET/POST /api/rfid-cards - List and create cards
- GET/PATCH/DELETE /api/rfid-cards/{id} - Single card operations
- POST /api/rfid-cards/{id}/topup - Top up balance
- GET /api/rfid-cards/{id}/history - Transaction history

## Credentials
- Admin: `admin@evcharge.com` / `admin123`

## Known Limitations
- OCPP 1.6 is simulated via REST endpoints (not WebSocket)
- PayU is in sandbox mode by default
- SendGrid requires configuration before emails work

## Completed Work (Jan 2026)
1. ✅ Pricing Groups feature with drag-and-drop UI
2. ✅ User Import from Excel/CSV with group assignment
3. ✅ Excel import case-insensitive column handling
4. ✅ All backend tests passing (100%)

## Upcoming/Future Tasks
1. **P1**: Full OCPP 1.6 WebSocket implementation
2. **P2**: Backend refactoring (split server.py into modules)
3. **P3**: Email templates customization
4. **P3**: Bulk RFID card import
