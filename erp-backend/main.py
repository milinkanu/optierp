from fastapi import FastAPI

from routes import auth, companies, health, invoices, onboarding, transactions
from routes.inspector import router as inspector_router

app = FastAPI()
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(onboarding.router)
app.include_router(invoices.router)
app.include_router(transactions.router)
app.include_router(inspector_router)

