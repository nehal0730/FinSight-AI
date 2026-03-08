"""
Test the fixed amount extraction with multi-column bank statements
"""
from app.services.transaction_extractor import TransactionExtractor


def test_multi_column_amounts():
    """Test that we extract the correct amount when there are multiple numbers"""
    
    # Simulate the HDFC bank statement format:
    # Date | Description | Ref No | Debit | Credit | Balance
    test_cases = [
        # Format: "Date Description RefNo Amount Balance"
        {
            "line": "01-02-2026 NEFT INTEREST CREDIT 919919523 1200.00 53200.00",
            "expected_amount": 1200.00,
            "description": "Should pick debit/credit amount, not ref number or balance"
        },
        {
            "line": "01-02-2026 UPI/FLIPKART/online 489156581 1425.73 51774.27",
            "expected_amount": 1425.73,
            "description": "Should pick transaction amount, not large ref ID or balance"
        },
        {
            "line": "22-02-2026 CRYPTO EXCHANGE PURCHASE 118855823 3602.46 10500.72",
            "expected_amount": 3602.46,
            "description": "Should handle crypto transactions correctly"
        },
        {
            "line": "23-02-2026 SALARY CREDIT TECHCORP PVT LTD 751486575 1200.00 65419.73",
            "expected_amount": 1200.00,
            "description": "Should extract salary amount correctly"
        },
    ]
    
    extractor = TransactionExtractor()
    
    print("="*70)
    print("Testing Multi-Column Amount Extraction Fix")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        line = test["line"]
        expected = test["expected_amount"]
        desc = test["description"]
        
        transactions = extractor.extract_transactions(line)
        
        if transactions:
            actual = transactions[0]["amount"]
            if actual == expected:
                print(f"\n[OK] Test {i}: {desc}")
                print(f"     Line: {line[:60]}...")
                print(f"     Expected: Rs.{expected:,.2f}, Got: Rs.{actual:,.2f}")
                passed += 1
            else:
                print(f"\n[FAIL] Test {i}: {desc}")
                print(f"       Line: {line[:60]}...")
                print(f"       Expected: Rs.{expected:,.2f}, Got: Rs.{actual:,.2f}")
                failed += 1
        else:
            print(f"\n[FAIL] Test {i}: No transactions extracted")
            print(f"       Line: {line[:60]}...")
            failed += 1
    
    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = test_multi_column_amounts()
    exit(0 if success else 1)
