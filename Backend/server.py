from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import httpx
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'ai-money-mentor-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI(title="AI Money Mentor API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# ============== MODELS ==============

class BankDetails(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    age: int = 25
    income: float = 0
    expenses: float = 0
    savings: float = 0
    bank_details: Optional[BankDetails] = None
    aadhaar: Optional[str] = None
    pan: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    age: int
    income: float
    expenses: float
    savings: float
    bank_details: Optional[BankDetails] = None
    aadhaar: Optional[str] = None
    pan: Optional[str] = None
    created_at: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    income: Optional[float] = None
    expenses: Optional[float] = None
    savings: Optional[float] = None
    bank_details: Optional[BankDetails] = None
    aadhaar: Optional[str] = None
    pan: Optional[str] = None

class FIRERequest(BaseModel):
    monthly_expenses: float
    current_savings: float
    monthly_sip: float
    current_age: int
    retirement_age: int = 45
    inflation_rate: float = 6.0
    expected_returns: float = 12.0

class FIREResponse(BaseModel):
    annual_expenses: float
    future_annual_expenses: float
    fire_corpus_needed: float
    current_wealth: float
    projected_wealth: float
    gap: float
    required_monthly_sip: float
    years_to_fire: int
    on_track: bool

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
    suggestions: List[str] = []

class CouplesPlanItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    description: str
    amount: float
    paid_by: str
    date: str

class CouplesPlanCreate(BaseModel):
    partner1_name: str
    partner2_name: str
    items: List[CouplesPlanItem] = []

class LifeEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    target_date: str
    estimated_cost: float
    current_savings: float
    monthly_contribution: float = 0
    notes: Optional[str] = None

class TaxWizardRequest(BaseModel):
    gross_income: float
    hra_received: float = 0
    rent_paid: float = 0
    lta: float = 0
    section_80c: float = 0
    section_80d: float = 0
    nps_80ccd: float = 0
    home_loan_interest: float = 0
    other_deductions: float = 0
    regime: str = "old"  # "old" or "new"

class TaxWizardResponse(BaseModel):
    gross_income: float
    total_deductions: float
    taxable_income: float
    tax_payable: float
    effective_tax_rate: float
    suggestions: List[str]
    comparison: dict

class MutualFund(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    invested_amount: float
    current_value: float
    units: float
    nav: float
    returns_percent: float

class MFPortfolioCreate(BaseModel):
    funds: List[MutualFund] = []

class MFPortfolioResponse(BaseModel):
    funds: List[MutualFund]
    total_invested: float
    total_current_value: float
    overall_returns: float
    overall_returns_percent: float
    category_allocation: dict
    risk_analysis: dict
    suggestions: List[str]

# ============== HELPER FUNCTIONS ==============

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ============== AUTH ROUTES ==============

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "age": user_data.age,
        "income": user_data.income,
        "expenses": user_data.expenses,
        "savings": user_data.savings,
        "bank_details": user_data.bank_details.model_dump() if user_data.bank_details else None,
        "aadhaar": user_data.aadhaar,
        "pan": user_data.pan,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Remove password and _id from response
    del user_doc["password"]
    token = create_token(user_id, user_data.email)
    
    return {"message": "User registered successfully", "token": token, "user": user_doc}

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["id"], user["email"])
    
    # Remove password from response
    user_response = {k: v for k, v in user.items() if k != "password"}
    
    return {"message": "Login successful", "token": token, "user": user_response}

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user_response = {k: v for k, v in current_user.items() if k != "password"}
    return user_response

@api_router.put("/auth/profile")
async def update_profile(updates: UserUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if "bank_details" in update_data and update_data["bank_details"]:
        update_data["bank_details"] = update_data["bank_details"]
    
    if update_data:
        await db.users.update_one({"id": current_user["id"]}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0, "password": 0})
    return {"message": "Profile updated", "user": updated_user}

# ============== FIRE CALCULATOR ==============

@api_router.post("/fire", response_model=FIREResponse)
async def calculate_fire(data: FIRERequest, current_user: dict = Depends(get_current_user)):
    # Calculate years to retirement
    years_to_fire = data.retirement_age - data.current_age
    if years_to_fire <= 0:
        years_to_fire = 1
    
    # Annual expenses
    annual_expenses = data.monthly_expenses * 12
    
    # Future annual expenses (adjusted for inflation)
    inflation_factor = (1 + data.inflation_rate / 100) ** years_to_fire
    future_annual_expenses = annual_expenses * inflation_factor
    
    # FIRE corpus needed (25x rule)
    fire_corpus_needed = future_annual_expenses * 25
    
    # Current wealth
    current_wealth = data.current_savings
    
    # Projected wealth with SIP
    monthly_rate = data.expected_returns / 100 / 12
    months = years_to_fire * 12
    
    # Future value of current savings
    fv_savings = data.current_savings * ((1 + data.expected_returns / 100) ** years_to_fire)
    
    # Future value of SIP (monthly compounding)
    if monthly_rate > 0:
        fv_sip = data.monthly_sip * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    else:
        fv_sip = data.monthly_sip * months
    
    projected_wealth = fv_savings + fv_sip
    
    # Gap calculation
    gap = fire_corpus_needed - projected_wealth
    
    # Required SIP to reach FIRE corpus
    if gap > 0 and monthly_rate > 0:
        # PMT formula to find required SIP
        remaining_corpus = fire_corpus_needed - fv_savings
        if remaining_corpus > 0:
            required_sip = remaining_corpus / ((((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate))
        else:
            required_sip = 0
    else:
        required_sip = 0
    
    return FIREResponse(
        annual_expenses=round(annual_expenses, 2),
        future_annual_expenses=round(future_annual_expenses, 2),
        fire_corpus_needed=round(fire_corpus_needed, 2),
        current_wealth=round(current_wealth, 2),
        projected_wealth=round(projected_wealth, 2),
        gap=round(max(0, gap), 2),
        required_monthly_sip=round(max(0, required_sip), 2),
        years_to_fire=years_to_fire,
        on_track=gap <= 0
    )

# ============== AI CHAT ==============

@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    message = request.message.lower()
    
    # Rule-based responses
    if any(word in message for word in ["tax", "80c", "deduction", "save tax"]):
        return ChatResponse(
            reply="For tax savings, you can invest in Section 80C instruments like PPF, ELSS, NPS, or life insurance. The maximum deduction under 80C is Rs. 1.5 lakhs. Additionally, consider Section 80D for health insurance premiums (up to Rs. 25,000 for self and Rs. 50,000 for parents).",
            suggestions=["Explore ELSS funds", "Open a PPF account", "Check NPS benefits"]
        )
    
    elif any(word in message for word in ["invest", "sip", "mutual fund", "stock", "equity"]):
        return ChatResponse(
            reply="SIP (Systematic Investment Plan) is a great way to invest regularly in mutual funds. Start with diversified equity funds for long-term wealth creation. Consider index funds like Nifty 50 or Sensex funds for beginners. For moderate risk, balanced advantage funds are a good option.",
            suggestions=["Start a SIP", "Check MF Portfolio X-ray", "Explore index funds"]
        )
    
    elif any(word in message for word in ["save", "budget", "expense", "spend"]):
        return ChatResponse(
            reply="Follow the 50-30-20 rule: 50% for needs (rent, utilities, food), 30% for wants (entertainment, dining out), and 20% for savings and investments. Track your expenses daily and review monthly. Cut unnecessary subscriptions and negotiate better deals on recurring expenses.",
            suggestions=["Create a budget", "Track expenses", "Review subscriptions"]
        )
    
    elif any(word in message for word in ["fire", "retire", "financial independence"]):
        return ChatResponse(
            reply="FIRE (Financial Independence, Retire Early) requires accumulating 25x your annual expenses. Focus on increasing your savings rate, investing in growth assets, and reducing lifestyle inflation. Use our FIRE calculator to plan your path to financial independence.",
            suggestions=["Use FIRE Calculator", "Increase savings rate", "Review investments"]
        )
    
    elif any(word in message for word in ["loan", "emi", "debt", "credit"]):
        return ChatResponse(
            reply="Prioritize paying off high-interest debt first (credit cards, personal loans). Consider the debt avalanche method for fastest payoff or debt snowball for psychological wins. Never take loans for depreciating assets. Home loans can be beneficial due to tax benefits.",
            suggestions=["Check EMI calculator", "Review credit score", "Debt repayment plan"]
        )
    
    elif any(word in message for word in ["emergency", "fund", "safety"]):
        return ChatResponse(
            reply="Build an emergency fund covering 6-12 months of expenses. Keep it in a liquid fund or high-interest savings account for easy access. This protects you from unexpected job loss, medical emergencies, or urgent repairs without touching your investments.",
            suggestions=["Calculate emergency fund", "Open liquid fund", "Review insurance"]
        )
    
    elif any(word in message for word in ["insurance", "term", "health"]):
        return ChatResponse(
            reply="Term insurance should be 10-15x your annual income. Health insurance should cover at least Rs. 10-20 lakhs per person. Buy these before investing. Consider super top-up plans for additional coverage at lower premiums.",
            suggestions=["Calculate term cover", "Compare health plans", "Review existing policies"]
        )
    
    elif any(word in message for word in ["marriage", "wedding", "child", "education", "house", "car"]):
        return ChatResponse(
            reply="Plan for life events by starting early and investing in goal-specific funds. Use our Life Events Planner to calculate how much you need and track your progress. Consider SIPs in equity funds for goals 5+ years away.",
            suggestions=["Use Life Events Planner", "Start goal-based SIP", "Review timeline"]
        )
    
    elif any(word in message for word in ["hello", "hi", "hey", "help"]):
        return ChatResponse(
            reply=f"Hello {current_user['name']}! I'm your AI Money Mentor. I can help you with tax savings, investments, budgeting, FIRE planning, and more. Just ask me anything about personal finance!",
            suggestions=["Tax planning tips", "Investment advice", "Budget help", "FIRE planning"]
        )
    
    else:
        return ChatResponse(
            reply="I can help you with financial topics like tax saving (80C, 80D), investments (SIP, mutual funds), budgeting (50-30-20 rule), FIRE planning, loans, insurance, and life event planning. What would you like to know more about?",
            suggestions=["Tax savings", "Start investing", "Budget planning", "FIRE calculator"]
        )

# ============== COUPLES PLANNER ==============

@api_router.post("/couples/create")
async def create_couples_plan(data: CouplesPlanCreate, current_user: dict = Depends(get_current_user)):
    plan_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "partner1_name": data.partner1_name,
        "partner2_name": data.partner2_name,
        "items": [item.model_dump() for item in data.items],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.couples_plans.insert_one(plan_doc)
    if "_id" in plan_doc:
        del plan_doc["_id"]
    return {"message": "Couples plan created", "plan": plan_doc}

@api_router.get("/couples")
async def get_couples_plan(current_user: dict = Depends(get_current_user)):
    plan = await db.couples_plans.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not plan:
        return {"plan": None}
    return {"plan": plan}

@api_router.post("/couples/item")
async def add_couples_item(item: CouplesPlanItem, current_user: dict = Depends(get_current_user)):
    result = await db.couples_plans.update_one(
        {"user_id": current_user["id"]},
        {"$push": {"items": item.model_dump()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Item added", "item": item}

@api_router.delete("/couples/item/{item_id}")
async def delete_couples_item(item_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.couples_plans.update_one(
        {"user_id": current_user["id"]},
        {"$pull": {"items": {"id": item_id}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted"}

# ============== LIFE EVENTS ==============

@api_router.post("/life-events")
async def add_life_event(event: LifeEvent, current_user: dict = Depends(get_current_user)):
    event_doc = event.model_dump()
    event_doc["user_id"] = current_user["id"]
    event_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.life_events.insert_one(event_doc)
    if "_id" in event_doc:
        del event_doc["_id"]
    return {"message": "Life event added", "event": event_doc}

@api_router.get("/life-events")
async def get_life_events(current_user: dict = Depends(get_current_user)):
    events = await db.life_events.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(100)
    return {"events": events}

@api_router.put("/life-events/{event_id}")
async def update_life_event(event_id: str, event: LifeEvent, current_user: dict = Depends(get_current_user)):
    event_data = event.model_dump()
    event_data["id"] = event_id
    result = await db.life_events.update_one(
        {"id": event_id, "user_id": current_user["id"]},
        {"$set": event_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event updated"}

@api_router.delete("/life-events/{event_id}")
async def delete_life_event(event_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.life_events.delete_one({"id": event_id, "user_id": current_user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}

# ============== TAX WIZARD ==============

@api_router.post("/tax-wizard", response_model=TaxWizardResponse)
async def calculate_tax(data: TaxWizardRequest, current_user: dict = Depends(get_current_user)):
    suggestions = []
    
    # Old Regime Calculation
    old_regime_deductions = 0
    
    # Standard deduction
    standard_deduction = 50000
    old_regime_deductions += standard_deduction
    
    # HRA exemption (simplified calculation)
    if data.hra_received > 0 and data.rent_paid > 0:
        hra_exemption = min(
            data.hra_received,
            data.rent_paid - (0.1 * data.gross_income),
            0.5 * data.gross_income  # Assuming metro city
        )
        old_regime_deductions += max(0, hra_exemption)
    
    # Section 80C (max 1.5L)
    section_80c = min(data.section_80c, 150000)
    old_regime_deductions += section_80c
    if data.section_80c < 150000:
        suggestions.append(f"You can invest Rs. {150000 - data.section_80c:,.0f} more in 80C instruments (PPF, ELSS, NPS)")
    
    # Section 80D (max 25k self + 50k parents)
    section_80d = min(data.section_80d, 75000)
    old_regime_deductions += section_80d
    if data.section_80d < 25000:
        suggestions.append("Consider health insurance for yourself to claim 80D deduction")
    
    # NPS 80CCD(1B) (additional 50k)
    nps_deduction = min(data.nps_80ccd, 50000)
    old_regime_deductions += nps_deduction
    if data.nps_80ccd < 50000:
        suggestions.append(f"Invest Rs. {50000 - data.nps_80ccd:,.0f} more in NPS for additional 80CCD(1B) benefit")
    
    # Home loan interest (max 2L)
    home_loan = min(data.home_loan_interest, 200000)
    old_regime_deductions += home_loan
    
    # Other deductions
    old_regime_deductions += data.other_deductions
    
    old_taxable = max(0, data.gross_income - old_regime_deductions)
    
    # Old regime tax slabs (FY 2024-25)
    def calc_old_tax(income):
        tax = 0
        if income > 1000000:
            tax += (income - 1000000) * 0.30
            income = 1000000
        if income > 500000:
            tax += (income - 500000) * 0.20
            income = 500000
        if income > 250000:
            tax += (income - 250000) * 0.05
        return tax
    
    old_tax = calc_old_tax(old_taxable)
    # Rebate 87A (up to 5L taxable income)
    if old_taxable <= 500000:
        old_tax = 0
    # Add cess
    old_tax = old_tax * 1.04
    
    # New Regime Calculation (FY 2024-25)
    new_regime_deductions = 75000  # Standard deduction only in new regime
    new_taxable = max(0, data.gross_income - new_regime_deductions)
    
    def calc_new_tax(income):
        tax = 0
        slabs = [
            (300000, 0),
            (700000, 0.05),
            (1000000, 0.10),
            (1200000, 0.15),
            (1500000, 0.20),
            (float('inf'), 0.30)
        ]
        prev_limit = 0
        for limit, rate in slabs:
            if income > prev_limit:
                taxable_in_slab = min(income, limit) - prev_limit
                tax += taxable_in_slab * rate
            prev_limit = limit
        return tax
    
    new_tax = calc_new_tax(new_taxable)
    # Rebate 87A (up to 7L taxable income in new regime)
    if new_taxable <= 700000:
        new_tax = 0
    # Add cess
    new_tax = new_tax * 1.04
    
    # Determine which regime is better
    if data.regime == "old":
        total_deductions = old_regime_deductions
        taxable_income = old_taxable
        tax_payable = old_tax
    else:
        total_deductions = new_regime_deductions
        taxable_income = new_taxable
        tax_payable = new_tax
    
    if old_tax < new_tax:
        suggestions.append(f"Old regime saves you Rs. {new_tax - old_tax:,.0f}. Consider switching.")
    elif new_tax < old_tax:
        suggestions.append(f"New regime saves you Rs. {old_tax - new_tax:,.0f}. Consider switching.")
    
    effective_rate = (tax_payable / data.gross_income * 100) if data.gross_income > 0 else 0
    
    return TaxWizardResponse(
        gross_income=data.gross_income,
        total_deductions=total_deductions,
        taxable_income=taxable_income,
        tax_payable=round(tax_payable, 2),
        effective_tax_rate=round(effective_rate, 2),
        suggestions=suggestions,
        comparison={
            "old_regime": {
                "deductions": old_regime_deductions,
                "taxable_income": old_taxable,
                "tax": round(old_tax, 2)
            },
            "new_regime": {
                "deductions": new_regime_deductions,
                "taxable_income": new_taxable,
                "tax": round(new_tax, 2)
            },
            "recommended": "old" if old_tax <= new_tax else "new"
        }
    )

# ============== MF PORTFOLIO ==============

@api_router.post("/mf-portfolio")
async def save_mf_portfolio(data: MFPortfolioCreate, current_user: dict = Depends(get_current_user)):
    portfolio_doc = {
        "user_id": current_user["id"],
        "funds": [fund.model_dump() for fund in data.funds],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.mf_portfolios.update_one(
        {"user_id": current_user["id"]},
        {"$set": portfolio_doc},
        upsert=True
    )
    
    return {"message": "Portfolio saved"}

@api_router.get("/mf-portfolio")
async def get_mf_portfolio(current_user: dict = Depends(get_current_user)):
    portfolio = await db.mf_portfolios.find_one({"user_id": current_user["id"]}, {"_id": 0})
    
    if not portfolio or not portfolio.get("funds"):
        # Return sample data for demo
        sample_funds = [
            {
                "id": str(uuid.uuid4()),
                "name": "Nifty 50 Index Fund",
                "category": "Large Cap",
                "invested_amount": 100000,
                "current_value": 125000,
                "units": 1250,
                "nav": 100,
                "returns_percent": 25
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Axis Small Cap Fund",
                "category": "Small Cap",
                "invested_amount": 50000,
                "current_value": 72000,
                "units": 500,
                "nav": 144,
                "returns_percent": 44
            },
            {
                "id": str(uuid.uuid4()),
                "name": "HDFC Balanced Advantage Fund",
                "category": "Balanced",
                "invested_amount": 75000,
                "current_value": 85000,
                "units": 2500,
                "nav": 34,
                "returns_percent": 13.33
            },
            {
                "id": str(uuid.uuid4()),
                "name": "SBI Debt Fund",
                "category": "Debt",
                "invested_amount": 50000,
                "current_value": 53000,
                "units": 5000,
                "nav": 10.6,
                "returns_percent": 6
            }
        ]
        portfolio = {"funds": sample_funds}
    
    funds = portfolio.get("funds", [])
    
    # Calculate totals
    total_invested = sum(f["invested_amount"] for f in funds)
    total_current = sum(f["current_value"] for f in funds)
    overall_returns = total_current - total_invested
    overall_returns_percent = (overall_returns / total_invested * 100) if total_invested > 0 else 0
    
    # Category allocation
    category_allocation = {}
    for fund in funds:
        cat = fund.get("category", "Other")
        if cat not in category_allocation:
            category_allocation[cat] = 0
        category_allocation[cat] += fund["current_value"]
    
    # Convert to percentages
    for cat in category_allocation:
        category_allocation[cat] = round(category_allocation[cat] / total_current * 100, 2) if total_current > 0 else 0
    
    # Risk analysis
    risk_weights = {
        "Large Cap": 1,
        "Mid Cap": 2,
        "Small Cap": 3,
        "Balanced": 1.5,
        "Debt": 0.5,
        "Liquid": 0.3,
        "Other": 1.5
    }
    
    weighted_risk = 0
    for cat, pct in category_allocation.items():
        weighted_risk += pct * risk_weights.get(cat, 1.5)
    
    risk_score = weighted_risk / 100
    risk_level = "Low" if risk_score < 1 else "Moderate" if risk_score < 2 else "High"
    
    # Suggestions
    suggestions = []
    if category_allocation.get("Small Cap", 0) > 30:
        suggestions.append("High small cap allocation. Consider reducing for better risk management.")
    if category_allocation.get("Large Cap", 0) < 30:
        suggestions.append("Consider adding more large cap funds for stability.")
    if category_allocation.get("Debt", 0) < 10:
        suggestions.append("Add debt funds for portfolio stability and emergency needs.")
    if len(funds) < 4:
        suggestions.append("Consider diversifying with more fund categories.")
    if overall_returns_percent > 20:
        suggestions.append("Great returns! Consider booking partial profits.")
    
    return MFPortfolioResponse(
        funds=funds,
        total_invested=total_invested,
        total_current_value=total_current,
        overall_returns=overall_returns,
        overall_returns_percent=round(overall_returns_percent, 2),
        category_allocation=category_allocation,
        risk_analysis={
            "score": round(risk_score, 2),
            "level": risk_level,
            "description": f"Your portfolio has {risk_level.lower()} risk exposure based on category allocation."
        },
        suggestions=suggestions
    )

@api_router.post("/mf-portfolio/fund")
async def add_fund(fund: MutualFund, current_user: dict = Depends(get_current_user)):
    result = await db.mf_portfolios.update_one(
        {"user_id": current_user["id"]},
        {"$push": {"funds": fund.model_dump()}},
        upsert=True
    )
    return {"message": "Fund added", "fund": fund}

@api_router.delete("/mf-portfolio/fund/{fund_id}")
async def delete_fund(fund_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.mf_portfolios.update_one(
        {"user_id": current_user["id"]},
        {"$pull": {"funds": {"id": fund_id}}}
    )
    return {"message": "Fund deleted"}

# ============== HEALTH SCORE ==============

@api_router.get("/health-score")
async def get_health_score(current_user: dict = Depends(get_current_user)):
    income = current_user.get("income", 0)
    expenses = current_user.get("expenses", 0)
    savings = current_user.get("savings", 0)
    
    # Calculate savings rate
    savings_rate = ((income - expenses) / income * 100) if income > 0 else 0
    
    # Score components (0-100 each)
    
    # 1. Savings Rate Score (40% weight)
    if savings_rate >= 30:
        savings_score = 100
    elif savings_rate >= 20:
        savings_score = 80
    elif savings_rate >= 10:
        savings_score = 60
    elif savings_rate > 0:
        savings_score = 40
    else:
        savings_score = 20
    
    # 2. Emergency Fund Score (30% weight)
    monthly_expenses = expenses
    emergency_months = (savings / monthly_expenses) if monthly_expenses > 0 else 0
    if emergency_months >= 6:
        emergency_score = 100
    elif emergency_months >= 3:
        emergency_score = 70
    elif emergency_months >= 1:
        emergency_score = 40
    else:
        emergency_score = 20
    
    # 3. Expense Ratio Score (30% weight)
    expense_ratio = (expenses / income * 100) if income > 0 else 100
    if expense_ratio <= 50:
        expense_score = 100
    elif expense_ratio <= 70:
        expense_score = 70
    elif expense_ratio <= 90:
        expense_score = 40
    else:
        expense_score = 20
    
    # Weighted total
    total_score = (savings_score * 0.4 + emergency_score * 0.3 + expense_score * 0.3)
    
    # Determine grade
    if total_score >= 80:
        grade = "Excellent"
        color = "#10b981"
    elif total_score >= 60:
        grade = "Good"
        color = "#3b82f6"
    elif total_score >= 40:
        grade = "Fair"
        color = "#f59e0b"
    else:
        grade = "Needs Improvement"
        color = "#ef4444"
    
    # Tips based on scores
    tips = []
    if savings_score < 80:
        tips.append("Aim to save at least 20% of your income")
    if emergency_score < 70:
        tips.append("Build an emergency fund of 6 months expenses")
    if expense_score < 70:
        tips.append("Review and reduce unnecessary expenses")
    if total_score >= 80:
        tips.append("Great job! Consider increasing investments")
    
    return {
        "score": round(total_score, 1),
        "grade": grade,
        "color": color,
        "savings_rate": round(savings_rate, 1),
        "emergency_months": round(emergency_months, 1),
        "expense_ratio": round(expense_ratio, 1),
        "breakdown": {
            "savings": {"score": savings_score, "weight": 40},
            "emergency": {"score": emergency_score, "weight": 30},
            "expense": {"score": expense_score, "weight": 30}
        },
        "tips": tips
    }

# ============== ROOT ROUTES ==============

@api_router.get("/")
async def root():
    return {"message": "AI Money Mentor API", "version": "2.0.0"}

# ============== EXPENSE TRACKER ==============

class Expense(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    amount: float
    category: str
    description: Optional[str] = None
    date: str
    payment_method: Optional[str] = "Cash"

class ExpenseCreate(BaseModel):
    amount: float
    category: str
    description: Optional[str] = None
    date: Optional[str] = None
    payment_method: Optional[str] = "Cash"

EXPENSE_CATEGORIES = [
    {"name": "Food & Dining", "icon": "utensils", "color": "#ef4444"},
    {"name": "Transportation", "icon": "car", "color": "#f59e0b"},
    {"name": "Shopping", "icon": "shopping-bag", "color": "#8b5cf6"},
    {"name": "Entertainment", "icon": "film", "color": "#ec4899"},
    {"name": "Bills & Utilities", "icon": "zap", "color": "#3b82f6"},
    {"name": "Healthcare", "icon": "heart", "color": "#10b981"},
    {"name": "Education", "icon": "book", "color": "#06b6d4"},
    {"name": "Travel", "icon": "plane", "color": "#6366f1"},
    {"name": "Groceries", "icon": "shopping-cart", "color": "#84cc16"},
    {"name": "Rent", "icon": "home", "color": "#14b8a6"},
    {"name": "Insurance", "icon": "shield", "color": "#0ea5e9"},
    {"name": "Investments", "icon": "trending-up", "color": "#22c55e"},
    {"name": "Other", "icon": "more-horizontal", "color": "#71717a"},
]

@api_router.get("/expense-categories")
async def get_expense_categories():
    return {"categories": EXPENSE_CATEGORIES}

@api_router.post("/expenses")
async def add_expense(expense: ExpenseCreate, current_user: dict = Depends(get_current_user)):
    expense_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "amount": expense.amount,
        "category": expense.category,
        "description": expense.description,
        "date": expense.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "payment_method": expense.payment_method,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.expenses.insert_one(expense_doc)
    if "_id" in expense_doc:
        del expense_doc["_id"]
    return {"message": "Expense added", "expense": expense_doc}

@api_router.get("/expenses")
async def get_expenses(
    month: Optional[str] = None,
    year: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {"user_id": current_user["id"]}
    
    # Filter by month/year if provided
    if month and year:
        start_date = f"{year}-{month.zfill(2)}-01"
        if int(month) == 12:
            end_date = f"{int(year)+1}-01-01"
        else:
            end_date = f"{year}-{str(int(month)+1).zfill(2)}-01"
        query["date"] = {"$gte": start_date, "$lt": end_date}
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    
    # Calculate category totals
    category_totals = {}
    total = 0
    for exp in expenses:
        cat = exp.get("category", "Other")
        category_totals[cat] = category_totals.get(cat, 0) + exp["amount"]
        total += exp["amount"]
    
    # Format for pie chart
    chart_data = [
        {"name": cat, "value": amount, "percentage": round(amount/total*100, 1) if total > 0 else 0}
        for cat, amount in category_totals.items()
    ]
    
    return {
        "expenses": expenses,
        "total": total,
        "category_totals": category_totals,
        "chart_data": chart_data
    }

@api_router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.expenses.delete_one({"id": expense_id, "user_id": current_user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted"}

# ============== GOAL-BASED SIP CALCULATOR ==============

class GoalSIPRequest(BaseModel):
    goal_name: str
    target_amount: float
    current_savings: float = 0
    time_horizon_years: int
    expected_returns: float = 12.0
    inflation_rate: float = 6.0
    step_up_percent: float = 0  # Annual SIP increase

class GoalSIPResponse(BaseModel):
    goal_name: str
    target_amount: float
    inflation_adjusted_target: float
    current_savings: float
    future_value_current: float
    gap: float
    required_monthly_sip: float
    total_investment: float
    total_returns: float
    time_horizon_years: int
    year_wise_projection: List[dict]

@api_router.post("/goal-sip-calculator", response_model=GoalSIPResponse)
async def calculate_goal_sip(data: GoalSIPRequest, current_user: dict = Depends(get_current_user)):
    # Inflation adjusted target
    inflation_factor = (1 + data.inflation_rate / 100) ** data.time_horizon_years
    inflation_adjusted_target = data.target_amount * inflation_factor
    
    # Future value of current savings
    annual_return = data.expected_returns / 100
    fv_current = data.current_savings * ((1 + annual_return) ** data.time_horizon_years)
    
    # Gap to fill
    gap = max(0, inflation_adjusted_target - fv_current)
    
    # Calculate required SIP
    monthly_rate = annual_return / 12
    months = data.time_horizon_years * 12
    
    if data.step_up_percent > 0:
        # Step-up SIP calculation (approximate)
        step_up_rate = data.step_up_percent / 100
        # Using formula for increasing SIP
        required_sip = gap / (
            sum([(1 + step_up_rate) ** (y) * 
                 (((1 + monthly_rate) ** (12 * (data.time_horizon_years - y)) - 1) / monthly_rate) * (1 + monthly_rate)
                 for y in range(data.time_horizon_years)])
        ) if gap > 0 else 0
    else:
        # Regular SIP calculation
        if monthly_rate > 0 and months > 0:
            required_sip = gap / ((((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate))
        else:
            required_sip = gap / months if months > 0 else gap
    
    required_sip = max(0, required_sip)
    
    # Year-wise projection
    projections = []
    current_value = data.current_savings
    total_sip_invested = 0
    yearly_sip = required_sip * 12
    
    for year in range(1, data.time_horizon_years + 1):
        # Apply step-up
        if data.step_up_percent > 0 and year > 1:
            yearly_sip *= (1 + data.step_up_percent / 100)
        
        monthly_sip = yearly_sip / 12
        
        # Calculate year-end value
        year_start = current_value
        for month in range(12):
            current_value = current_value * (1 + monthly_rate) + monthly_sip
            total_sip_invested += monthly_sip
        
        projections.append({
            "year": year,
            "age": (current_user.get("age", 25) or 25) + year,
            "sip_amount": round(monthly_sip, 0),
            "year_investment": round(yearly_sip, 0),
            "total_invested": round(total_sip_invested + data.current_savings, 0),
            "corpus_value": round(current_value, 0),
            "target_progress": round(current_value / inflation_adjusted_target * 100, 1)
        })
    
    total_investment = total_sip_invested + data.current_savings
    total_returns = current_value - total_investment
    
    return GoalSIPResponse(
        goal_name=data.goal_name,
        target_amount=data.target_amount,
        inflation_adjusted_target=round(inflation_adjusted_target, 0),
        current_savings=data.current_savings,
        future_value_current=round(fv_current, 0),
        gap=round(gap, 0),
        required_monthly_sip=round(required_sip, 0),
        total_investment=round(total_investment, 0),
        total_returns=round(total_returns, 0),
        time_horizon_years=data.time_horizon_years,
        year_wise_projection=projections
    )

# ============== LINKED BANK ACCOUNTS (Mock) ==============

class LinkedAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bank_name: str
    account_type: str  # savings, current, credit_card
    account_number_masked: str
    balance: float
    last_synced: str
    status: str = "active"

class LinkAccountRequest(BaseModel):
    bank_name: str
    account_type: str
    account_number: str  # Will be masked

# Mock bank data
MOCK_BANKS = [
    {"name": "HDFC Bank", "logo": "hdfc", "supports_upi": True},
    {"name": "ICICI Bank", "logo": "icici", "supports_upi": True},
    {"name": "SBI", "logo": "sbi", "supports_upi": True},
    {"name": "Axis Bank", "logo": "axis", "supports_upi": True},
    {"name": "Kotak Mahindra Bank", "logo": "kotak", "supports_upi": True},
    {"name": "Yes Bank", "logo": "yes", "supports_upi": True},
    {"name": "Punjab National Bank", "logo": "pnb", "supports_upi": True},
    {"name": "Bank of Baroda", "logo": "bob", "supports_upi": True},
]

@api_router.get("/banks")
async def get_supported_banks():
    return {"banks": MOCK_BANKS}

@api_router.post("/linked-accounts")
async def link_bank_account(data: LinkAccountRequest, current_user: dict = Depends(get_current_user)):
    # Mask account number
    masked = "XXXX" + data.account_number[-4:] if len(data.account_number) >= 4 else "XXXX"
    
    # Generate mock balance
    import random
    mock_balance = round(random.uniform(10000, 500000), 2)
    
    account_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "bank_name": data.bank_name,
        "account_type": data.account_type,
        "account_number_masked": masked,
        "balance": mock_balance,
        "last_synced": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.linked_accounts.insert_one(account_doc)
    if "_id" in account_doc:
        del account_doc["_id"]
    
    return {"message": "Account linked successfully", "account": account_doc}

@api_router.get("/linked-accounts")
async def get_linked_accounts(current_user: dict = Depends(get_current_user)):
    accounts = await db.linked_accounts.find(
        {"user_id": current_user["id"]}, 
        {"_id": 0}
    ).to_list(100)
    
    total_balance = sum(acc.get("balance", 0) for acc in accounts)
    
    return {"accounts": accounts, "total_balance": total_balance}

@api_router.delete("/linked-accounts/{account_id}")
async def unlink_account(account_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.linked_accounts.delete_one({
        "id": account_id, 
        "user_id": current_user["id"]
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account unlinked"}

@api_router.post("/linked-accounts/{account_id}/sync")
async def sync_account(account_id: str, current_user: dict = Depends(get_current_user)):
    # Mock sync - update balance with random change
    import random
    change = round(random.uniform(-5000, 10000), 2)
    
    account = await db.linked_accounts.find_one({
        "id": account_id,
        "user_id": current_user["id"]
    })
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    new_balance = max(0, account.get("balance", 0) + change)
    
    await db.linked_accounts.update_one(
        {"id": account_id},
        {"$set": {
            "balance": new_balance,
            "last_synced": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Account synced", "new_balance": new_balance}

# ============== FINANCIAL REPORT ==============

@api_router.get("/financial-report")
async def generate_financial_report(current_user: dict = Depends(get_current_user)):
    """Generate comprehensive financial report data"""
    
    user = current_user
    
    # Get health score
    income = user.get("income", 0)
    expenses_monthly = user.get("expenses", 0)
    savings = user.get("savings", 0)
    
    savings_rate = ((income - expenses_monthly) / income * 100) if income > 0 else 0
    emergency_months = (savings / expenses_monthly) if expenses_monthly > 0 else 0
    
    # Get FIRE data
    fire_data = None
    if expenses_monthly > 0:
        years_to_fire = 45 - (user.get("age", 25) or 25)
        if years_to_fire > 0:
            annual_expenses = expenses_monthly * 12
            inflation_factor = (1.06) ** years_to_fire
            future_expenses = annual_expenses * inflation_factor
            fire_corpus = future_expenses * 25
            
            monthly_sip = (income - expenses_monthly) * 0.5
            monthly_rate = 0.12 / 12
            months = years_to_fire * 12
            
            fv_savings = savings * (1.12 ** years_to_fire)
            fv_sip = monthly_sip * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate) if monthly_rate > 0 else monthly_sip * months
            projected_wealth = fv_savings + fv_sip
            
            fire_data = {
                "fire_corpus_needed": round(fire_corpus, 0),
                "projected_wealth": round(projected_wealth, 0),
                "years_to_fire": years_to_fire,
                "on_track": projected_wealth >= fire_corpus
            }
    
    # Get expenses summary
    expenses = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(1000)
    expense_by_category = {}
    for exp in expenses:
        cat = exp.get("category", "Other")
        expense_by_category[cat] = expense_by_category.get(cat, 0) + exp["amount"]
    
    # Get MF portfolio
    portfolio = await db.mf_portfolios.find_one({"user_id": user["id"]}, {"_id": 0})
    mf_data = None
    if portfolio and portfolio.get("funds"):
        funds = portfolio["funds"]
        total_invested = sum(f["invested_amount"] for f in funds)
        total_current = sum(f["current_value"] for f in funds)
        mf_data = {
            "total_invested": total_invested,
            "total_current_value": total_current,
            "returns": total_current - total_invested,
            "returns_percent": round((total_current - total_invested) / total_invested * 100, 2) if total_invested > 0 else 0,
            "fund_count": len(funds)
        }
    
    # Get life events
    life_events = await db.life_events.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    
    # Get linked accounts
    linked_accounts = await db.linked_accounts.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    total_bank_balance = sum(acc.get("balance", 0) for acc in linked_accounts)
    
    # Calculate net worth
    net_worth = savings + total_bank_balance
    if mf_data:
        net_worth += mf_data["total_current_value"]
    
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "name": user.get("name", "User"),
            "age": user.get("age", 25),
            "email": user.get("email", "")
        },
        "summary": {
            "net_worth": round(net_worth, 0),
            "monthly_income": income,
            "monthly_expenses": expenses_monthly,
            "savings_rate": round(savings_rate, 1),
            "emergency_fund_months": round(emergency_months, 1),
            "current_savings": savings,
            "bank_balance": round(total_bank_balance, 0)
        },
        "health_score": {
            "score": round(min(100, savings_rate * 2 + emergency_months * 5), 0),
            "savings_rate": round(savings_rate, 1),
            "emergency_months": round(emergency_months, 1)
        },
        "fire_status": fire_data,
        "expense_breakdown": expense_by_category,
        "investments": mf_data,
        "life_goals": [
            {
                "event_type": e.get("event_type"),
                "target": e.get("estimated_cost"),
                "saved": e.get("current_savings"),
                "target_date": e.get("target_date")
            } for e in life_events
        ],
        "linked_accounts_count": len(linked_accounts)
    }
    
    return report

# ============== REAL MF DATA (AMFI) ==============

@api_router.get("/mf-search")
async def search_mutual_funds(query: str = "", category: str = ""):
    """Search mutual funds from AMFI data"""
    
    # Pre-defined popular funds with real NAV approximations
    POPULAR_FUNDS = [
        {"scheme_code": "119551", "name": "Axis Bluechip Fund - Direct Growth", "category": "Large Cap", "nav": 52.34, "aum": 35000, "rating": 5},
        {"scheme_code": "120503", "name": "Mirae Asset Large Cap Fund - Direct Growth", "category": "Large Cap", "nav": 89.67, "aum": 42000, "rating": 5},
        {"scheme_code": "118989", "name": "SBI Bluechip Fund - Direct Growth", "category": "Large Cap", "nav": 73.21, "aum": 38000, "rating": 4},
        {"scheme_code": "125354", "name": "HDFC Index Fund Nifty 50 - Direct Growth", "category": "Index", "nav": 178.45, "aum": 12000, "rating": 5},
        {"scheme_code": "120505", "name": "UTI Nifty Index Fund - Direct Growth", "category": "Index", "nav": 134.56, "aum": 15000, "rating": 5},
        {"scheme_code": "122639", "name": "Axis Midcap Fund - Direct Growth", "category": "Mid Cap", "nav": 78.90, "aum": 22000, "rating": 5},
        {"scheme_code": "125497", "name": "Kotak Emerging Equity Fund - Direct Growth", "category": "Mid Cap", "nav": 85.34, "aum": 28000, "rating": 4},
        {"scheme_code": "125494", "name": "HDFC Mid-Cap Opportunities Fund - Direct Growth", "category": "Mid Cap", "nav": 112.45, "aum": 45000, "rating": 4},
        {"scheme_code": "125307", "name": "Axis Small Cap Fund - Direct Growth", "category": "Small Cap", "nav": 78.23, "aum": 18000, "rating": 5},
        {"scheme_code": "125356", "name": "SBI Small Cap Fund - Direct Growth", "category": "Small Cap", "nav": 145.67, "aum": 25000, "rating": 5},
        {"scheme_code": "119568", "name": "Nippon India Small Cap Fund - Direct Growth", "category": "Small Cap", "nav": 134.89, "aum": 35000, "rating": 4},
        {"scheme_code": "119062", "name": "ICICI Prudential Balanced Advantage Fund - Direct Growth", "category": "Balanced", "nav": 56.78, "aum": 52000, "rating": 4},
        {"scheme_code": "118834", "name": "HDFC Balanced Advantage Fund - Direct Growth", "category": "Balanced", "nav": 345.23, "aum": 65000, "rating": 4},
        {"scheme_code": "119784", "name": "Parag Parikh Flexi Cap Fund - Direct Growth", "category": "Flexi Cap", "nav": 62.45, "aum": 48000, "rating": 5},
        {"scheme_code": "118778", "name": "HDFC Flexi Cap Fund - Direct Growth", "category": "Flexi Cap", "nav": 456.78, "aum": 42000, "rating": 4},
        {"scheme_code": "120716", "name": "ICICI Prudential Corporate Bond Fund - Direct Growth", "category": "Debt", "nav": 25.67, "aum": 22000, "rating": 4},
        {"scheme_code": "119237", "name": "HDFC Corporate Bond Fund - Direct Growth", "category": "Debt", "nav": 28.34, "aum": 28000, "rating": 4},
        {"scheme_code": "120837", "name": "Axis Liquid Fund - Direct Growth", "category": "Liquid", "nav": 2456.78, "aum": 35000, "rating": 5},
        {"scheme_code": "118560", "name": "HDFC Liquid Fund - Direct Growth", "category": "Liquid", "nav": 4523.45, "aum": 55000, "rating": 5},
        {"scheme_code": "101079", "name": "Quant Small Cap Fund - Direct Growth", "category": "Small Cap", "nav": 198.45, "aum": 8000, "rating": 5},
    ]
    
    results = POPULAR_FUNDS
    
    # Filter by query
    if query:
        query_lower = query.lower()
        results = [f for f in results if query_lower in f["name"].lower()]
    
    # Filter by category
    if category:
        results = [f for f in results if f["category"].lower() == category.lower()]
    
    return {"funds": results, "total": len(results)}

@api_router.get("/mf-nav/{scheme_code}")
async def get_fund_nav(scheme_code: str):
    """Get NAV for a specific fund"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.mfapi.in/mf/{scheme_code}",
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "scheme_code": scheme_code,
                    "name": data.get("meta", {}).get("scheme_name", "Unknown"),
                    "nav": float(data.get("data", [{}])[0].get("nav", 0)),
                    "date": data.get("data", [{}])[0].get("date", ""),
                    "category": data.get("meta", {}).get("scheme_category", ""),
                    "fund_house": data.get("meta", {}).get("fund_house", "")
                }
    except Exception as e:
        logger.error(f"Error fetching NAV: {e}")
    
    raise HTTPException(status_code=404, detail="Fund not found")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
