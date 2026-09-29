# Quick Start Guide

Get the E-Commerce API running and test your first requests.

## 1. System Management

| Action | Command |
|--------|---------|
| **Start App** | `docker-compose up --build` |
| **Stop App** | `docker-compose down` |
| **Full Reset** | `docker-compose down -v` (Wipes database) |
| **Run Tests** | `docker-compose exec api pytest -v` |

## 2. Initial Setup

1. **Launch Services**: Run `docker-compose up --build`.
2. **Register Admin**: Visit http://localhost:8000/docs and use **POST `/api/v1/auth/register`**.
   ```json
   {"email": "admin@example.com", "username": "admin", "password": "admin123456", "is_admin": true}
   ```
3. **Authenticate**: Click the **Authorize** button in Swagger UI and login with your credentials.

## 3. Usage Examples

### Create Product
```bash
curl -X POST "http://localhost:8000/api/v1/products/" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptop", "price": 999.99, "stock_quantity": 10}'
```

### View Performance Analytics
Navigate to **GET `/api/v1/orders/summary`** to view reports generated via optimized raw SQL queries.

## 🛠 Troubleshooting

*   **Database not ready?** Wait 10s for Postgres initialization on first run.
*   **Port Conflict?** Ensure port `8000` and `5432` are available on your host.

---
**Happy Coding!** 🚀
