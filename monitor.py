import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import yfinance as yf
import pandas as pd

# 挪威主權基金核心台股觀察池（可自行隨時增減代碼）
# 包含台積電、聯發科、日月光、鴻海、台達電、廣達、緯創、致茂、奇鋐等熱門持股
NBIM_WATCHLIST = {
    '2330.TW': '台積電',
    '2454.TW': '聯發科',
    '2317.TW': '鴻海',
    '2308.TW': '台達電',
    '2382.TW': '廣達',
    '3017.TW': '奇鋐',
    '2376.TW': '技嘉',
    '3231.TW': '緯創',
    '2360.TW': '致茂',
    '3034.TW': '聯詠'
}

def check_stock_pullbacks():
    """
    掃描觀察池中的標的，計算是否自近期高點拉回 10% ~ 20%
    """
    pullback_list = []
    
    for ticker, name in NBIM_WATCHLIST.items():
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="3m") # 抓取近 3 個月 K 線數據
            if not df.empty:
                high_price = df['High'].max() # 近 3 個月最高價
                current_price = df['Close'].iloc[-1] # 最新收盤價
                drop_pct = ((high_price - current_price) / high_price) * 100
                
                # 篩選自高點拉回 10% 以上的標的
                if drop_pct >= 10.0:
                    pullback_list.append({
                        'code': ticker.replace('.TW', ''),
                        'name': name,
                        'high': round(high_price, 2),
                        'current': round(current_price, 2),
                        'drop': round(drop_pct, 1)
                    })
        except Exception as e:
            print(f"檢查 {ticker} 失敗: {e}")
            
    return pullback_list

def send_email(subject, body):
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    receiver_email = os.environ.get('RECEIVER_EMAIL')

    if not all([sender_email, sender_password, receiver_email]):
        print("未設定 Email 環境變數。")
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
        print("Email 發送成功！")
    except Exception as e:
        print(f"發送 Email 失敗: {e}")

def main():
    print("開始掃描 NBIM 概念股價格拉回狀況...")
    pullbacks = check_stock_pullbacks()
    
    if pullbacks:
        rows_html = ""
        for item in pullbacks:
            rows_html += f"""
            <tr style='text-align: center;'>
                <td style='border: 1px solid #ddd; padding: 8px;'><b>{item['code']} {item['name']}</b></td>
                <td style='border: 1px solid #ddd; padding: 8px;'>${item['high']}</td>
                <td style='border: 1px solid #ddd; padding: 8px;'>${item['current']}</td>
                <td style='border: 1px solid #ddd; padding: 8px; color: red;'><b>-{item['drop']}%</b></td>
            </tr>
            """
        table_html = f"""
        <h3 style='color: #d9534f;'>🎯 警告：發現以下 NBIM 持股已自高點拉回超過 10%！</h3>
        <table style='border-collapse: collapse; width: 100%;'>
            <thead>
                <tr style='background-color: #f2f2f2;'>
                    <th style='border: 1px solid #ddd; padding: 8px;'>標的</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>3個月高點</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>最新收盤價</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>拉回幅度</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """
    else:
        table_html = "<p>✅ 目前觀察池中的 NBIM 概念股皆未出現 10% 以上的明顯拉回（表現相對強勢）。</p>"

    subject = "【挪威主權基金月報】拉回 10% 觸發標的與檢查通知"
    
    html_content = f"""
    <h2>📊 每月挪威主權基金持股與價格掃描通知</h2>
    <hr>
    <h3>📌 執行步驟簡要：</h3>
    <ol>
        <li><b>觀察超跌標的：</b> 優先檢視下方自動算出的拉回 10% 觀察清單。</li>
        <li><b>雙重確認：</b> 確認同族群是否集體回檔，且大戶籌碼未鬆動。</li>
        <li><b>技術面進場：</b> 開啟券商 App 觀察<b>【第二隻腳鬧鈴（日 KD 黃金交叉/止跌）】</b>。</li>
    </ol>
    <hr>
    {table_html}
    <hr>
    <p><i>祝您交易紀律嚴明，穩健獲利！</i></p>
    """
    
    send_email(subject, html_content)

if __name__ == "__main__":
    main()
