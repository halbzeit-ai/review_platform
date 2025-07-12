"""
Email service for sending verification emails using Hetzner SMTP
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import logging
from typing import Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME

    def send_email(self, to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Send an email using Hetzner SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = to_email

            # Add text version if provided
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)

            # Add HTML version
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_verification_email(self, email: str, verification_token: str) -> bool:
        """Send email verification email"""
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        subject = "Verify your HALBZEIT AI account"
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Account</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                    border-bottom: 2px solid #1976d2;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1976d2;
                }}
                .content {{
                    padding: 30px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #1976d2;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 10px;
                    border-radius: 4px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">HALBZEIT AI</div>
                <div>Startup Review Platform</div>
            </div>
            
            <div class="content">
                <h2>Welcome to HALBZEIT AI!</h2>
                
                <p>Thank you for registering with our startup review platform. To complete your registration and start using your account, please verify your email address.</p>
                
                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </p>
                
                <div class="warning">
                    <strong>Important:</strong> This verification link will expire in 24 hours. If you don't verify within this time, you'll need to register again.
                </div>
                
                <p>If the button above doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
                    {verification_url}
                </p>
                
                <p>If you didn't create an account with us, please ignore this email.</p>
            </div>
            
            <div class="footer">
                <p>This email was sent by HALBZEIT AI Review Platform</p>
                <p>If you have any questions, please contact our support team.</p>
            </div>
        </body>
        </html>
        """
        
        # Text version for email clients that don't support HTML
        text_body = f"""
        Welcome to HALBZEIT AI!
        
        Thank you for registering with our startup review platform. To complete your registration, please verify your email address by clicking the link below:
        
        {verification_url}
        
        This verification link will expire in 24 hours.
        
        If you didn't create an account with us, please ignore this email.
        
        Best regards,
        HALBZEIT AI Team
        """
        
        return self.send_email(email, subject, html_body, text_body)

    def send_welcome_email(self, email: str, company_name: str) -> bool:
        """Send welcome email after successful verification"""
        subject = "Welcome to HALBZEIT AI - Your account is ready!"
        
        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to HALBZEIT AI</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                    border-bottom: 2px solid #1976d2;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1976d2;
                }}
                .content {{
                    padding: 30px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #1976d2;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .features {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .feature-item {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">HALBZEIT AI</div>
                <div>Startup Review Platform</div>
            </div>
            
            <div class="content">
                <h2>🎉 Welcome to HALBZEIT AI, {company_name}!</h2>
                
                <p>Your email has been successfully verified and your account is now active. You can start using our AI-powered startup review platform immediately.</p>
                
                <div class="features">
                    <h3>What you can do now:</h3>
                    <div class="feature-item">📄 Upload your pitch deck for AI analysis</div>
                    <div class="feature-item">🤖 Get detailed VC-style reviews powered by AI</div>
                    <div class="feature-item">💬 Engage in Q&A with General Partners</div>
                    <div class="feature-item">📊 Track your review progress</div>
                </div>
                
                <p style="text-align: center;">
                    <a href="{settings.FRONTEND_URL}/login" class="button">Login to Your Account</a>
                </p>
                
                <p>We're excited to help you get valuable feedback on your startup!</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(email, subject, html_body)

# Global email service instance
email_service = EmailService()