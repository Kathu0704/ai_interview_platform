# 📧 Email Configuration Setup Guide

## 🔧 **SMTP Configuration for AI Mock Interview Platform**

### **Step 1: Gmail App Password Setup**

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account Settings
   - Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
   - Copy the 16-character password

### **Step 2: Update Settings.py**

Edit `ai_interview_platform/settings.py` and replace these values:

```python
EMAIL_HOST_USER = 'your-actual-email@gmail.com'  # Your Gmail address
EMAIL_HOST_PASSWORD = 'your-16-char-app-password'  # App password from Step 1
```

### **Step 3: Test Email Configuration**

1. **Start the server**: `python manage.py runserver`
2. **Go to**: `http://localhost:8000/candidate/email-confirmation/`
3. **Enter your email** and click "Send Confirmation OTP"
4. **Check your email** for the OTP

### **Alternative: Use Console Backend for Development**

If you want to test without setting up SMTP, change this line in `settings.py`:

```python
# Comment out SMTP settings
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'

# Use console backend instead
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

This will print OTPs to the console instead of sending emails.

### **Step 4: Production Deployment**

For production, consider using:
- **SendGrid** (recommended)
- **Mailgun**
- **AWS SES**
- **Gmail SMTP** (limited to 500 emails/day)

### **Troubleshooting**

- **"Authentication failed"**: Check your app password
- **"Connection refused"**: Check firewall/network settings
- **"Rate limit exceeded"**: Gmail has daily sending limits

### **Security Notes**

- ✅ **App passwords** are more secure than regular passwords
- ✅ **Never commit** real credentials to version control
- ✅ **Use environment variables** in production
- ✅ **Enable 2FA** on your email account

---

**Need Help?** Check Django's email documentation or contact support.
