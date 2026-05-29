from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings as app_settings
from app.core.database import SessionLocal
from app.integrations.smtp_client import SMTPClient
from app.models.setting import SystemSetting
from app.utils.time import utc_now

router = APIRouter()


class EmailSettingsUpdate(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None


@router.get("/email")
def get_email_settings() -> dict:
    config = _email_config()
    return {
        "smtp_host": config["smtp_host"],
        "smtp_port": config["smtp_port"],
        "smtp_username": config["smtp_username"],
        "smtp_from": config["smtp_from"],
        "smtp_to": config["smtp_to"],
        "configured": bool(config["smtp_host"] and config["smtp_to"]),
    }


@router.patch("/email")
def update_email_settings(payload: EmailSettingsUpdate) -> dict:
    current = _email_config(include_password=True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            current[key] = value
            setattr(app_settings, key, value)
    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter(SystemSetting.key == "email").first()
        if row:
            row.value = current
            row.updated_at = utc_now()
        else:
            db.add(
                SystemSetting(
                    key="email",
                    value=current,
                    description="SMTP 邮件配置",
                    updated_at=utc_now(),
                )
            )
        db.commit()
    finally:
        db.close()
    return {
        "message": "ok",
        "configured": bool(current["smtp_host"] and current["smtp_to"]),
    }


@router.post("/email/test")
def test_email() -> dict:
    try:
        SMTPClient().send(
            "量化平台测试邮件",
            "这是一封来自量化平台的 SMTP 测试邮件。如果你收到该邮件，说明邮件配置可用。",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "测试邮件已发送"}


def _email_config(include_password: bool = False) -> dict:
    config = {
        "smtp_host": app_settings.smtp_host,
        "smtp_port": app_settings.smtp_port,
        "smtp_username": app_settings.smtp_username,
        "smtp_password": app_settings.smtp_password,
        "smtp_from": app_settings.smtp_from,
        "smtp_to": app_settings.smtp_to,
    }
    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter(SystemSetting.key == "email").first()
        if row and isinstance(row.value, dict):
            for key, value in row.value.items():
                if value is not None:
                    config[key] = value
    finally:
        db.close()
    if not include_password:
        config.pop("smtp_password", None)
    return config
