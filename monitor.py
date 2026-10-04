import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

def get_nbim_taiwan_holdings():
    """
    抓取挪威主權基金 (NBIM) 官方最新公佈的台灣持股清單
    """
    # NBIM 官方公開持股 API/JSON 資料源
    url = "https://www.nbim.no/api/investments/holdings/getholdings"
    
    try:
        # 請求最新年份的權益類持股資料
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            # 篩選出國家為 Taiwan 的股票
            taiwan_stocks = [
                item for item in data.get('holdings', []) 
                if item.get('country') == 'Taiwan'
            ]
            # 依持股價值 (USD) 由大到小排序
            taiwan_stocks.sort(key=lambda x: x.get('market_value_usd', 0), reverse=True)
            return taiwan_stocks
    except Exception as e:
        print(f"抓取 NBIM 資料失敗: {e}")
    
    return []

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
    print("正在抓取挪威主權基金最新台灣持股名單...")
    taiwan_holdings = get_nbim_taiwan_holdings()
    
    # 組合持股 HTML 表格
    if taiwan_holdings:
        rows_html = ""
        for i, stock in enumerate(taiwan_holdings[:50], 1):  # 預設列出前 50 大持股
            name = stock.get('name', 'N/A')
            ownership = stock.get('ownership', 0)  # 持股比例 %
            val_usd = stock.get('market_value_usd', 0) / 1000000  # 轉成百萬美元
            
            rows_html += f"""
            <tr>
                <td style='border: 1px solid #ddd; padding: 8px;'>{i}</td>
                <td style='border: 1px solid #ddd; padding: 8px;'><b>{name}</b></td>
                <td style='border: 1px solid #ddd; padding: 8px;'>{ownership:.2f}%</td>
                <td style='border: 1px solid #ddd; padding: 8px;'>${val_usd:,.2f} M</td>
            </tr>
            """
        
        table_html = f"""
        <h3>🇹🇼 挪威主權基金持股 - 台灣前 50 大標的清單</h3>
        <p>（資料來源：NBIM 官方最新公開年報資料，共持有 {len(taiwan_holdings)} 檔台股）</p>
        <table style='border-collapse: collapse; width: 100%; text-align: left;'>
            <thead>
                <tr style='background-color: #f2f2f2;'>
                    <th style='border: 1px solid #ddd; padding: 8px;'>#</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>公司名稱</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>持股比例 (%)</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>持股市值 (USD)</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """
    else:
        table_html = "<p>⚠️ 暫時無法自動取得 NBIM 官方台灣持股清單，請至官網手動查詢。</p>"

    subject = "【挪威主權基金月報】持股清單與檢查通知"
    
    html_content = f"""
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
    {table_html}
    <hr>
    <p><i>祝您這個月交易紀律嚴明，穩健獲利！</i></p>
    """
    
    send_email(subject, html_content)

if __name__ == "__main__":
    main()
