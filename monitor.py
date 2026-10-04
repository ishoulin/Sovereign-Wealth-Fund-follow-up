import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(subject, body):
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    receiver_email = os.environ.get('RECEIVER_EMAIL')

    if not all([sender_email, sender_password, receiver_email]):
        print("未設定 Email 環境變數，無法發送郵件。")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Email 通知發送成功！")
    except Exception as e:
        print(f"發送 Email 失敗: {e}")

def main():
    # 這裡可以撰寫爬蟲抓取公開資訊或你的觀察清單
    # 以下為發送給你的月度檢查提醒模板：
    
    subject = "【挪威主權基金月報】持股檢查與超跌 10% 觀察清單"
    
    html_content = """
    <h2>📊 每月挪威主權基金持股與價格掃描通知</h2>
    <p>這是您設定的 GitHub 機器人月度通知。</p>
    
    <hr>
    <h3>📌 檢查任務備忘錄：</h3>
    <ol>
        <li><b>比對最新持股：</b> 確認關注的標的是否仍留在 NBIM 名單內（未被清倉剔除）。</li>
        <li><b>鎖定拉回標的：</b> 檢查持股池中是否有標的自高點拉回 <b>10%~15%</b>。</li>
        <li><b>雙重確認：</b> 確認該拉回為同產業集體回檔，且千張大戶籌碼未鬆動。</li>
        <li><b>觸發點：</b> 若條件滿足，開啟券商 App 觀察<b>【第二隻腳鬧鈴（日 KD 黃金交叉/止跌）】</b>準備分批佈局。</li>
    </ol>
    <hr>
    <p><i>祝您這個月交易紀律嚴明，穩健獲利！</i></p>
    """
    
    send_email(subject, html_content)

if __name__ == "__main__":
    main()
