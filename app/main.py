from fastapi import FastAPI

from app.api.routers import deadlines, notification_jobs, notification_rules, study_groups, vk_chats, vk_communities
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="VK Deadline API", version="0.1.0")

app.include_router(vk_communities.router)
app.include_router(study_groups.router)
app.include_router(vk_chats.router)
app.include_router(deadlines.router)
app.include_router(notification_rules.router)
app.include_router(notification_jobs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
