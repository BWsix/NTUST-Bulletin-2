from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime, timedelta
import smtplib
import email.message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import emoji
import imaplib
import logging
import os
import sys

HOST = "mail.ntust.edu.tw"
SKIP_DATE_CHECK = os.getenv("SKIP_DATE_CHECK", False)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(sys.argv[0])


@dataclass
class Announcement():
    publisher: str
    title: str
    link: str

    def __str__(self):
        return f'<tr><td data-title="發佈單位">{self.publisher}</td><td data-title="標題"><a target="_blank" href="{self.link}" style="text-decoration: none">{self.title}</a></td></tr>'


class IMAPClient():
    client = imaplib.IMAP4(HOST)

    def __init__(self, user: str, password: str):
        self.client.login(user, password)

    def logout(self):
        self.client.close()
        self.client.logout()

    def getAnnouncements(self) -> tuple[datetime, list[Announcement]]:
        self.client.select("INBOX")
        indices = self.fetchBulletinIndices()

        message = self.fetchMessage(indices[-1])
        payload = self.getMessagePayload(message)
        announcements = self.parsePayload(payload)
        prev_message = self.fetchMessage(indices[-2])
        prev_payload = self.getMessagePayload(prev_message)
        prev_announcements = self.parsePayload(prev_payload)

        date = self.getMessageDate(message)
        announcements = [item for item in announcements if item not in prev_announcements]

        if not SKIP_DATE_CHECK and date.date() != datetime.now().date():
            logger.info("No email from ntust bulletin today (.-.)")
            exit(0)
        if len(announcements) == 0:
            logger.info("No new announcements today (.-.)")
            exit(0)

        return date, announcements

    def fetchBulletinIndices(self):
        status, data = self.client.search(
            None, '(FROM "bulletin@mail.ntust.edu.tw" SUBJECT "NTUST Bulletin")')
        if status != "OK" or len(data) != 1 or not isinstance(data[0], bytes):
            logger.error("Failed to search mails from NTUST Bulletin")
            exit(1)
        indices = list(data[0].decode().split())
        return indices

    def fetchMessage(self, index: str):
        status, data = self.client.fetch(index, "(RFC822)")

        if status != "OK" or len(data) < 1 or not isinstance(data[0], tuple):
            logger.error("Failed to fetch message at index " + index)
            exit(1)
        if len(data[0]) < 2 or not isinstance(data[0][1], bytes):
            logger.error("Failed to fetch message at index " + index)
            exit(1)

        raw_content = data[0][1]
        message = email.message_from_bytes(raw_content)
        return message

    def parsePayload(self, payload: str):
        soup = BeautifulSoup(payload, 'html.parser')

        announcements: list[Announcement] = list()
        for tr in soup.find_all("tr")[1:]:  # the first row is title
            td_from = tr.find("td")
            a_title = tr.find("a")
            announcements.append(Announcement(
                publisher=td_from.text,
                title=emoji.replace_emoji(a_title.text, ""),
                link=a_title["href"],
            ))
        return announcements

    def getMessagePayload(self, message: email.message.Message):
        raw_body = message.get_payload(decode=True)
        if not isinstance(raw_body, bytes):
            logger.error("Failed to parse email: invalid body (type != bytes)")
            exit(1)

        payload = raw_body.decode()
        return payload

    def getMessageDate(self, message: email.message.Message):
        date_format = "%d %b %Y %H:%M:%S %z"

        date_str = message.get("Date")
        if date_str is None:
            logger.error("Failed to parse email: no `Date` in header")
            exit(1)

        date = datetime.strptime(date_str, date_format)
        return date


class SMTPClient():
    server = smtplib.SMTP()
    fromaddr: str

    def __init__(self, user: str, password: str):
        self.fromaddr = f"{user}@{HOST}"

        self.server.connect(HOST, 25)
        self.server.login(user, password)

    def send_many(self, recipients: list[str], subject: str, message: str):
        for recipient in recipients:
            self.send(recipient, subject, message)

    def send(self, recipient: str, subject: str, message: str):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"NTUST Bulletin 2 <{self.fromaddr}>"
        msg["To"] = recipient
        msg.attach(MIMEText(message, "html"))

        self.server.send_message(msg)

    def logout(self):
        self.server.quit()


def generate_subject(date: datetime):
    yesterday = date - timedelta(days=1)
    date_format = "%Y/%m/%d"
    return f"[NTUST Bulletin 2] {yesterday.strftime(date_format)}-{date.strftime(date_format)}"


def generate_message(announcements: list[Announcement]):
    with open("./minified_template.html", "r") as f:
        template = f.read()

    body = "".join(str(item) for item in announcements)
    return template.replace("BODY", body)


if __name__ == "__main__":
    user = os.getenv("MAIL_USER")
    password = os.getenv("MAIL_PASSWORD")
    if user is None or password is None:
        logger.error(
            "Failed to load environment variable `MAIL_USER` & `MAIL_PASSWORD`")
        exit(1)

    imap_client = IMAPClient(user, password)
    date, announcements = imap_client.getAnnouncements()
    imap_client.logout()

    subject = generate_subject(date)
    message = generate_message(announcements)

    recipient = os.getenv("RECIPIENT", f"{user}@{HOST}")

    smtp_client = SMTPClient(user, password)
    smtp_client.send(recipient, subject, message)
    smtp_client.logout()
