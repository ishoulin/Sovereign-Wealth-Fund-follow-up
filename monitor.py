import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import yfinance as yf

# 預備觀察池（若未上傳 nbim_holdings.csv 時使用）
DEFAULT_WATCHLIST = {
    '2330.TW': '台積電', '2454.TW': '聯發科', '2317.TW': '鴻海', '2308.TW': '台達電', 
    '2382.TW': '廣達', '2379.TW': '瑞昱', '3034.TW': '聯詠', '2303.TW': '聯電', 
    '3711.TW': '日月光投控', '2881.TW': '富邦金', '2882.TW': '國泰金', '2891.TW': '中信金', 
    '2886.TW': '兆豐金', '3008.TW': '大立光', '2357.TW': '華碩', '3231.TW': '緯創', 
    '6669.TW': '緯穎', '3017.TW': '奇鋐', '2376.TW': '技嘉', '2360.TW': '致茂'
}

def get_nbim_watchlist(csv_filename='nbim_holdings.csv'):
    """
    動態讀取 CSV，若無 CSV 則自動切換至預備清單
    """
    if not os.path.exists(csv_filename):
        print(f"⚠️ 找不到 {csv_filename}，使用預備觀察池進行掃描...")
        return DEFAULT_WATCHLIST

    try:
        df = pd.read_csv(csv_filename)
        country_col = [c for c in df.columns if 'country' in c.lower()][0]
        name_col = [c for c in df.columns if 'name' in c.lower() or 'company' in c.lower()][0]
        val_col = [c for c in df.columns if 'market value' in c.lower() or 'value' in c.lower()][0]
        ticker_col = [c for c in df.columns if 'ticker' in c.lower() or 'code' in c.lower()]

        taiwan_df = df[df[country_col].astype(str).str.contains('Taiwan', case=False, na=False)].copy()
        taiwan_df[val_col] = pd.to_numeric(taiwan_df[val_col].astype(str).str.replace(',', ''), errors='coerce')
        taiwan_df = taiwan_df.sort_values(by=val_col, ascending=False).head(50)

        watchlist = {}
        for _, row in taiwan_df.iterrows():
            name = str(row[name_col]).strip()
            if ticker_col:
                raw_code = str(row[ticker_col[0]]).strip().replace('$', '')
                ticker = raw_code if raw_code.endswith(('.TW', '.TWO')) else f"{raw_code}.TW"
                watchlist[ticker] = name
                
        return watchlist if watchlist else DEFAULT_WATCHLIST
    except Exception as e:
        print(f"❌ 解析 CSV 失敗 ({e})，切換至預備觀察池...")
        return DEFAULT_WATCHLIST

def scan_stocks():
    """
    掃描標的，計算近 3 個月高點與拉回幅度
    """
    watchlist = get_nbim_watchlist()
    scanned_results = []
    pullback_list = []
    
    print(f"開始執行 {len(watchlist)} 檔標的價格掃描...")

    for ticker, name in watchlist.items():
        code = ticker.replace('.TW', '').replace('.TWO', '')
        try:
            stock = yf.Ticker(ticker)
            # 修正 1：yfinance 3個月的正確參數是 '3mo'，而非 '3m'
            df = stock.history(period="3mo")
            
            # 若上市 (.TW) 抓不到，備用嘗試上櫃 (.TWO)
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
                if drop_pct >= 10.0:
                    pullback_list.append(item)
        except Exception as e:
            print(f"掃描 {code} {name} 失敗: {e}")

    pullback_list.sort(key=lambda x: x['drop'], reverse=True)
    return scanned_results, pullback_list

def send_email(subject, body):
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    receiver_email = os.environ.get('RECEIVER_EMAIL')

    if not all([sender_email, sender_password, receiver_email]):
        print("未設定 Email 環境變數，無法發送。")
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
    
    # 1. 處理拉回 >= 10% 區塊
    if pullbacks:
        target_rows = ""
        # 修正 2：迭代正確的字典元素 item
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
        <h3 style='color: #d9534f;'>🎯 觸發注意：以下 {len(pullbacks)} 檔標的已自近 3 個月高點拉回超過 10%！</h3>
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
                {target_rows}
            </tbody>
        </table>
        """
    else:
        target_html = "<p style='color: green;'><b>✅ 掃描結果：觀察標的目前皆未出現 10% 以上的明顯拉回。</b></p>"

    # 2. 處理全量掃描結果表格
    all_rows = ""
    for item in scanned_results:
        color_style = "color: #d9534f; font-weight: bold;" if item['drop'] >= 10.0 else "color: #333;"
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
    <h3>📋 持股完整掃描總覽（已驗證 {len(scanned_results)} 檔）</h3>
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

    subject = f"【挪威主權基金月報】持股掃描完畢（發現 {len(pullbacks)} 檔拉回 >10%）"
    
    html_content = f"""
    <h2>📊 每月挪威主權基金持股與價格掃描通知</h2>
    <hr>
    <h3>📌 交易紀律提醒：</h3>
    <ol>
        <li><b>觀察超跌標的：</b> 優先檢視下方拉回超過 10% 的觀察清單。</li>
        <li><b>雙重確認：</b> 確認同族群是否集體回檔，且千張大戶籌碼未鬆動。</li>
        <li><b>技術面進場：</b> 開啟券商 App 觀察<b>【第二隻腳鬧鈴（日 KD 黃金交叉/止跌）】</b>。</li>
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
