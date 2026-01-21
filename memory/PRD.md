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
- RFID card management with top-up
- PayU Colombia online payment integration
- 3rd party invoicing webhook API

## Core Features

### 1. Authentication & Authorization
- JWT-based authentication
- Three roles: Admin, User, Viewer
- Role-based route protection
- Demo credentials shown on login page

### 2. User Management ✅ (Enhanced Jan 2026)
- Create new users (Admin only)
- Edit user details (name, email, password)
- Delete users
- Role management (Admin, User, Viewer)

### 3. Dashboard
- Total transactions, energy, revenue stats
- Paid vs unpaid revenue breakdown
- Active stations count
- Recent transactions list
- Payment method breakdown

### 4. Transaction Management
- Excel import (columns: TxID, Station, Connector, Account, Start Time, End Time, Meter value)
- Case-insensitive column matching for "Start Time"
- Bulk payment updates
- Individual transaction editing
- CSV export
- Filtering by date, station, account, payment status

### 5. Pricing
- Custom pricing rules per account/connector
- Special accounts (PORTERIA, Jorge Iluminacion, John Iluminacion) with connector-type pricing

### 6. Charger Management ✅
- Full CRUD operations
- Charger details: name, location, model, serial number, connector types, max power, status

### 7. OCPP Monitoring ✅ (Enhanced Jan 2026)
- OCPP 1.6 endpoint support
- Remote Control panel with Start/Stop charging buttons
- **RFID card integration** - Use card number as ID tag
- **Auto balance validation** - Min $5,000 COP required
- **Auto balance deduction** - Cost deducted when session ends
- Active charging sessions table

### 8. RFID Card Management ✅ (Enhanced Jan 2026)
- Create/Edit/Delete RFID cards for users
- Card details: card number, assigned user, balance, status (active/inactive/blocked)
- **Manual top-up** with preset amounts
- **PayU Colombia online top-up** (Sandbox mode)
- **Transaction history** - Full log of all card activity (top-ups, charges)

### 9. PayU Colombia Integration ✅ (Added Jan 2026)
- WebCheckout integration for RFID card top-ups
- Sandbox mode configured by default
- Webhook for payment confirmation
- Automatic balance update on successful payment

### 10. Invoice Webhook API ✅ (Added Jan 2026)
- Configurable webhook URL for 3rd party invoicing systems
- Full transaction details sent on completion:
  - Transaction ID, account, station, connector
  - Energy consumed, cost
  - Start/end times
  - RFID card info (if linked)
  - User email
- API key authentication support
- Webhook delivery logs
- Test webhook functionality

### 11. Reports & Analytics ✅
- Comprehensive filtering
- Summary cards
- Bar and pie charts
- CSV export

### 12. PDF Invoicing
- Generate invoices for paid transactions

### 13. Internationalization
- English and Spanish support

## Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI, i18next, axios
- **Backend**: FastAPI (Python), PyJWT, Pydantic, openpyxl, reportlab, httpx
- **Database**: MongoDB
- **Payment**: PayU Colombia (Sandbox)

## API Endpoints Summary

### User Management
- `POST /api/users` - Create user
- `PATCH /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### RFID Cards
- `GET /api/rfid-cards` - List all cards
- `POST /api/rfid-cards` - Create card
- `PATCH /api/rfid-cards/{id}` - Update card
- `DELETE /api/rfid-cards/{id}` - Delete card
- `POST /api/rfid-cards/{id}/topup` - Manual top-up
- `GET /api/rfid-cards/{id}/history` - Get card transaction history

### PayU Integration
- `POST /api/payu/initiate-topup` - Start PayU payment flow
- `POST /api/payu/webhook` - Receive payment confirmation
- `GET /api/payu/payment-status/{ref}` - Check payment status

### Invoice Webhook
- `GET /api/invoice-webhook/config` - Get webhook config
- `POST /api/invoice-webhook/config` - Set webhook config
- `GET /api/invoice-webhook/logs` - View delivery logs
- `POST /api/invoice-webhook/test` - Test webhook

### OCPP (Enhanced)
- `POST /api/ocpp/remote-start` - Start with RFID validation
- `POST /api/ocpp/remote-stop` - Stop with auto balance deduction

## Credentials
- Admin: `admin@evcharge.com` / `admin123`

## Known Limitations
- OCPP 1.6 is simulated via REST endpoints (not full WebSocket protocol)
- PayU is in sandbox mode (test payments only)

## Upcoming/Future Tasks
1. **P1**: Full OCPP 1.6 WebSocket implementation
2. **P2**: User grouping for pricing rules
3. **P2**: Backend refactoring (split server.py into modules)
4. **P3**: PayU production credentials configuration page
