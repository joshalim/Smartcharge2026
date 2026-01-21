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

### 3. Settings Page ✅ (Added Jan 2026)
**Three configuration tabs:**
- **PayU Colombia**: API Key, API Login, Merchant ID, Account ID, Test Mode toggle
- **SendGrid Email**: API Key, Sender Email/Name, Enable/Disable, Test email button
- **Invoice Webhook**: URL, API Key, Enable/Disable, Test webhook, Payload preview

### 4. RFID Card Management ✅ (Enhanced Jan 2026)
- Create/Edit/Delete RFID cards
- **Per-card low balance threshold** (default $10,000 COP)
- Manual top-up with preset amounts
- PayU Colombia online top-up
- Transaction history log
- **Email notification** when balance falls below threshold

### 5. OCPP Monitoring ✅
- OCPP 1.6 endpoint support
- Remote Control with Start/Stop buttons
- RFID card validation (min $5k balance)
- Auto balance deduction on session end
- Triggers email if balance drops below threshold

### 6. Invoice Webhook API ✅
- Configurable webhook URL
- Full transaction details on completion
- API key authentication
- Delivery logs
- Test webhook functionality

### 7. Dashboard, Transactions, Reports, Chargers, Pricing
- All previously implemented features

## Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI, i18next, axios
- **Backend**: FastAPI (Python), PyJWT, Pydantic, openpyxl, reportlab, httpx, sendgrid
- **Database**: MongoDB
- **Payment**: PayU Colombia
- **Email**: SendGrid

## API Endpoints Summary

### Settings
- `GET/POST /api/settings/payu` - PayU configuration
- `GET/POST /api/settings/sendgrid` - SendGrid configuration
- `POST /api/settings/sendgrid/test` - Test email

### RFID Cards (Enhanced)
- Cards now include `low_balance_threshold` field
- `PATCH /api/rfid-cards/{id}` supports threshold update

## Credentials
- Admin: `admin@evcharge.com` / `admin123`

## Known Limitations
- OCPP 1.6 is simulated via REST endpoints
- PayU is in sandbox mode by default
- SendGrid requires configuration before emails work

## Upcoming/Future Tasks
1. **P1**: Full OCPP 1.6 WebSocket implementation
2. **P2**: User grouping for pricing rules
3. **P2**: Backend refactoring (split server.py)
4. **P3**: Email templates customization
