from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.logging import RequestLoggingMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import db, Base, engine, close_engine, close_mongo_connection
from app.core.redis import clear_permissions_cache, close_redis
from fastapi.responses import HTMLResponse
from app.api.routers import (
    auth, users,
    brands, product_types, occasions, categories, review_status, order_status,
    return_status, exchange_status, payment_types, payment_status, coupons_status,
    hero_images, cards_1, cards_2, how_it_works, testimonials, about, policies, faq,
    terms_and_conditions, store_details, products, product_images, wishlist_items,
    cart_items, user_address, orders, order_items, user_reviews, user_ratings,
    returns, exchanges, payments, card_details, upi_details, coupons, 
    backup_logs, restore_logs , files, address , contact_us, logs
)
prefix = settings.API_V1_PREFIX
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    """Create database tables and start Redis connection on FastAPI startup,
    and close them on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await db["token_revocations"].create_index("expiresAt", expireAfterSeconds=0)
    await db["sessions"].create_index("refresh_hash", unique=True)
    await db["sessions"].create_index("user_id")
    await clear_permissions_cache()

    yield  # <--- app runs while this yields

    # Shutdown
    await close_mongo_connection()
    await close_redis()
    await close_engine()
    
    """
    Initialize Fastapi with swagger redirect url to hanle custom login
    """
app = FastAPI(
    title=settings.PROJECT_NAME,
    servers=[{"url": "http://localhost:8000"}],
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
    docs_url=None,
    lifespan=lifespan
)

""" Added CORS Middle ware to allow cross origin resouce sharing
    Currently in development so allowed all origins, methods, headers, with credentials
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""Custom middle to print meta data of request and computation time for each request"""
app.add_middleware(RequestLoggingMiddleware)


"""Over ridding inbuilt swagger/ui to add drop down for filtering routes based on tags"""
@app.get("/docs", include_in_schema=False)
def custom_docs():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
        <title>True Style - FastAPI Backend</title>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>

        <script>
        const ui = SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            layout: 'BaseLayout',
            deepLinking: true,
            showExtensions: true,
            showCommonExtensions: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            onComplete: () => {
                // Wait for DOM to be ready
                const authButton = document.querySelector('.btn.authorize.unlocked');

  
    
    // Wait a short time in case the modal content loads dynamically
    setInterval(() => {
      
      const modal = document.querySelector('.modal-ux'); // or use your modal selector
modal.querySelectorAll('*').forEach(el => {
  el.childNodes.forEach(node => {
    if (node.nodeType === 3) {
      const text = node.textContent.trim();
      if (text.includes('username')) {
        node.textContent = text.replace(/username/gi, 'Email');
      }
      if (text.includes('password')) {
        node.textContent = text.replace(/password/gi, 'Password');
      }
    }  
  });
});
    }, 1000);
                setTimeout(() => {
                    const authWrapper = document.querySelector('.auth-wrapper');
                    if (authWrapper) {
                        const dropdown = document.createElement('select');
                        dropdown.style.marginRight = '10px';
                        dropdown.innerHTML = `
                            <option value="">Show All</option>
                            <option value="Root">Root</option>
                            <option value="Auth">Auth</option>
                            <option value="Users">Users</option>
                            <option value="Content">Content</option>
                            <option value="Utility">Utility</option>
                            <option value="Wishlists">Wishlists</option>
                            <option value="Carts">Carts</option>
                            <option value="Products">Products</option>
                            <option value="Orders">Orders</option>
                            <option value="Returns">Returns</option>
                            <option value="Exchanges">Exchanges</option>
                            <option value="Reviews">Reviews</option>
                            <option value="Ratings">Ratings</option>
                            <option value="Backup">Backup</option>
                            <option value="Restore">Restore</option>
                            <optioin value="Files">Files</option>
                            <optioin value="Coupons">Coupons</option>
                            <option value="Payments">Payments</option>
                            <option value="Logs">Logs</option>
                            <option value="Contact Us">Contact Us</option>

                        `;

                        
                        dropdown.style.zIndex = '9999';
                        dropdown.style.padding = '8px';
                        dropdown.style.backgroundColor = '#f5f5f5';
                        dropdown.style.border = '1px solid #ccc';
                        dropdown.style.borderRadius = '4px';
                        dropdown.style.cursor = 'pointer';
                        dropdown.style.marginRight = '10px';


                        dropdown.onchange = function() {
                            const tag = this.value;
                            document.querySelectorAll('.opblock-tag-section').forEach(sec => {
                                const tagName = sec.querySelector('.opblock-tag').textContent.trim();
                                if (!tag || tagName === tag) {
                                    sec.style.display = '';
                                } else {
                                    sec.style.display = 'none';
                                }
                            });
                        };

                        // Insert dropdown before the auth button
                        authWrapper.parentNode.insertBefore(dropdown, authWrapper);
                    }
                }, 100); // Small delay to ensure Swagger UI renders
            }
        });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

"""Adding all the routes to FastAPI instance"""

app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["Auth"])
app.include_router(users.router, prefix=f"{prefix}/users", tags=["Users"])
app.include_router(files.router, prefix=f"{prefix}/files", tags=["Files"])
app.include_router(brands.router, prefix=f"{prefix}/brands", tags=["Utility"])
app.include_router(product_types.router, prefix=f"{prefix}/product-types", tags=["Utility","Product-Types"])
app.include_router(occasions.router, prefix=f"{prefix}/occasions", tags=["Utility"])
app.include_router(categories.router, prefix=f"{prefix}/categories", tags=["Utility"])
app.include_router(review_status.router, prefix=f"{prefix}/review-status", tags=["Utility"])
app.include_router(order_status.router, prefix=f"{prefix}/order-status", tags=["Utility"])
app.include_router(return_status.router, prefix=f"{prefix}/return-status", tags=["Utility"])
app.include_router(exchange_status.router, prefix=f"{prefix}/exchange-status", tags=["Utility"])
app.include_router(payment_types.router, prefix=f"{prefix}/payment-types", tags=["Utility"])
app.include_router(payment_status.router, prefix=f"{prefix}/payment-status", tags=["Utility"])
app.include_router(coupons_status.router, prefix=f"{prefix}/coupons-status", tags=["Utility"])

app.include_router(hero_images.router, prefix=f"{prefix}/hero-images", tags=["Content"])
app.include_router(cards_1.router, prefix=f"{prefix}/cards-1", tags=["Content"])
app.include_router(cards_2.router, prefix=f"{prefix}/cards-2", tags=["Content"])
app.include_router(how_it_works.router, prefix=f"{prefix}/how-it-works", tags=["Content"])
app.include_router(testimonials.router, prefix=f"{prefix}/testimonials", tags=["Content"])
app.include_router(about.router, prefix=f"{prefix}/about", tags=["Content"])
app.include_router(policies.router, prefix=f"{prefix}/policies", tags=["Content"])
app.include_router(faq.router, prefix=f"{prefix}/faq", tags=["Content"])
app.include_router(terms_and_conditions.router, prefix=f"{prefix}/terms", tags=["Content"])
app.include_router(store_details.router, prefix=f"{prefix}/store-details", tags=["Content"])

app.include_router(products.router, prefix=f"{prefix}/products", tags=["Products"])
app.include_router(product_images.router, prefix=f"{prefix}/product-images", tags=["Products"])
app.include_router(wishlist_items.router, prefix=f"{prefix}/wishlist-items", tags=["Wishlists"])
app.include_router(cart_items.router, prefix=f"{prefix}/cart-items", tags=["Carts"])
app.include_router(user_address.router, prefix=f"{prefix}/user-address", tags=["Users"])
app.include_router(address.router, prefix=f"{prefix}/address", tags=["Users"])
app.include_router(orders.router, prefix=f"{prefix}/orders", tags=["Orders"])
app.include_router(order_items.router, prefix=f"{prefix}/order-items", tags=["Orders"])
app.include_router(user_reviews.router, prefix=f"{prefix}/user-reviews", tags=["Reviews"])
app.include_router(user_ratings.router, prefix=f"{prefix}/user-ratings", tags=["Ratings"])
app.include_router(returns.router, prefix=f"{prefix}/returns", tags=["Returns"])
app.include_router(exchanges.router, prefix=f"{prefix}/exchanges", tags=["Exchanges"])
app.include_router(payments.router, prefix=f"{prefix}/payments", tags=["Payments"])
app.include_router(card_details.router, prefix=f"{prefix}/card-details", tags=["Payments"])
app.include_router(upi_details.router, prefix=f"{prefix}/upi-details", tags=["Payments"])
app.include_router(coupons.router, prefix=f"{prefix}/coupons", tags=["Coupons"])
app.include_router(backup_logs.router, prefix=f"{prefix}/backup-logs", tags=["Backup"])
app.include_router(restore_logs.router, prefix=f"{prefix}/restore-logs", tags=["Restore"])
app.include_router(contact_us.router, prefix=f"{prefix}/contact-us", tags=["Contact Us"])
app.include_router(logs.router, prefix=f"{prefix}/logs", tags=["Logs"])


@app.get("/",tags=["Root"])
async def root():
    return {"message": f"{settings.PROJECT_NAME} is running"}


