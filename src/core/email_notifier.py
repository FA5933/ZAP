import smtplib
from email.mime.text import MIMEText

class EmailNotifier:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def send_notification(self, subject, body):
        self.logger.log(f"Sending email notification: {subject}")
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.config.get('Email', 'sender_email')
            msg['To'] = self.config.get('Email', 'recipient_email')

            with smtplib.SMTP(self.config.get('Email', 'smtp_server'), self.config.getint('Email', 'smtp_port')) as server:
                server.starttls()
                server.login(self.config.get('Email', 'sender_email'), self.config.get('Email', 'sender_password'))
                server.send_message(msg)
            self.logger.log("Email sent successfully.")
        except Exception as e:
            self.logger.log(f"Failed to send email: {e}", level='error')

