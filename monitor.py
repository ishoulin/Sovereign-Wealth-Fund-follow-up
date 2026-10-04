import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import yfinance as yf
import pandas as pd

def get_dynamic_nbim_top50(csv_filename='nbim_holdings.csv'):
    """
    從 Repo 內的 CSV 檔案動態解析出最新台灣持股前 50 大標的
    """
    if not os.path.exists(csv_filename):
        print(f"⚠️ 找不到 {csv_filename}，請確認檔案已 Commit 至 Repository。")
        return {}

    try:
        df = pd.read_csv(csv_filename)
        
        # 1. 欄位相容處理（視 NBIM 官方 CSV 欄位名稱自動調整）
        country_col = [c for c in df.columns if 'country' in c.lower()][0]
        name_col = [c for c in df.columns if 'name' in c.lower() or 'company' in c.lower()][0]
        val_col = [c for c in df.columns if 'market value' in c.lower() or 'value' in c.lower()][0]
        ticker_col = [c for c in df.columns if 'ticker' in c.lower() or 'code' in c.lower()]

        # 2. 篩選台灣持股 (Taiwan)
        taiwan_df = df[df[country_col].astype(str).str.contains('Taiwan', case=False, na=False)].copy()
        
        # 3. 依持股市值 (USD) 排序取前 50 大
        taiwan_df[val_col] = pd.to_numeric(taiwan_df[val_col].astype(str).str.replace(',', ''), errors='coerce')
        taiwan_df = taiwan_df.sort_values(by=val_col, ascending=False).head(50)

        top50_dict = {}
        for _, row in taiwan_df.iterrows():
            name = str(row[name_col]).strip()
            
            # 若 CSV 內已有股票代碼則使用，若無則依公司名稱或現有代碼格式處理
            if ticker_col:
                raw_code = str(row[ticker_col[0]]).strip()
                # 處理台股代碼後綴（上市 .TW / 上櫃 .TWO）
                ticker = raw_code if raw_code.endswith(('.TW', '.TWO')) else f"{raw_code}.TW"
            else:
                # 備用邏輯：若 CSV 無代碼欄位，可透過對照字典或轉換名稱
                continue
                
            top50_dict[ticker] = name

        print(f"✅ 成功從 {csv_filename} 解析出 {len(top50_dict)} 檔台灣前 50 大持股。")
        return top50_dict

    except Exception as e:
        print(f"❌ 解析 CSV 失敗: {e}")
        return {}

def check_stock_pullbacks():
    """
    掃描動態取得的前 50 大標的，計算近 3 個月最高價與拉回幅度
    """
    nbim_watchlist = get_dynamic_nbim_top50()
    
    # 若 CSV 解析失敗，可設定一組基礎備用名單
    if not nbim_watchlist:
        print("使用備用預設觀察池...")
        nbim_watchlist = {
            '2330.TW': '台積電', '2454.TW': '聯發科', '2317.TW': '鴻海',
            '2308.TW': '台達電', '2382.TW': '廣達', '3017.TW': '奇鋐',
            '2376.TW': '技嘉', '3231.TW': '緯創', '2360.TW': '致茂', '3034.TW': '聯詠'
        }

    scanned_results = []
    pullback_list = []
    
    for ticker, name in nbim_watchlist.items():
        code = ticker.replace('.TW', '').replace('.TWO', '')
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="3m") # 抓取近 3 個月 K 線數據
            
            # 若上市 .TW 抓不到，嘗試切換為上櫃 .TWO 重新抓取
            if df.empty and ticker.endswith('.TW'):
                alt_ticker = f"{code}.TWO"
                stock = yf.Ticker(alt_ticker)
                df = stock.history(period="3m")

            if not df.empty:
                high_price = df['High'].max() # 近 3 個月最高價
                current_price = df['Close'].iloc[-1] # 最新收盤價
                drop_pct = ((high_price - current_price) / high_price) * 100
                
                item = {
                    'code': code,
                    'name': name,
                    'high': round(high_price, 2),
                    'current': round(current_price, 2),
                    'drop': round(drop_pct, 1)
                }
                
                scanned_results.append(item)
                
                # 篩選自高點拉回 10% 以上的標的
                if drop_pct >= 10.0:
                    pullback_list.append(item)

        except Exception as e:
            print(f"檢查 {ticker} ({name}) 失敗: {e}")
            
    # 將拉回標的按拉回幅度由大到小排序
    pullback_list.sort(key=lambda x: x['drop'], reverse=True)
    return scanned_results, pullback_list

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
