# System Architecture Document

## True Style – Online Clothing Store Backend (FastAPI)

**Version:** 1.0  
**Last Updated:** 10-Nov-2025

**Technology Stack:**  
- FastAPI  
- MongoDB (Primary Database for business data)  
- PostgreSQL (Logs + Contact Us)  
- GridFS (Product images, banners, testimonials, etc.)  
- Redis (Permission cache, session/token cache)  

---

## 1. Executive Summary

True Style is a full-stack backend system for a modern clothing e‑commerce platform.  
It enables customers to browse apparel, add products to carts/wishlists, place orders, make payments, manage returns/exchanges, and leave reviews/ratings.

The admin panel provides rich management including product catalog, orders, customers, content (banners, hero images, policies), coupons, payments, analytics, backups, and logs.

The system is built with **FastAPI**, supports **JWT Auth**, **RBAC**, **GridFS image storage**, **MongoDB transactions**, and **PostgreSQL** for application logs and contact messages.

---

## 2. System Overview

### 2.1 Purpose
- Secure, scalable e‑commerce backend  
- Customers can shop, pay, track orders, return/exchange  
- Admins manage entire clothing store operations  
- Content & catalog management  
- Analytics and data backup  

### 2.2 Key Features
✅ Authentication (Login, Register, OTP Forgot Password)  
✅ Wishlists & carts  
✅ Orders, payments, invoices  
✅ Returns, exchanges, refunds  
✅ Reviews & ratings  
✅ Coupons & promotions  
✅ CMS (Hero banners, testimonials, policies, about, T&C, FAQs, store details)  
✅ RBAC for role-based access  
✅ Dashboard analytics  
✅ Backup & restore logs  
✅ File uploads via GridFS  

---

## 3. High‑Level Architecture

```
 ┌───────────────────────────────────────────────────────┐
 │                     Client Layer                       │
 │  (Web App, Mobile App, Admin Panel)                    │
 └─────────────────────────┬──────────────────────────────┘
                           │ HTTPS REST API
 ┌─────────────────────────▼──────────────────────────────┐
 │                    FastAPI Backend                      │
 │ ┌────────────────────────────────────────────────────┐ │
 │ │       Authentication & RBAC Middleware             │ │
 │ └──────────────────────────┬─────────────────────────┘ │
 │                            │                           │
 │ ┌──────────────────────────▼─────────────────────────┐ │
 │ │                API Routers                         │ │
 │ │  Auth, Users, Products, Orders, Reviews, etc.      │ │
 │ └──────────────────────────┬─────────────────────────┘ │
 │                            │                           │
 │ ┌──────────────────────────▼─────────────────────────┐ │
 │ │              Services Layer                        │ │
 │ │  Business logic, payments, coupons, analytics      │ │
 │ └──────────────────────────┬─────────────────────────┘ │
 │                            │                           │
 │ ┌──────────────────────────▼─────────────────────────┐ │
 │ │             Database Layer                         │ │
 │ │  MongoDB (Core Data) + PostgreSQL (Logs/Contact)   │ │
 │ └──────────────────────────┬─────────────────────────┘ │
 └────────────────────────────┼───────────────────────────┘
                              │
                ┌─────────────┼──────────────┬────────────┐
                │             │              │            │
         ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼─────┐ ┌────▼─────┐
         │ MongoDB     │ │ PostgreSQL│ │ Redis     │ │ GridFS    │
         │ Business DB │ │ Logs/Contact│ Permission│ │ Images    │
         └─────────────┘ └────────────┘ └──────────┘ └───────────┘
```

---

## 4. Component Architecture

### ✅ Authentication & Authorization
- JWT Access & Refresh tokens
- Refresh tokens stored in `sessions` collection
- Token revocation (logout/refresh rotation)
- Redis caching for RBAC policy lookup
- Admin vs User permissions

### ✅ Catalog & Product Service
- Brands, categories, product types, product images
- Adjustable inventory (per product)
- Product gallery stored in GridFS
- Reviews & ratings (with status moderation)

### ✅ Order & Payment Service
- Order placement, itemized records
- Multiple payment types: UPI, Cards, COD
- Payment logs stored
- Refund handling via return/exchange flows

### ✅ Return & Exchange Service
- Status‑driven workflow (requested → approved → shipped → completed)
- Admin approval required
- Items returned to stock after completion

### ✅ Coupon & Discounts Service
- Coupon creation, status
- Minimum price validation
- Usage count validation

### ✅ CMS Content
- Hero images, cards, testimonials, how‑it‑works, about, policies, FAQs
- Reordering and update support
- GridFS image storage

### ✅ Backup System
- Admin can trigger database backup
- Logs saved in PostgreSQL and backup_logs collection
- Restore_logs maintained for restores

---

## 5. Databases

### ✅ MongoDB (Primary)
Stores all business data:

| Module | Collection |
|--------|------------|
| Authentication | users, sessions, token_revocations |
| Catalog | products, product_images, brands, categories, occasions, product_types |
| Shopping | carts, cart_items, wishlists, wishlist_items |
| Orders | orders, order_items |
| Returns/Exchanges | returns, exchanges |
| CMS | hero_images, testimonials, cards_1, cards_2, about, faq, policies, T&C, store_details |
| Coupons | coupons, coupons_status |
| Ratings & Reviews | user_reviews, user_ratings |
| Backup | backup_logs, restore_logs |
| Utilities | permissions, role_permissions, user_status, order_status, payment_types, etc. |

### ✅ PostgreSQL (Secondary)
Stores:
- contact_us table
- logs table (audit logs)

### ✅ Redis
- Cached permission policies
- Faster RBAC authorization

### ✅ GridFS
- Stores all images and files safely
- URLs generated via `/files/{id}` endpoint

---

## 6. Data Flow Examples

### ✅ Login Flow
1. User submits email/password
2. Password hashed & verified
3. Access + Refresh token generated
4. Refresh stored in DB (sessions)
5. Access used for authentication

### ✅ Add to Cart Flow
1. User sends item, size
2. Validates product exists
3. Adds to cart_items under user cart
4. Cart returned with updated total

### ✅ Return/Exchange Flow
1. Customer requests return
2. Admin approves/rejects
3. If approved → pickup/shipping
4. Refund issued or replacement dispatched
5. Status updated in return_status/exchange_status

---

## 7. Security Architecture

- All protected routes use JWT access
- Refresh token rotation (security best practice)
- Revocation of used refresh tokens
- OTP‑based password reset
- Image upload type validation & size limit (GridFS)
- All DB writes use transactions where needed

---

## 8. Deployment Architecture

```
             ┌──────────────┐
             │Cloud / VPS   │
             └──────┬───────┘
                    │
             ┌──────▼───────┐
             │  Uvicorn     │
             │  Gunicorn    │
             └──────┬───────┘
                    │
     ┌──────────────┼──────────────────┐
     │              │                  │
 ┌───▼───┐      ┌───▼───┐         ┌────▼────╗
 │MongoDB│      │Postgres│        │Redis    │
 └───────┘      └────────┘        └─────────┘
        ┌────────────────────────────┐
        │   GridFS (File Storage)   │
        └────────────────────────────┘
```

---

## 9. API Design Principles
- RESTful endpoints
- Versioned prefix `/api/v1`
- JWT Bearer authentication
- Request validation with Pydantic
- Unified error responses

Example response:
```json
{
  "message": "Order placed successfully",
  "order_id": "65af0b12..."
}
```

---

## 10. Performance Considerations
- Redis caching for permissions
- MongoDB indexes on frequently queried fields
- Pagination on GET endpoints
- Async IO for non‑blocking requests
- Streaming uploads to GridFS to handle large files

---

## 11. Monitoring & Logs
- Logging middleware prints request metadata + compute time
- PostgreSQL logs table for long‑term records
- Backup and restore logs stored
- Audit logs for user actions can be expanded

---

## 12. Future Enhancements
✅ Machine learning: trending predictions  

---

## 13. Technology Stack Summary

| Layer | Technology |
|-------|------------|
| API Framework | FastAPI |
| Language | Python 3.12 |
| Database | MongoDB + PostgreSQL |
| Cache | Redis |
| File Storage | GridFS |
| Auth | JWT + bcrypt |
| Background Tasks | Async I/O |
| Deployment | Uvicorn/Gunicorn, Docker |

---

## 14. Project Structure

```bash
└──backend/
    ├── .env
    ├── .gitignore
    ├── main.py
    ├── README.md
    ├── requirements.txt
    ├── scripts/
    │   ├── seed.py
    │   ├── __init__.py
    ├── app/
    │   ├── main.py
    │   ├── __init__.py
    │   ├── utils/
    │   │   ├── crypto.py
    │   │   ├── fastapi_mail.py
    │   │   ├── gridfs.py
    │   │   ├── mongo.py
    │   │   ├── tokens.py
    │   │   └── __init__.py
    │   ├── services/
    │   │   ├── about.py
    │   │   ├── address.py
    │   │   ├── auth.py
    │   │   ├── backup_logs.py
    │   │   ├── brands.py
    │   │   ├── cards_1.py
    │   │   ├── cards_2.py
    │   │   ├── card_details.py
    │   │   ├── cart_items.py
    │   │   ├── categories.py
    │   │   ├── contact_us.py
    │   │   ├── coupons.py
    │   │   ├── coupons_status.py
    │   │   ├── dashboard.py
    │   │   ├── exchanges.py
    │   │   ├── exchange_status.py
    │   │   ├── faq.py
    │   │   ├── files.py
    │   │   ├── hero_images.py
    │   │   ├── how_it_works.py
    │   │   ├── logs.py
    │   │   ├── log_writer.py
    │   │   ├── occasions.py
    │   │   ├── orders.py
    │   │   ├── order_items.py
    │   │   ├── order_status.py
    │   │   ├── payments.py
    │   │   ├── payment_status.py
    │   │   ├── payment_types.py
    │   │   ├── policies.py
    │   │   ├── products.py
    │   │   ├── product_images.py
    │   │   ├── product_types.py
    │   │   ├── restore_logs.py
    │   │   ├── returns.py
    │   │   ├── return_status.py
    │   │   ├── review_status.py
    │   │   ├── store_details.py
    │   │   ├── terms_and_conditions.py
    │   │   ├── testimonials.py
    │   │   ├── upi_details.py
    │   │   ├── users.py
    │   │   ├── user_address.py
    │   │   ├── user_ratings.py
    │   │   ├── user_reviews.py
    │   │   ├── user_roles.py
    │   │   ├── user_status.py
    │   │   └── wishlist_items.py
    │   ├── schemas/
    │   │   ├── about.py
    │   │   ├── backup_logs.py
    │   │   ├── brands.py
    │   │   ├── cards_1.py
    │   │   ├── cards_2.py
    │   │   ├── card_details.py
    │   │   ├── carts.py
    │   │   ├── cart_items.py
    │   │   ├── categories.py
    │   │   ├── contact_us.py
    │   │   ├── coupons.py
    │   │   ├── coupons_status.py
    │   │   ├── dashboard.py
    │   │   ├── exchanges.py
    │   │   ├── exchange_status.py
    │   │   ├── faq.py
    │   │   ├── hero_images.py
    │   │   ├── how_it_works.py
    │   │   ├── logs.py
    │   │   ├── object_id.py
    │   │   ├── occasions.py
    │   │   ├── orders.py
    │   │   ├── order_items.py
    │   │   ├── order_status.py
    │   │   ├── payments.py
    │   │   ├── payment_status.py
    │   │   ├── payment_types.py
    │   │   ├── policies.py
    │   │   ├── products.py
    │   │   ├── product_images.py
    │   │   ├── product_types.py
    │   │   ├── requests.py
    │   │   ├── responses.py
    │   │   ├── restore_logs.py
    │   │   ├── returns.py
    │   │   ├── return_status.py
    │   │   ├── review_status.py
    │   │   ├── sessions.py
    │   │   ├── store_details.py
    │   │   ├── terms_and_conditions.py
    │   │   ├── testimonials.py
    │   │   ├── token_revocations.py
    │   │   ├── upi_details.py
    │   │   ├── users.py
    │   │   ├── user_address.py
    │   │   ├── user_ratings.py
    │   │   ├── user_reviews.py
    │   │   ├── user_roles.py
    │   │   ├── user_status.py
    │   │   ├── wishlists.py
    │   │   ├── wishlist_items.py
    │   │   └── __init__.py
    │   ├── models/
    │   │   ├── contact_us.py
    │   │   ├── login_logs.py
    │   │   ├── logout_logs.py
    │   │   ├── register_logs.py
    │   │   └── __init__.py
    │   ├── middleware/
    │   │   ├── error_handler.py
    │   │   └── logging.py
    │   ├── crud/
    │   │   ├── about.py
    │   │   ├── backup_logs.py
    │   │   ├── brands.py
    │   │   ├── cards_1.py
    │   │   ├── cards_2.py
    │   │   ├── card_details.py
    │   │   ├── carts.py
    │   │   ├── cart_items.py
    │   │   ├── categories.py
    │   │   ├── contact_us.py
    │   │   ├── coupons.py
    │   │   ├── coupons_status.py
    │   │   ├── exchanges.py
    │   │   ├── exchange_status.py
    │   │   ├── faq.py
    │   │   ├── hero_images.py
    │   │   ├── how_it_works.py
    │   │   ├── logs.py
    │   │   ├── occasions.py
    │   │   ├── orders.py
    │   │   ├── order_items.py
    │   │   ├── order_status.py
    │   │   ├── payments.py
    │   │   ├── payment_status.py
    │   │   ├── payment_types.py
    │   │   ├── policies.py
    │   │   ├── products.py
    │   │   ├── product_images.py
    │   │   ├── product_types.py
    │   │   ├── restore_logs.py
    │   │   ├── returns.py
    │   │   ├── return_status.py
    │   │   ├── review_status.py
    │   │   ├── sessions.py
    │   │   ├── store_details.py
    │   │   ├── terms_and_conditions.py
    │   │   ├── testimonials.py
    │   │   ├── token_revocations.py
    │   │   ├── upi_details.py
    │   │   ├── users.py
    │   │   ├── user_address.py
    │   │   ├── user_ratings.py
    │   │   ├── user_reviews.py
    │   │   ├── user_roles.py
    │   │   ├── user_status.py
    │   │   ├── wishlists.py
    │   │   ├── wishlist_items.py
    │   │   └── __init__.py
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── database.py
    │   │   ├── redis.py
    │   │   ├── security.py
    │   │   └── __init__.py
    │   └── api/
    │       ├── deps.py
    │       ├── __init__.py
    │       └── routers/
    │           ├── about.py
    │           ├── address.py
    │           ├── auth.py
    │           ├── backup_logs.py
    │           ├── brands.py
    │           ├── cards_1.py
    │           ├── cards_2.py
    │           ├── card_details.py
    │           ├── cart_items.py
    │           ├── categories.py
    │           ├── contact_us.py
    │           ├── coupons.py
    │           ├── coupons_status.py
    │           ├── dashboard.py
    │           ├── exchanges.py
    │           ├── exchange_status.py
    │           ├── faq.py
    │           ├── files.py
    │           ├── hero_images.py
    │           ├── how_it_works.py
    │           ├── logs.py
    │           ├── occasions.py
    │           ├── orders.py
    │           ├── order_items.py
    │           ├── order_status.py
    │           ├── payments.py
    │           ├── payment_status.py
    │           ├── payment_types.py
    │           ├── policies.py
    │           ├── products.py
    │           ├── product_images.py
    │           ├── product_types.py
    │           ├── restore_logs.py
    │           ├── returns.py
    │           ├── return_status.py
    │           ├── review_status.py
    │           ├── store_details.py
    │           ├── terms_and_conditions.py
    │           ├── testimonials.py
    │           ├── upi_details.py
    │           ├── users.py
    │           ├── user_address.py
    │           ├── user_ratings.py
    │           ├── user_reviews.py
    │           ├── user_roles.py
    │           ├── user_status.py
    │           ├── wishlist_items.py
    │           └── __init__.py
```

---

## Contact & Support
**Author:** Lokesh Chirumamilla
**Support Email:** lokeshchirumamillla2104@gmail.com
