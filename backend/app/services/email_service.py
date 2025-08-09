"""
Email service for sending verification emails using Hetzner SMTP
"""
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
import logging
from typing import Optional
from ..core.config import settings
from .i18n_service import i18n_service

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
        """Send an email using Hetzner SMTP with improved Gmail deliverability"""
        try:
            # Create message with proper headers for better deliverability
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = to_email
            msg['Reply-To'] = self.from_email
            
            # Add additional headers for better deliverability
            msg['Message-ID'] = f"<{secrets.token_urlsafe(16)}@halbzeit.ai>"
            msg['Date'] = formatdate(localtime=True)
            msg['X-Mailer'] = 'HALBZEIT AI Platform'
            msg['X-Priority'] = '3'
            msg['Importance'] = 'Normal'
            
            # SPF/DKIM friendly headers
            msg['Return-Path'] = self.from_email
            msg['Sender'] = self.from_email

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

    def send_verification_email(self, email: str, verification_token: str, language: str = "en") -> bool:
        """Send email verification email"""
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        # Get translations using I18n service
        subject = i18n_service.t("emails.verification.subject", language)
        welcome_text = i18n_service.t("emails.verification.welcome", language)
        thank_you_text = i18n_service.t("emails.verification.thank_you", language)
        button_text = i18n_service.t("emails.verification.button_text", language)
        important_text = i18n_service.t("emails.verification.important", language)
        expiry_text = i18n_service.t("emails.verification.expiry", language)
        fallback_text = i18n_service.t("emails.verification.fallback", language)
        ignore_text = i18n_service.t("emails.verification.ignore", language)
        footer_text = i18n_service.t("emails.verification.footer", language)
        support_text = i18n_service.t("emails.verification.support", language)
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html lang="{language}">
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
                <h2>{welcome_text}</h2>
                
                <p>{thank_you_text}</p>
                
                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">{button_text}</a>
                </p>
                
                <div class="warning">
                    <strong>{important_text}</strong> {expiry_text}
                </div>
                
                <p>{fallback_text}</p>
                <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
                    {verification_url}
                </p>
                
                <p>{ignore_text}</p>
            </div>
            
            <div class="footer">
                <p>{footer_text}</p>
                <p>{support_text}</p>
            </div>
        </body>
        </html>
        """
        
        # Text version for email clients that don't support HTML
        text_welcome = i18n_service.t("emails.verification.text_welcome", language)
        text_thank_you = i18n_service.t("emails.verification.text_thank_you", language)
        text_expiry = i18n_service.t("emails.verification.text_expiry", language)
        text_ignore = i18n_service.t("emails.verification.text_ignore", language)
        text_regards = i18n_service.t("emails.verification.text_regards", language)
        
        text_body = f"""
        {text_welcome}
        
        {text_thank_you}
        
        {verification_url}
        
        {text_expiry}
        
        {text_ignore}
        
        {text_regards}
        """
        
        return self.send_email(email, subject, html_body, text_body)

    def send_welcome_email(self, email: str, company_name: str, language: str = "en") -> bool:
        """Send welcome email after successful verification"""
        
        # Get translations using I18n service
        subject = i18n_service.t("emails.welcome.subject", language)
        welcome_title = i18n_service.t("emails.welcome.title", language, company_name=company_name)
        verified_text = i18n_service.t("emails.welcome.verified", language)
        features_title = i18n_service.t("emails.welcome.features_title", language)
        upload_text = i18n_service.t("emails.welcome.feature_upload", language)
        review_text = i18n_service.t("emails.welcome.feature_review", language)
        qa_text = i18n_service.t("emails.welcome.feature_qa", language)
        track_text = i18n_service.t("emails.welcome.feature_track", language)
        login_button = i18n_service.t("emails.welcome.login_button", language)
        excited_text = i18n_service.t("emails.welcome.excited", language)
        
        html_body = f"""
        <!DOCTYPE html>
        <html lang="{language}">
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
                <h2>{welcome_title}</h2>
                
                <p>{verified_text}</p>
                
                <div class="features">
                    <h3>{features_title}</h3>
                    <div class="feature-item">{upload_text}</div>
                    <div class="feature-item">{review_text}</div>
                    <div class="feature-item">{qa_text}</div>
                    <div class="feature-item">{track_text}</div>
                </div>
                
                <p style="text-align: center;">
                    <a href="{settings.FRONTEND_URL}/login" class="button">{login_button}</a>
                </p>
                
                <p>{excited_text}</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(email, subject, html_body)

    def send_password_reset_email(self, email: str, reset_token: str, language: str = "en") -> bool:
        """Send password reset email"""
        
        # Create reset URL
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        # Get translations using I18n service
        subject = i18n_service.t("emails.password_reset.subject", language)
        reset_title = i18n_service.t("emails.password_reset.title", language)
        reset_text = i18n_service.t("emails.password_reset.reset_text", language)
        button_text = i18n_service.t("emails.password_reset.button_text", language)
        important_text = i18n_service.t("emails.password_reset.important", language)
        expiry_text = i18n_service.t("emails.password_reset.expiry", language)
        fallback_text = i18n_service.t("emails.password_reset.fallback", language)
        ignore_text = i18n_service.t("emails.password_reset.ignore", language)
        footer_text = i18n_service.t("emails.password_reset.footer", language)
        support_text = i18n_service.t("emails.password_reset.support", language)
        
        html_body = f"""
        <!DOCTYPE html>
        <html lang="{language}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset - HALBZEIT AI</title>
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
                    background-color: #f44336;
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
                <h2>{reset_title}</h2>
                
                <p>{reset_text}</p>
                
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">{button_text}</a>
                </p>
                
                <div class="warning">
                    <strong>{important_text}</strong> {expiry_text}
                </div>
                
                <p>{fallback_text}</p>
                <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
                    {reset_url}
                </p>
                
                <p>{ignore_text}</p>
            </div>
            
            <div class="footer">
                <p>{footer_text}</p>
                <p>{support_text}</p>
            </div>
        </body>
        </html>
        """
        
        # Text version for email clients that don't support HTML
        text_body = f"""
        {reset_title}
        
        {reset_text}
        
        {reset_url}
        
        {expiry_text}
        
        {ignore_text}
        
        HALBZEIT AI Team
        """
        
        return self.send_email(email, subject, html_body, text_body)

    def send_invitation_email(self, email: str, gp_name: str, project_name: str, invitation_url: str, language: str = "en") -> bool:
        """Send project invitation email"""
        
        # Get translations using I18n service
        subject = i18n_service.t("emails.invitation.subject", language)
        title = i18n_service.t("emails.invitation.title", language)
        greeting = i18n_service.t("emails.invitation.greeting", language)
        invited_by_text = i18n_service.t("emails.invitation.invited_by", language).format(gp_name=gp_name)
        description = i18n_service.t("emails.invitation.description", language)
        button_text = i18n_service.t("emails.invitation.button_text", language)
        important_text = i18n_service.t("emails.invitation.important", language)
        expiry_text = i18n_service.t("emails.invitation.expiry", language)
        fallback_text = i18n_service.t("emails.invitation.fallback", language)
        footer_text = i18n_service.t("emails.invitation.footer", language).format(gp_name=gp_name)
        support_text = i18n_service.t("emails.invitation.support", language)
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html lang="{language}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Project Invitation - HALBZEIT AI</title>
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
                .invitation-title {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #1976d2;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                .project-info {{
                    background-color: #f5f5f5;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .cta-button {{
                    display: inline-block;
                    background-color: #1976d2;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                    font-weight: bold;
                    text-align: center;
                }}
                .important {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    border-top: 1px solid #ddd;
                    padding-top: 20px;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">HALBZEIT AI</div>
            </div>
            
            <div class="content">
                <div class="invitation-title">{title}</div>
                
                <p>{greeting}</p>
                
                <p>{invited_by_text}</p>
                
                <div class="project-info">
                    <strong>Project:</strong> {project_name}
                </div>
                
                <p>{description}</p>
                
                <div style="text-align: center;">
                    <a href="{invitation_url}" class="cta-button" style="display: inline-block; background-color: #1976d2; color: #ffffff !important; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; margin: 20px 0; text-align: center;">{button_text}</a>
                </div>
                
                <div class="important">
                    <strong>{important_text}</strong><br>
                    {expiry_text}
                </div>
                
                <p>{fallback_text}</p>
                <p><a href="{invitation_url}">{invitation_url}</a></p>
            </div>
            
            <div class="footer">
                <p>{footer_text}</p>
                <p>{support_text}</p>
            </div>
        </body>
        </html>
        """
        
        # Text version for email clients that don't support HTML
        text_body = f"""
        {title}
        
        {greeting}
        
        {invited_by_text}
        
        Project: {project_name}
        
        {description}
        
        {button_text}: {invitation_url}
        
        {important_text}
        {expiry_text}
        
        {footer_text}
        
        HALBZEIT AI Team
        """
        
        return self.send_email(email, subject, html_body, text_body)

    def send_gp_invitation_email(self, email: str, name: str, temp_password: str, verification_token: str, invited_by: str, language: str = "en") -> bool:
        """Send GP invitation email with temporary password"""
        
        # Create verification URL
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        # Get translations (using existing ones for now)
        subject = i18n_service.t("emails.invitation.subject", language)
        
        # Create HTML body with improved Gmail compatibility
        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>HALBZEIT AI - GP Invitation</title>
            <!--[if mso]>
            <noscript>
                <xml>
                    <o:OfficeDocumentSettings>
                        <o:PixelsPerInch>96</o:PixelsPerInch>
                    </o:OfficeDocumentSettings>
                </xml>
            </noscript>
            <![endif]-->
            <style type="text/css">
                /* Email client compatibility */
                body, table, td, p, a, li, blockquote {{
                    -webkit-text-size-adjust: 100%;
                    -ms-text-size-adjust: 100%;
                }}
                table, td {{
                    mso-table-lspace: 0pt;
                    mso-table-rspace: 0pt;
                }}
                img {{
                    -ms-interpolation-mode: bicubic;
                    border: 0;
                    height: auto;
                    line-height: 100%;
                    outline: none;
                    text-decoration: none;
                }}
                
                /* Main styles */
                body {{
                    margin: 0 !important;
                    padding: 0 !important;
                    font-family: Arial, Helvetica, sans-serif;
                    background-color: #f8f9fa;
                }}
                
                .email-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                }}
                
                .header {{
                    background-color: #1976d2;
                    text-align: center;
                    padding: 30px 20px;
                }}
                
                .header h1 {{
                    color: #ffffff;
                    font-size: 24px;
                    margin: 0;
                    font-weight: bold;
                }}
                
                .content {{
                    padding: 40px 30px;
                }}
                
                .invitation-title {{
                    font-size: 22px;
                    color: #1976d2;
                    margin-bottom: 20px;
                    font-weight: bold;
                }}
                
                .credentials-box {{
                    background-color: #f8f9fa;
                    border: 2px solid #e9ecef;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 25px 0;
                    font-family: Monaco, Consolas, "Lucida Console", monospace;
                }}
                
                .cta-button {{
                    display: inline-block;
                    background-color: #1976d2;
                    color: #ffffff;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 16px;
                    margin: 20px 0;
                    text-align: center;
                }}
                
                .cta-container {{
                    text-align: center;
                    padding: 20px 0;
                }}
                
                .footer {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    text-align: center;
                    font-size: 14px;
                    color: #6c757d;
                    border-top: 1px solid #e9ecef;
                }}
                
                .security-note {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 6px;
                    padding: 15px;
                    margin: 20px 0;
                    color: #856404;
                }}
                
                /* Mobile responsiveness */
                @media screen and (max-width: 600px) {{
                    .content {{
                        padding: 20px 15px;
                    }}
                    .cta-button {{
                        display: block;
                        width: 90%;
                        margin: 20px auto;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>HALBZEIT AI</h1>
                    <div style="color: #e3f2fd; font-size: 14px;">Healthcare Investment Platform</div>
                </div>
                
                <div class="content">
                    <div class="invitation-title">Welcome to HALBZEIT AI</div>
                    
                    <p>Hello {name},</p>
                    
                    <p>You have been invited by <strong>{invited_by}</strong> to join HALBZEIT AI as a General Partner (GP) to evaluate healthcare startup investments.</p>
                    
                    <p>We've created your account with the following temporary credentials:</p>
                    
                    <div class="credentials-box">
                        <strong>Email:</strong> {email}<br>
                        <strong>Temporary Password:</strong> {temp_password}
                    </div>
                    
                    <div class="security-note">
                        <strong>Security Notice:</strong> You will be required to change this temporary password when you first log in.
                    </div>
                    
                    <p><strong>Next Steps:</strong></p>
                    <ol>
                        <li>Click the button below to verify your email address</li>
                        <li>Log in with your temporary password</li>
                        <li>Set your new secure password</li>
                        <li>Start evaluating healthcare startups</li>
                    </ol>
                    
                    <div class="cta-container">
                        <a href="{verification_url}" class="cta-button">Verify Email & Get Started</a>
                    </div>
                    
                    <p style="font-size: 14px; color: #6c757d;">If the button doesn't work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; font-size: 12px; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
                        {verification_url}
                    </p>
                </div>
                
                <div class="footer">
                    <p><strong>This invitation expires in 7 days.</strong></p>
                    <p>© 2025 HALBZEIT AI - Advanced Healthcare Investment Analysis</p>
                    <p>Secure • Professional • Trusted by Healthcare Investors</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Text version
        text_body = f"""
        Welcome to HALBZEIT AI
        
        Hello {name},
        
        You have been invited by {invited_by} to join HALBZEIT AI as a General Partner (GP).
        
        We've created an account for you with the following credentials:
        
        Email: {email}
        Temporary Password: {temp_password}
        
        IMPORTANT: Please verify your email address first by visiting:
        {verification_url}
        
        After verifying your email, you can log in with your temporary password and we recommend changing it immediately.
        
        This invitation will expire in 7 days.
        
        © 2025 HALBZEIT AI
        """
        
        return self.send_email(email, subject, html_body, text_body)

# Global email service instance
email_service = EmailService()