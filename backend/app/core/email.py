from brevo_python import ApiClient, Configuration
from brevo_python.api.transactional_emails_api import TransactionalEmailsApi
from brevo_python.models import SendSmtpEmail
from app.core.config import settings

def get_brevo_client():
    configuration = Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY
    return ApiClient(configuration)

def send_otp_email(email: str, otp: str):
    try:
        client = get_brevo_client()
        api_instance = TransactionalEmailsApi(client)
        
        send_email = SendSmtpEmail(
            to=[{"email": email}],
            sender={"email": settings.FROM_EMAIL, "name": settings.FROM_NAME},
            subject="Your Task Manager OTP Code",
            html_content=f"<h2>Your OTP code is: <strong>{otp}</strong></h2><p>It expires in 5 minutes.</p>"
        )
        api_instance.send_transac_email(send_email)
    except Exception as e:
        print(f"[ERROR] Failed to send OTP email to {email}: {str(e)}")
        raise

def send_csv_export_email(email: str, download_url: str):
    try:
        client = get_brevo_client()
        api_instance = TransactionalEmailsApi(client)
        
        send_email = SendSmtpEmail(
            to=[{"email": email}],
            sender={"email": settings.FROM_EMAIL, "name": settings.FROM_NAME},
            subject="Your Task Export is Ready",
            html_content=f'<p>Your CSV export is ready.</p><p><a href="{download_url}" style="display:inline-block;padding:10px 20px;background:#0066cc;color:white;text-decoration:none;border-radius:4px;">Download CSV</a></p><p>Link expires in 1 hour.</p>'
        )
        api_instance.send_transac_email(send_email)
    except Exception as e:
        print(f"[ERROR] Failed to send CSV export email to {email}: {str(e)}")
        raise