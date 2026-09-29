"""Benchmark: raw SQL aggregate vs naive ORM N+1 for the order summary endpoint."""
import statistics, time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem

eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
S = sessionmaker(bind=eng); Base.metadata.create_all(eng); db = S()

N_ORDERS, ITEMS_PER = 500, 4
u = User(email="b@x.com", username="b", full_name="B", hashed_password="x", is_active=True, is_admin=True)
db.add(u); db.commit()
prods = [Product(name=f"p{i}", description="d", price=10.0+i, stock_quantity=10**6, is_active=True) for i in range(20)]
db.add_all(prods); db.commit()
for i in range(N_ORDERS):
    o = Order(user_id=u.id, total_amount=100.0+i, status=None); db.add(o); db.flush()
    db.add_all([OrderItem(order_id=o.id, product_id=prods[j % 20].id, quantity=1,
                          price_at_purchase=prods[j % 20].price)
                for j in range(ITEMS_PER)])
db.commit()

RAW = text("""
 SELECT o.id AS order_id, u.email AS user_email, o.total_amount,
        COUNT(oi.id) AS item_count, o.status, o.created_at
 FROM orders o JOIN users u ON o.user_id = u.id
 LEFT JOIN order_items oi ON o.id = oi.order_id
 WHERE (:is_admin = 1 OR o.user_id = :user_id)
 GROUP BY o.id, u.email, o.total_amount, o.status, o.created_at
 ORDER BY o.created_at DESC""")

def raw():
    return [(r.order_id, r.user_email, r.item_count) for r in
            db.execute(RAW, {"is_admin": 1, "user_id": u.id})]

def orm_n1():
    """The naive pattern the raw query replaces: per-order lazy loads."""
    out = []
    for o in db.query(Order).order_by(Order.created_at.desc()).all():
        owner = db.query(User).filter(User.id == o.user_id).first()      # +1 per order
        cnt = db.query(OrderItem).filter(OrderItem.order_id == o.id).count()  # +1 per order
        out.append((o.id, owner.email, cnt))
    return out

def timeit(fn, reps=15):
    fn(); ts = []
    for _ in range(reps):
        db.expire_all()
        t = time.perf_counter(); fn(); ts.append((time.perf_counter()-t)*1000)
    return statistics.median(ts), min(ts), max(ts)

assert len(raw()) == len(orm_n1()) == N_ORDERS
rm, rlo, rhi = timeit(raw)
om, olo, ohi = timeit(orm_n1)
print(f"dataset: {N_ORDERS} orders x {ITEMS_PER} items = {N_ORDERS*ITEMS_PER} order_items, sqlite in-memory")
print(f"raw SQL  : median {rm:8.2f} ms   (min {rlo:.2f} / max {rhi:.2f})")
print(f"ORM N+1  : median {om:8.2f} ms   (min {olo:.2f} / max {ohi:.2f})")
print(f"queries  : raw = 1  |  ORM N+1 = {1 + 2*N_ORDERS}")
print(f"reduction: {(1-rm/om)*100:.1f}%   speedup: {om/rm:.1f}x")
