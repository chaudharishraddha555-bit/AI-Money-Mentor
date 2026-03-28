import requests
import sys
import json
from datetime import datetime

class AIMoneyMentorTester:
    def __init__(self, base_url="https://ai-budget-coach-1.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.text else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json() if response.text else {}
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self):
        """Test login with test user"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": "test@example.com", "password": "test123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response.get('user', {}).get('id')
            print(f"   Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_expense_categories(self):
        """Test expense categories endpoint"""
        success, response = self.run_test(
            "Get Expense Categories",
            "GET",
            "expense-categories",
            200
        )
        if success and 'categories' in response:
            categories = response['categories']
            print(f"   Found {len(categories)} categories")
            return True
        return False

    def test_add_expense(self):
        """Test adding an expense"""
        expense_data = {
            "amount": 500.0,
            "category": "Food & Dining",
            "description": "Test lunch expense",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "payment_method": "UPI"
        }
        success, response = self.run_test(
            "Add Expense",
            "POST",
            "expenses",
            200,
            data=expense_data
        )
        if success and 'expense' in response:
            expense_id = response['expense'].get('id')
            print(f"   Expense created with ID: {expense_id}")
            return expense_id
        return None

    def test_get_expenses(self):
        """Test getting expenses"""
        success, response = self.run_test(
            "Get Expenses",
            "GET",
            "expenses",
            200
        )
        if success:
            expenses = response.get('expenses', [])
            total = response.get('total', 0)
            chart_data = response.get('chart_data', [])
            print(f"   Found {len(expenses)} expenses, total: ₹{total}")
            print(f"   Chart data categories: {len(chart_data)}")
            return True
        return False

    def test_goal_sip_calculator(self):
        """Test Goal SIP Calculator"""
        sip_data = {
            "goal_name": "Test Child Education",
            "target_amount": 5000000,
            "current_savings": 100000,
            "time_horizon_years": 15,
            "expected_returns": 12.0,
            "inflation_rate": 6.0,
            "step_up_percent": 0
        }
        success, response = self.run_test(
            "Goal SIP Calculator",
            "POST",
            "goal-sip-calculator",
            200,
            data=sip_data
        )
        if success:
            required_sip = response.get('required_monthly_sip', 0)
            inflation_target = response.get('inflation_adjusted_target', 0)
            projections = response.get('year_wise_projection', [])
            print(f"   Required SIP: ₹{required_sip}/month")
            print(f"   Inflation adjusted target: ₹{inflation_target}")
            print(f"   Year-wise projections: {len(projections)} years")
            return True
        return False

    def test_banks(self):
        """Test supported banks endpoint"""
        success, response = self.run_test(
            "Get Supported Banks",
            "GET",
            "banks",
            200
        )
        if success and 'banks' in response:
            banks = response['banks']
            print(f"   Found {len(banks)} supported banks")
            return True
        return False

    def test_link_account(self):
        """Test linking a bank account"""
        account_data = {
            "bank_name": "HDFC Bank",
            "account_type": "savings",
            "account_number": "1234567890123456"
        }
        success, response = self.run_test(
            "Link Bank Account",
            "POST",
            "linked-accounts",
            200,
            data=account_data
        )
        if success and 'account' in response:
            account_id = response['account'].get('id')
            balance = response['account'].get('balance', 0)
            print(f"   Account linked with ID: {account_id}")
            print(f"   Mock balance: ₹{balance}")
            return account_id
        return None

    def test_get_linked_accounts(self):
        """Test getting linked accounts"""
        success, response = self.run_test(
            "Get Linked Accounts",
            "GET",
            "linked-accounts",
            200
        )
        if success:
            accounts = response.get('accounts', [])
            total_balance = response.get('total_balance', 0)
            print(f"   Found {len(accounts)} linked accounts")
            print(f"   Total balance: ₹{total_balance}")
            return True
        return False

    def test_financial_report(self):
        """Test financial report generation"""
        success, response = self.run_test(
            "Generate Financial Report",
            "GET",
            "financial-report",
            200
        )
        if success:
            user_data = response.get('user', {})
            summary = response.get('summary', {})
            health_score = response.get('health_score', {})
            print(f"   Report for user: {user_data.get('name', 'Unknown')}")
            print(f"   Net worth: ₹{summary.get('net_worth', 0)}")
            print(f"   Health score: {health_score.get('score', 0)}/100")
            return True
        return False

    def test_delete_expense(self, expense_id):
        """Test deleting an expense"""
        if not expense_id:
            return False
        success, response = self.run_test(
            "Delete Expense",
            "DELETE",
            f"expenses/{expense_id}",
            200
        )
        return success

    def test_unlink_account(self, account_id):
        """Test unlinking a bank account"""
        if not account_id:
            return False
        success, response = self.run_test(
            "Unlink Bank Account",
            "DELETE",
            f"linked-accounts/{account_id}",
            200
        )
        return success

def main():
    print("🚀 Starting AI Money Mentor API Tests")
    print("=" * 50)
    
    tester = AIMoneyMentorTester()
    
    # Test authentication first
    if not tester.test_login():
        print("❌ Login failed, stopping tests")
        return 1

    # Test Expense Tracker APIs
    print("\n📊 Testing Expense Tracker APIs")
    tester.test_expense_categories()
    expense_id = tester.test_add_expense()
    tester.test_get_expenses()
    
    # Test Goal SIP Calculator
    print("\n🎯 Testing Goal SIP Calculator")
    tester.test_goal_sip_calculator()
    
    # Test Linked Accounts APIs
    print("\n🏦 Testing Linked Accounts APIs")
    tester.test_banks()
    account_id = tester.test_link_account()
    tester.test_get_linked_accounts()
    
    # Test Financial Report
    print("\n📋 Testing Financial Report")
    tester.test_financial_report()
    
    # Cleanup - delete test data
    print("\n🧹 Cleanup")
    if expense_id:
        tester.test_delete_expense(expense_id)
    if account_id:
        tester.test_unlink_account(account_id)

    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Tests completed: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())