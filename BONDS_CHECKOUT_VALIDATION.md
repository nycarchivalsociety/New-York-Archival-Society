# Bonds Checkout End-to-End Validation Checklist

## Overview
This document provides a comprehensive checklist for validating all Bonds checkout scenarios including shipping, pickup, and international order flows.

## Test Environment Setup
- [ ] Ensure PayPal sandbox credentials are configured
- [ ] Verify EmailJS is properly configured
- [ ] Confirm database has test bonds available
- [ ] Open browser developer console to monitor network requests

---

## ✅ Test Scenario 1: US Address + Pickup Checked

### Steps:
1. Navigate to `/bonds` and select any available bond
2. Check the "In-person pickup" checkbox
3. Click PayPal button and proceed with checkout
4. Use a US-based PayPal test account
5. Complete the payment

### Expected Results:
- [ ] **UI Display:**
  - [ ] Handling fee text (`+ $5 Handling Cost`) is HIDDEN
  - [ ] International fee text (`+ $20 International Shipping`) is HIDDEN
  - [ ] Only base price is shown (e.g., $100)

- [ ] **PayPal Order:**
  - [ ] Order total equals base price only
  - [ ] No handling or shipping fees in breakdown
  - [ ] Shipping address is still collected (for validation)

- [ ] **Order Capture:**
  - [ ] Transaction completes successfully
  - [ ] Success message displayed
  - [ ] Bond status changes to "purchased"

- [ ] **Email Notification:**
  - [ ] Email subject: "Bond Purchase!"
  - [ ] Total amount shows base price only ($100)
  - [ ] Pickup status shows: "IN-PERSON PICKUP"
  - [ ] Shipping address marked as "N/A (In-person pickup)"

---

## ✅ Test Scenario 2: US Address + Pickup Unchecked

### Steps:
1. Navigate to `/bonds` and select any available bond
2. Leave "In-person pickup" checkbox UNCHECKED
3. Click PayPal button and proceed with checkout
4. Use a US-based PayPal test account
5. Complete the payment

### Expected Results:
- [ ] **UI Display:**
  - [ ] Handling fee text (`+ $5 Handling Cost`) is VISIBLE
  - [ ] International fee text (`+ $20 International Shipping`) is HIDDEN
  - [ ] Total shown: Base price + $5

- [ ] **PayPal Order:**
  - [ ] Order total equals base + $5 handling
  - [ ] Breakdown shows:
    - Item total: $100
    - Handling: $5
    - Shipping: $0

- [ ] **Order Capture:**
  - [ ] Transaction completes successfully
  - [ ] Total captured: $105

- [ ] **Email Notification:**
  - [ ] Total amount shows $105
  - [ ] Pickup status shows: "SHIPPING REQUIRED"
  - [ ] Full shipping address included

---

## ✅ Test Scenario 3: Non-US Address + Pickup Unchecked

### Steps:
1. Navigate to `/bonds` and select any available bond
2. Leave "In-person pickup" checkbox UNCHECKED
3. Click PayPal button
4. In PayPal, change shipping country to non-US (e.g., UK, Canada, France)
5. Complete the payment

### Expected Results:
- [ ] **UI Display (after country change):**
  - [ ] Handling fee text (`+ $5 Handling Cost`) is VISIBLE
  - [ ] International fee text (`+ $20 International Shipping`) is VISIBLE
  - [ ] Total dynamically updates to: Base + $5 + $20 = $125

- [ ] **PayPal Order Patching:**
  - [ ] Order automatically patches when country changes
  - [ ] New total: $125
  - [ ] Breakdown shows:
    - Item total: $100
    - Handling: $5
    - Shipping: $20

- [ ] **Order Capture:**
  - [ ] Transaction completes with $125 total
  - [ ] International shipping properly recorded

- [ ] **Email Notification:**
  - [ ] Total amount shows $125
  - [ ] International shipping fee reflected
  - [ ] Full international address included

---

## ❌ Test Scenario 4: Non-US Address + Pickup Checked (Should Block)

### Steps:
1. Navigate to `/bonds` and select any available bond
2. CHECK the "In-person pickup" checkbox
3. Click PayPal button
4. In PayPal, attempt to change shipping country to non-US

### Expected Results:
- [ ] **Validation Error:**
  - [ ] SweetAlert popup appears immediately
  - [ ] Title: "Invalid Shipping Country" or "In-person pickup restricted"
  - [ ] Message explains pickup is USA-only
  - [ ] Orange confirm button (#EC994B color)

- [ ] **Order Blocking:**
  - [ ] PayPal order is rejected (`actions.reject()` called)
  - [ ] User cannot proceed with non-US address
  - [ ] Must either:
    - Uncheck pickup option, OR
    - Change back to US address

- [ ] **Console Logs:**
  - [ ] "Rejecting non-US address for in-person pickup" logged
  - [ ] No errors in console

---

## 📱 Test Scenario 5: Mobile Responsiveness

### Steps:
1. Open browser developer tools
2. Toggle device toolbar (mobile view)
3. Test each viewport:
   - iPhone SE (375px)
   - iPad (768px)
   - Desktop (1920px)
4. Navigate through bond purchase flow

### Expected Results:
- [ ] **All Viewports:**
  - [ ] PayPal button properly sized
  - [ ] Pickup checkbox accessible
  - [ ] Fee text readable
  - [ ] No horizontal scrolling
  - [ ] All modals/alerts properly centered

---

## 💳 Test Scenario 6: Dynamic Price Updates

### Steps:
1. Open bond details page
2. Monitor the price display while:
   - Toggling pickup checkbox
   - Changing countries in PayPal
   - Switching between US and international addresses

### Expected Results:
- [ ] **Price Updates:**
  - [ ] Immediate UI updates when pickup toggled
  - [ ] Smooth transitions when fees appear/disappear
  - [ ] PayPal order patches successfully
  - [ ] No price mismatches

---

## 📧 Test Scenario 7: Email Content Validation

### For Each Scenario Above:
- [ ] **Email Template Parameters:**
  ```
  - subject: "Bond Purchase!"
  - item_name: [Bond Type]
  - item_fee: [Total including fees]
  - pickup_status: "IN-PERSON PICKUP" or "SHIPPING REQUIRED"
  - base_price: $100
  - handling_fee: $0 or $5
  - shipping_fee: $0 or $20
  - total_paid: [Actual amount charged]
  ```

- [ ] **Recipient List:**
  - [ ] All configured admin emails receive notification
  - [ ] Customer receives confirmation

---

## 🔧 Technical Validation

### JavaScript Console Checks:
```javascript
// Run these in console during testing

// 1. Check if pickup is selected
document.getElementById("pickup-checkbox").checked

// 2. Verify fee display states
document.getElementById("handling-text").style.display
document.getElementById("international-text").style.display

// 3. Monitor PayPal patches
// Watch Network tab for PATCH requests to PayPal API
```

### Database Verification:
```sql
-- Check transaction records
SELECT * FROM transactions WHERE item_id = '[BOND_ID]' ORDER BY created_at DESC;

-- Verify bond status
SELECT bond_id, status FROM bonds WHERE bond_id = '[BOND_ID]';

-- Check donor information
SELECT * FROM donors WHERE donor_email = '[TEST_EMAIL]';
```

---

## 🐛 Common Issues to Watch For

1. **Fee Display Bugs:**
   - [ ] Fees not hiding when pickup selected
   - [ ] International fee showing for US addresses
   - [ ] Both fees showing simultaneously (should be either/or)

2. **PayPal Integration:**
   - [ ] Order patch failures
   - [ ] Incorrect total calculations
   - [ ] Missing onShippingChange callback

3. **Validation Issues:**
   - [ ] Non-US + pickup not being rejected
   - [ ] Error messages not displaying
   - [ ] Order completing despite validation failure

4. **Email Issues:**
   - [ ] Incorrect totals in email
   - [ ] Missing pickup status
   - [ ] Wrong fee breakdown

---

## 📋 Sign-off Checklist

### All Scenarios Tested:
- [ ] US + Pickup ✅
- [ ] US + Shipping ✅
- [ ] International + Shipping ✅
- [ ] International + Pickup (Blocked) ✅
- [ ] Mobile Responsiveness ✅
- [ ] Email Accuracy ✅

### Final Verification:
- [ ] No console errors during any flow
- [ ] All fees calculate correctly
- [ ] Database records accurate
- [ ] Email notifications sent properly
- [ ] UI responsive on all devices

---

## Test Data

### PayPal Sandbox Test Accounts:
- US Buyer: `sb-buyer-us@example.com`
- UK Buyer: `sb-buyer-uk@example.com`
- Personal: Use your sandbox personal account

### Test Addresses:
```
US Address:
123 Main Street
New York, NY 10001
United States

UK Address:
10 Downing Street
London, SW1A 2AA
United Kingdom

French Address:
123 Rue de la Paix
75001 Paris
France
```

---

## Notes
- Always test in PayPal Sandbox mode first
- Clear browser cache between test scenarios if experiencing issues
- Monitor browser console for any JavaScript errors
- Check network tab for failed API calls

---

**Testing Completed By:** _________________  
**Date:** _________________  
**Version:** _________________
