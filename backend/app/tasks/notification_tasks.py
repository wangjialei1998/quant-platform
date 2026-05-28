from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.notification_tasks.send_notification")
def send_notification(notification_id: int) -> dict:
    return {
        "status": "success",
        "notification_id": notification_id,
        "message": "邮件通知任务接口已建立，SMTP 发送待接入配置",
    }

