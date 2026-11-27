"""Environment-only, zero-secret-output production readiness checks.

Run inside the Render service shell with the service's existing environment.
Does NOT send OTP, debit payments, disclose secrets, or change configuration.
"""
import os
import sys
from urllib.parse import urlsplit


def present(name, *, min_length=1):
    value=os.getenv(name,'')
    return len(value.strip())>=min_length


def flag(name):
    return os.getenv(name,'').strip().lower() in ('true','1','yes')


def result(title, ok, action=''):
    print(('PASS' if ok else 'CHECK') + '  '+title+((' — '+action) if not ok and action else ''))
    return bool(ok)


def main():
    checks=[]
    checks.append(result('Strong SECRET_KEY',present('SECRET_KEY',min_length=32) and not os.getenv('SECRET_KEY','').startswith('development'), 'Set a unique server secret, at least 32 characters'))
    checks.append(result('Strong JWT_SECRET_KEY',present('JWT_SECRET_KEY',min_length=32) and not os.getenv('JWT_SECRET_KEY','').startswith('development'), 'Set a separate secure JWT signing key'))
    db=os.getenv('DATABASE_URL','')
    checks.append(result('Persistent database URL',bool(db) and not db.startswith('sqlite:'),'Configure managed production database'))
    redis=os.getenv('REDIS_URL','')
    checks.append(result('Redis for distributed rate limits and OTP',redis.startswith(('redis://','rediss://')),'Configure Redis URL'))
    checks.append(result('CORS allowed website origins',present('WEB_ORIGINS') and 'localhost' not in os.getenv('WEB_ORIGINS',''),'Set the exact HTTPS production origins'))
    checks.append(result('Google backend client ID',present('GOOGLE_CLIENT_ID'),'Use the matching Google OAuth client ID'))
    checks.append(result('Google client front end (NEXT_PUBLIC_GOOGLE_CLIENT_ID)',present('NEXT_PUBLIC_GOOGLE_CLIENT_ID'),'Check this separately in Vercel if frontend variables are not on Render'))
    sms=flag('SMS_ENABLED')
    otp=flag('PHONE_OTP_ENABLED')
    checks.append(result('Phone OTP enabled with SMS',sms and otp,'Set both flags only after Arkesel and Redis are working'))
    checks.append(result('Arkesel SMS credentials',os.getenv('SMS_PROVIDER','').lower()=='arkesel' and present('ARKESEL_API_KEY') and 1<=len(os.getenv('ARKESEL_SENDER_ID',''))<=11,'Check SMS_PROVIDER, ARKESEL_API_KEY, ARKESEL_SENDER_ID'))
    checks.append(result('Sentry monitoring configured',flag('SENTRY_ENABLED') and present('SENTRY_DSN'),'Configure production error tracking'))
    checks.append(result('Notification scheduler protection',not flag('NOTIFICATION_SCHEDULER_ENABLED') or present('NOTIFICATION_SCHEDULER_TOKEN',min_length=32),'Set scheduler bearer token'))
    checks.append(result('Finance scheduler protection',not flag('PAYMENT_SCHEDULER_ENABLED') or present('PAYMENT_SCHEDULER_TOKEN',min_length=32),'Set finance scheduler bearer token'))
    if flag('PAYMENTS_ENABLED'):
        checks.append(result('Live payments provider configured',os.getenv('PAYSTACK_SECRET_KEY','').startswith('sk_live_'),'Check Paystack live key; do not paste it into chat'))
    else:
        print('INFO  Live payments disabled; no financial transaction was triggered')
    print('\nSummary: %d checks need attention. No secrets or customer data printed.' % checks.count(False))
    return 0 if all(checks) else 2

if __name__=='__main__':
    sys.exit(main())
