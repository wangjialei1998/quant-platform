from fastapi import APIRouter

from app.core.config import settings as app_settings

router = APIRouter()


@router.get("/email")
def get_email_settings() -> dict:
    return {
        "smtp_host": app_settings.smtp_host,
        "smtp_port": app_settings.smtp_port,
        "smtp_username": app_settings.smtp_username,
        "smtp_from": app_settings.smtp_from,
        "smtp_to": app_settings.smtp_to,
        "configured": bool(app_settings.smtp_host and app_settings.smtp_to),
    }


@router.patch("/email")
def update_email_settings() -> dict:
    return {"message": "邮件配置持久化接口已预留，请通过环境变量配置第一版 SMTP"}


@router.post("/email/test")
def test_email() -> dict:
    return {"message": "测试邮件接口已预留，SMTP 配置完成后接入发送任务"}

