"""Independent notification, only for verified live video after artifact upload."""
import json
import os
import smtplib
import ssl
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
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=60, context=ssl.create_default_context()) as smtp:
        smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        smtp.send_message(msg)
    print('E-mail Shorts odeslán.')


if __name__ == '__main__':
    main()
