# Here are your Instructions

"# AI Money Mentor

A comprehensive fintech web application for personal finance management, FIRE planning, and investment tracking.

## Features

- **User Authentication**: JWT-based login/signup with personal, financial, and KYC details
- **Dashboard**: Money Health Score, income/expense tracking, savings rate
- **FIRE Planner**: Financial Independence, Retire Early calculator with projections
- **Goal-Based SIP Calculator**: Plan for life goals with step-up SIP options
- **Expense Tracker**: Track expenses by category with pie chart visualization
- **Couples Planner**: Joint expense tracking and settlement
- **Life Events Planner**: Plan for marriage, home, education, etc.
- **Tax Wizard**: Compare old vs new tax regime, get optimization suggestions
- **MF Portfolio X-ray**: Mutual fund analysis with risk assessment
- **Bank Account Linking**: Mock bank integration (demo mode)
- **PDF Reports**: Download comprehensive financial reports
- **AI Chat**: Rule-based financial advisor

## Tech Stack

### Backend
- FastAPI (Python)
- MongoDB with Motor (async driver)
- JWT Authentication
- bcrypt for password hashing

### Frontend
- React 18
- Tailwind CSS
- shadcn/ui components
- Recharts for visualizations
- jsPDF for report generation

## Project Structure

```
ai-money-mentor/
├── backend/
│   ├── server.py          # FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── .env.example       # Environment variables template
├── frontend/
│   ├── src/
│   │   ├── pages/         # React pages
│   │   ├── components/    # React components
│   │   │   └── ui/        # shadcn/ui components
│   │   ├── hooks/         # Custom hooks
│   │   ├── lib/           # Utilities
│   │   ├── App.js         # Main app component
│   │   ├── App.css        # App styles
│   │   ├── index.js       # Entry point
│   │   └── index.css      # Global styles
│   ├── package.json       # Node dependencies
│   ├── tailwind.config.js # Tailwind configuration
│   └── .env.example       # Environment variables template
└── README.md
```

## Installation

### Prerequisites
- Node.js 18+
- Python 3.11+
- MongoDB

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your MongoDB URL and JWT secret

# Run server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Copy environment file
cp .env.example .env
# Edit .env with your backend URL

# Run development server
yarn start
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `PUT /api/auth/profile` - Update profile

### Financial Tools
- `POST /api/fire` - FIRE calculator
- `GET /api/health-score` - Money health score
- `POST /api/goal-sip-calculator` - Goal-based SIP
- `POST /api/tax-wizard` - Tax calculator

### Expense Tracking
- `GET /api/expense-categories` - Get categories
- `GET /api/expenses` - List expenses
- `POST /api/expenses` - Add expense
- `DELETE /api/expenses/{id}` - Delete expense

### Couples Planner
- `POST /api/couples/create` - Create plan
- `GET /api/couples` - Get plan
- `POST /api/couples/item` - Add item
- `DELETE /api/couples/item/{id}` - Delete item

### Life Events
- `GET /api/life-events` - List events
- `POST /api/life-events` - Add event
- `PUT /api/life-events/{id}` - Update event
- `DELETE /api/life-events/{id}` - Delete event

### MF Portfolio
- `GET /api/mf-portfolio` - Get portfolio
- `POST /api/mf-portfolio/fund` - Add fund
- `DELETE /api/mf-portfolio/fund/{id}` - Delete fund
- `GET /api/mf-search` - Search mutual funds

### Bank Accounts (Mock)
- `GET /api/banks` - Get supported banks
- `GET /api/linked-accounts` - List accounts
- `POST /api/linked-accounts` - Link account
- `DELETE /api/linked-accounts/{id}` - Unlink account

### Reports
- `GET /api/financial-report` - Get report data

### Chat
- `POST /api/chat` - AI chat

## Environment Variables

### Backend (.env)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=ai_money_mentor
CORS_ORIGINS=*
JWT_SECRET=your-secret-key
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

## Screenshots

The app features a dark theme with:
- Clean dashboard with bento grid layout
- Interactive charts and visualizations
- Mobile-responsive design
- AI chat widget

## License

MIT License

## Author

Built with AI Money Mentor
"
