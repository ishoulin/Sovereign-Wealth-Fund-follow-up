import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import yfinance as yf

# ==============================================================================
# 📋 嚴格持股維護區
# 條件 1：挪威主權基金 (NBIM) 持股比例 > 10%
# 條件 2：名列國內前 25 大主流 ETF（0050, 0056, 00878, 00919, 00929等）的前 25 大核心重倉持股
# ==============================================================================
LAST_UPDATE_DATE = "2026-10-01"      # 上次修訂日期
NEXT_UPDATE_DATE = "2027-04-01"      # 建議下次更新日期

# 雙重交集精華清單：[股票名稱]
WATCHLIST = {
    # 權值與半導體
    '2330.TW': '台積電', '2454.TW': '聯發科', '2317.TW': '鴻海', '2308.TW': '台達電',
    '2303.TW': '聯電', '3711.TW': '日月光投控', '2379.TW': '瑞昱', '3034.TW': '聯詠',
    '3661.TW': '世芯-KY', '3443.TW': '創意', '3529.TW': '力旺', '5269.TW': '祥碩',
    '3035.TW': '智原', '6415.TW': '矽力*-KY', '2408.TW': '南亞科', '2337.TW': '旺宏',
    
    # AI 伺服器、散熱與組裝
    '2382.TW': '廣達', '3231.TW': '緯創', '6669.TW': '緯穎', '3017.TW': '奇鋐',
    '2376.TW': '技嘉', '2360.TW': '致茂', '2059.TW': '川湖', '2345.TW': '智邦',
    '2357.TW': '華碩', '1519.TW': '華城', '1504.TW': '東元', '1513.TW': '中興電',
    '3037.TW': '欣興', '8046.TW': '南電', '3189.TW': '景碩', '6271.TW': '同欣電',
    
    # 金融與傳統權值
    '2881.TW': '富邦金', '2882.TW': '國泰金', '2891.TW': '中信金', '2886.TW': '兆豐金',
    '3008.TW': '大立光', '2409.TW': '友達', '3481.TW': '群創', '2603.TW': '長榮',
    '2609.TW': '陽明', '2615.TW': '萬海', '9910.TW': '豐泰', '9921.TW': '巨大',
    '1476.TW': '儒鴻', '1477.TW': '聚陽', '8454.TW': '富邦媒', '6409.TW': '旭隼',
    '6121.TW': '新普', '5483.TW': '中美晶'    
}

def scan_stocks():
    scanned_results = []
    pullback_list = []
    
    print(f"開始掃描 {len(WATCHLIST)} 檔「雙重籌碼交集」標的...")

    for ticker, name in WATCHLIST.items():
        code = ticker.replace('.TW', '').replace('.TWO', '')
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="3mo")
            
            if df.empty and ticker.endswith('.TW'):
                stock = yf.Ticker(f"{code}.TWO")
                df = stock.history(period="3mo")

            if not df.empty:
                high_price = df['High'].max()
                current_price = df['Close'].iloc[-1]
                drop_pct = ((high_price - current_price) / high_price) * 100
                
                item = {
                    'code': code,
                    'name': name,
                    'high': round(high_price, 2),
                    'current': round(current_price, 2),
                    'drop': round(drop_pct, 1)
                }
                
                scanned_results.append(item)
                
                # 🎯 紀律條件：僅鎖定拉回 10.0% ~ 15.0% 的黃金波段區
                if 10.0 <= drop_pct <= 15.0:
                    pullback_list.append(item)
        except Exception as e:
            print(f"掃描 {code} {name} 失敗: {e}")

    # 依跌幅大小排序（跌幅大的排前面）
    pullback_list.sort(key=lambda x: -x['drop'])
    scanned_results.sort(key=lambda x: -x['drop'])
    return scanned_results, pullback_list

def send_email(subject, body):
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    receiver_email = os.environ.get('RECEIVER_EMAIL')

    if not all([sender_email, sender_password, receiver_email]):
        print("未設定 Email 環境變數，跳過發送。")
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
    scanned_results, pullbacks = scan_stocks()
    
    # 1. 觸發黃金觀察區 (10%~15%)
    if pullbacks:
        target_rows = ""
        for item in pullbacks:
            target_rows += f"""
            <tr style='text-align: center;'>
                <td style='border: 1px solid #ddd; padding: 8px;'><b>{item['code']} {item['name']}</b></td>
                <td style='border: 1px solid #ddd; padding: 8px;'>${item['high']}</td>
                <td style='border: 1px solid #ddd; padding: 8px;'>${item['current']}</td>
                <td style='border: 1px solid #ddd; padding: 8px; color: #d9534f;'><b>-{item['drop']}%</b></td>
            </tr>
            """
        target_html = f"""
        <h3 style='color: #d9534f;'>🎯 觸發注意：以下 {len(pullbacks)} 檔雙重認證標的已進入「拉回 10% ~ 15% 黃金觀察區」！</h3>
        <table style='border-collapse: collapse; width: 100%;'>
            <thead>
                <tr style='background-color: #f2f2f2;'>
                    <th style='border: 1px solid #ddd; padding: 8px;'>標的</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>3個月高點</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>最新價</th>
                    <th style='border: 1px solid #ddd; padding: 8px;'>拉回幅度</th>
                </tr>
            </thead>
            <tbody>
                {target_rows}
            </tbody>
        </table>
        """
    else:
        target_html = "<p style='color: green;'><b>✅ 掃描結果：目前沒有核心標的落在 10%～15% 的黃金拉回區。</b></p>"

    # 2. 雙重認證池總覽
    all_rows = ""
    for item in scanned_results:
        color_style = "color: #d9534f; font-weight: bold;" if 10.0 <= item['drop'] <= 15.0 else "color: #333;"
        
        all_rows += f"""
        <tr style='text-align: center;'>
            <td style='border: 1px solid #ddd; padding: 6px;'>{item['code']}</td>
            <td style='border: 1px solid #ddd; padding: 6px;'>{item['name']}</td>
            <td style='border: 1px solid #ddd; padding: 6px;'>${item['high']}</td>
            <td style='border: 1px solid #ddd; padding: 6px;'>${item['current']}</td>
            <td style='border: 1px solid #ddd; padding: 6px; {color_style}'>-{item['drop']}%</td>
        </tr>
        """

    summary_table_html = f"""
    <h3>📋 雙重核心持股掃描總覽（共 {len(scanned_results)} 檔）</h3>
    <table style='border-collapse: collapse; width: 100%; font-size: 14px;'>
        <thead>
            <tr style='background-color: #f8f9fa;'>
                <th style='border: 1px solid #ddd; padding: 6px;'>代號</th>
                <th style='border: 1px solid #ddd; padding: 6px;'>名稱</th>
                <th style='border: 1px solid #ddd; padding: 6px;'>3個月高價</th>
                <th style='border: 1px solid #ddd; padding: 6px;'>最新價</th>
                <th style='border: 1px solid #ddd; padding: 6px;'>拉回幅度</th>
            </tr>
        </thead>
        <tbody>
            {all_rows}
        </tbody>
    </table>
    """

    subject = f"【法人籌碼月報】已鎖定 {len(pullbacks)} 檔精華標的落在黃金拉回區（10%~15%）"
    
    html_content = f"""
    <h2>📊 挪威基金 (>10%) + 國內主要 ETF 前25大重倉 雙重掃描通知</h2>
    <div style='background-color: #e9ecef; padding: 10px 15px; border-radius: 5px; margin-bottom: 15px;'>
        <b>🛠️ 持股清單維護狀態：</b><br>
        • 上次修訂日期：<b>{LAST_UPDATE_DATE}</b><br>
        • 建議下次更新：<b>{NEXT_UPDATE_DATE}</b>（建議每半年核對一次各大 ETF 權重）
    </div>
    <hr>
    <h3>📌 交易紀律提醒：</h3>
    <ol>
        <li><b>雙重保險：</b> 清單標的皆通過「挪威基金長線持有 >10%」與「國內主流 ETF 前25大重倉」雙重審核。</li>
        <li><b>進場驗證：</b> 避開暴跌 >20% 有基本面疑慮的刀子，僅在拉回 10%~15% 且日 KD 築底時觀察進場。</li>
    </ol>
    <hr>
    {target_html}
    <hr>
    {summary_table_html}
    <hr>
    <p><i>祝您交易紀律嚴明，穩健獲利！</i></p>
    """
    
    send_email(subject, html_content)

if __name__ == "__main__":
    main()
