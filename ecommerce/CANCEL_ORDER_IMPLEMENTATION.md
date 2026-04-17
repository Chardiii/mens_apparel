# Order Cancellation System - Implementation Summary

## What Changed

### 1. Database Schema (`models/order.py`)
Added 3 new columns to the `orders` table:
- `cancel_reason` (VARCHAR 500) - Stores the reason for cancellation
- `cancel_requested_by` (VARCHAR 10) - Tracks who initiated: 'buyer', 'seller', or 'admin'
- `cancel_status` (VARCHAR 10) - Approval status: 'pending', 'approved', 'rejected'

Added new order status:
- `CANCEL_REQUESTED` - Buyer requested cancellation, awaiting seller review

### 2. Business Logic (`routes/orders.py`)

**Buyer Cancellation Flow:**
- Buyer can request cancellation ONLY if order status is `pending` or `verified`
- Buyer CANNOT cancel if order is `shipped`, `assigned`, or `delivered`
- Cancellation request requires a reason (max 500 chars)
- Order status changes to `cancel_requested` - NO stock restored yet
- Seller receives notification to approve/reject

**Seller Approval:**
- Seller reviews the buyer's reason
- If approved: Stock is restored, order status → `cancelled`
- If rejected: Order reverts to `pending`, buyer is notified

**Seller Direct Cancel:**
- Seller can cancel orders at `pending` or `verified` stage
- Immediate cancellation - stock restored right away
- Optional reason field

**Stock Restoration Logic:**
- Properly handles variant-level stock restoration
- Parent product stock is synced as sum of all variant stocks
- Prevents stock drift between parent and variants

### 3. New Routes
- `POST /orders/<id>/cancel` - Buyer requests or seller directly cancels
- `POST /orders/<id>/approve-cancel` - Seller approves buyer's request
- `POST /orders/<id>/reject-cancel` - Seller rejects buyer's request

### 4. UI Updates

**order_detail.html:**
- Buyer sees "Request Cancellation" button (opens modal with reason field)
- Shows "Cancellation Requested" banner when pending seller review
- Locked state for shipped/delivered orders
- Seller sees approve/reject buttons for pending cancel requests
- Displays cancel reason and who cancelled in the cancelled state

**seller_orders.html:**
- Shows "Approve Cancel" and "Reject" buttons for `cancel_requested` orders
- Inline actions in the orders table

**Modals Added:**
- Buyer cancel request modal (requires reason)
- Seller direct cancel modal (optional reason)
- Seller reject cancel modal (optional rejection reason)

## Security & Data Integrity

✅ **Stock sync fixed** - Variant stock and parent stock stay in sync
✅ **Authorization checks** - Only authorized users can cancel/approve
✅ **Status validation** - Prevents cancellation at wrong stages
✅ **Audit trail** - Tracks who requested, who approved, and reasons

## Testing Checklist

- [ ] Buyer requests cancel on pending order → seller sees request
- [ ] Seller approves cancel → stock restored correctly
- [ ] Seller rejects cancel → order resumes, buyer notified
- [ ] Buyer cannot cancel shipped order → blocked with message
- [ ] Seller direct cancel → immediate, stock restored
- [ ] Variant stock sync → parent stock = sum of variants after restore
- [ ] Email notifications sent for all status changes

## Migration

Run: `python migrate_cancel.py` (already executed)

Adds the 3 new columns to existing `orders` table.
