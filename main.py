from fastapi import FastAPI

from routes import auth, companies, onboarding

app = FastAPI()
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(onboarding.router)

