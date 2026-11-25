"""Independent notification, only for verified live video after artifact upload."""
import json
import os
import smtplib
import ssl
import time
from email.message import EmailMessage
from pathlib import Path


def message(root, env):
    audit = json.loads((root / 'audit.json').read_text(encoding='utf-8'))
    check = json.loads((root / 'verification.json').read_text(encoding='utf-8'))
    if audit['mode'] != 'NHL_API' or check['status'] != 'PASS' or not audit['game_count']:
        return None
    if not (root / 'video' / audit['video_file']).is_file():
        raise ValueError('Chybí ověřené video')
    for key in ('SMTP_USER', 'SMTP_PASSWORD', 'MAIL_TO', 'ARTIFACT_URL'):
        if not env.get(key):
            raise ValueError(f'Chybí nastavení {key}')
    msg = EmailMessage()
    msg['From'] = env['SMTP_USER']
    msg['To'] = env['MAIL_TO']
    msg['Subject'] = f"Be6player NHL Shorts – {audit['date']} – video připraveno"
    msg.set_content(f"Video je připraveno ke stažení.\nDatum: {audit['date']}\nPočet zápasů: {audit['game_count']}\nDokončeno: {audit['finished_prague']}\n\nZIP: {env['ARTIFACT_URL']}\n\nOdkaz vyžaduje přihlášení na GitHub. Archiv je uchováván 14 dní. Publikování na YouTube je ruční.")
    return msg


def main():
    msg = message(Path('shorts_preview'), os.environ)
    if msg is None:
        print('Bez ověřeného živého videa: e-mail se neposílá.')
        return
    user = os.environ['SMTP_USER'].strip()
    password = os.environ['SMTP_PASSWORD'].replace(' ', '').strip()
    context = ssl.create_default_context()
    # Retry only before sending, to avoid duplicate messages after ambiguous delivery.
    for attempt, port in enumerate((465, 587, 465), 1):
        smtp = None
        try:
            if port == 465:
                smtp = smtplib.SMTP_SSL('smtp.gmail.com', port, timeout=60, context=context)
            else:
                smtp = smtplib.SMTP('smtp.gmail.com', port, timeout=60)
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
            smtp.login(user, password)
        except smtplib.SMTPAuthenticationError:
            if smtp: smtp.close()
            raise RuntimeError('Gmail odmítl přihlášení. Zkontrolujte SMTP_USER a heslo aplikace SMTP_PASSWORD.') from None
        except (smtplib.SMTPException, OSError) as exc:
            if smtp: smtp.close()
            print(f'Pokus {attempt}/3, port {port}: {type(exc).__name__}', flush=True)
            if attempt == 3:
                raise RuntimeError('SMTP připojení selhalo i po opakování.') from None
            time.sleep(10 * attempt)
            continue
        try:
            refused = smtp.send_message(msg)
            if refused:
                raise RuntimeError('Někteří příjemci byli odmítnuti.')
        finally:
            smtp.close()
        break
    print('E-mail Shorts odeslán.')


if __name__ == '__main__':
    main()
