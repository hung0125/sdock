import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, font
from time import time, mktime, sleep
import requests as rq
import numpy as np
from os.path import isfile
from json import loads, dumps
from datetime import datetime
from tabulate import tabulate

# tmp storage ------------------------------------------------
trade_details = []
month_gain_details = {} # key = stock code
templateScript = b'''
General tech:GOOG MSFT META AMZN
AI:SMCI NVDA MU AVGO
Payments:V MA AXP
Oil:CVX XOM HES
Defensive:BRK-B KO MSI COST
Construction: DHI LEN PHM
Trading centers:CBOE NDAQ SPGI
Shorts:SDOW SPXU FAZ KOLD
Filter:ETF:IVV VUG BRK-B VOO QQQ
Filter:AI Energy:VST NRG TLN AMAT KLAC
Filter:Sun Energy:FSLR ENPH RUN
Filter:Defensive:[Drink] KO PEP [Telecom] MSI TMUS [Payment] V MA AXP [Store] WMT TGT COST [Construction] DHI LEN PHM [Bank] JPM BAC
'''.strip()
if not isfile('stocksDB.txt'):
    open('stocksDB.txt', 'wb').write(templateScript)
# tmp storage ------------------------------------------------

# prep -------------------------------------------------------
header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive',
        }
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
nxt_mth = {}
for i in range(len(months)):
    nxt_mth[months[i]] = months[(i + 1) % 12]
stocks = []
s_button_names = []
stocksDB = open('stocksDB.txt', 'rb').read().decode('utf-8').splitlines()
for i in range(len(stocksDB)):
    comp = stocksDB[i].split(':')
    use_idx = 2 if comp[0] == 'Filter' else 1
    if comp[0] == 'Filter':
        s_button_names.append(f'{comp[0]} ({comp[1]})')
    else:
        s_button_names.append(comp[0])
    
    stks = []
    for S in comp[use_idx].split():
        if not S.startswith('['):
            stks.append(S)
    stocks.append(stks)

def ts2date(timestamp):
    # Convert the timestamp to a datetime object
    dt_object = datetime.fromtimestamp(timestamp)
    # Format the datetime object to the desired format
    formatted_date = dt_object.strftime('%d %b %Y')
    return formatted_date

date_now = ts2date(time()).split()

def pchange(new, old):
    return ((new - old) / old) * 100

def calcDays(cur_ts, last_ts):
    ts1 = int( ( cur_ts - last_ts)/86400 )
    return ts1 - (int(ts1/7) * 2)

def getBaseTx(dat, emas_line, idx):
    return {'date': dat['chart']['result'][0]['timestamp'][idx], 
            'buy': False,
            'price': 0,
            'ema': emas_line[-1][-1]}

def mo_analysis(m_gains, stockcode):
    final_out = ''
    wins = []
    for M in months:
        lth = m_gains[M][0] > 0 if m_gains[M][0] != 0 else m_gains[M][1] > 0
        gain_str = " -> ".join([str(round(num, 1)) if num != 0 else '?' for num in m_gains[M]][::-1])
        final_out += f'{M}{'*' if lth else ''}\t({m_gain_confd(m_gains[M])}): {round(np.mean(m_gains[M]), 2)}%\tAll: ({gain_str})\n'
        
        to_num = m_gain_confd(m_gains[M])[:-1].split('/')
        if int(to_num[1]) > 0:
            wins.append(int(to_num[0])/int(to_num[1]) * 100)

    cur_vals = list(combo_mth["values"])
    cur_vals.append(f'{stockcode},avg_win={round(np.mean(wins), 1)}%,max_win={round(np.max(wins), 1)}%')
    combo_mth["values"] = tuple(cur_vals)
    
    month_gain_details[stockcode] = final_out

def m_gain_confd(gain_arr):
    clean_arr = []
    for N in gain_arr:
        if N != 0 or N != 0.0:
            clean_arr.append(N)
    arr = np.array(clean_arr)
    # Calculate the percentage of positive numbers
    positive_count = np.sum(arr > 0)
    total_count = arr.size
    return f'{positive_count}/{total_count}y'

def base_stock_anal(stock_idx_or_name):
    global trade_details

    stock_c = stock_idx_or_name
    choice_isnum = False
    filter_mode = False
    try:
        stock_c = int(stock_c)
        choice_isnum = True
        comp = stocksDB[stock_c].split(':')
        if comp[0] == 'Filter':
            filter_mode = True
            output_table_f.pack()
            output_table.pack_forget()
        else:
            output_table.pack()
            output_table_f.pack_forget()
    except:
        pass

    if not choice_isnum:
        stocks.append([stock_c])
        stock_c = len(stocks) - 1
        output_table.pack()
        output_table_f.pack_forget()


    filter_list = []
    cnt = 0
    
    for S in stocks[stock_c]:
        try:
            sleep(0.25)
            cnt += 1
            root.update_idletasks()
            resp = rq.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{S}?range=1y&interval=1d&indicators=quote&includeTimestamps=true&corsDomain=finance.yahoo.com", headers=header)
            resp_m = rq.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{S}?range=10y&interval=1mo&indicators=quote&includeTimestamps=true&corsDomain=finance.yahoo.com", headers=header)
            dat = loads(resp.text)
            dat_m = loads(resp_m.text)['chart']['result'][0]

            # do monthly analysis
            opens_m = dat_m['indicators']['quote'][0]['open']
            opens_m.pop()
            closes_m = dat_m['indicators']['quote'][0]['close']
            closes_m.pop()
            dat_m['timestamp'].pop()
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            m_gains = {}
            for M in months:
                m_gains[M] = [0] * 10
            
            for i in range(len(opens_m)):
                p_op = opens_m[i]
                p_cl = closes_m[i]
                ts = ts2date(dat_m['timestamp'][i]).split() # d m y
                # if ts[1] == 'Sep':
                #     print(f'[{ts[1]}]{int(date_now[2])}-{int(ts[2])}-1 -> {p_op}, {p_cl}, {pchange(p_cl, p_op)}')
                use_idx = int(date_now[2])-int(ts[2])
                if use_idx == 10:
                    use_idx -= 1
                m_gains[ts[1]][use_idx] += pchange(p_cl, p_op)

            # do emas
            ps = dat['chart']['result'][0]['indicators']['quote'][0]
            closes = list(ps['close'])
            emas_days = [5, 10, 20, 30, 50]
            emas_line = []
            emas_trades = []

            for ED in emas_days:
                windows = closes[:ED] # closed price in first ED days
                emas_line.append([np.mean(np.array(windows))])
                
                in_buy = False
                cur_trades = []
                wons = 0
                losses = 0
                gain_p = 0
                buy_intervals = [] # days
                last_buy_ts = dat['chart']['result'][0]['timestamp'][0]
                last_sell_ts = -1
                
                for i in range(10, len(closes)): # day 11, really analyze
                    # buy signal
                    if closes[i] >= emas_line[-1][-1] and not in_buy:
                        tx = getBaseTx(dat, emas_line, i)
                        tx['price'] = closes[i]
                        tx['buy'] = True
                        in_buy = True

                        ts_cur = dat['chart']['result'][0]['timestamp'][i]
                        buy_intervals.append(calcDays(ts_cur, last_buy_ts))
                        last_buy_ts = ts_cur
                        last_sell_ts = -1
                        cur_trades.append(tx)
                    # sell signal
                    if closes[i] < emas_line[-1][-1] and in_buy and len(cur_trades) > 0:
                        tx = getBaseTx(dat, emas_line, i)
                        tx['price'] = closes[i]
                        
                        change = pchange(closes[i], cur_trades[-1]['price'])
                        tx['gain'] = round(change, 2)
                        
                        if change > 0:
                            wons += 1
                        else:
                            losses += 1
                        gain_p += change
                        
                        tx['buy'] = False
                        in_buy = False
                        cur_ts = dat['chart']['result'][0]['timestamp'][i]
                        if cur_ts >= last_buy_ts:
                            last_sell_ts = cur_ts
                        cur_trades.append(tx)
                        

                    windows.pop(0)
                    windows.append(closes[i])
                    # add ema value
                    emas_line[-1].append(np.mean(np.array(windows)))
                    

                emas_trades.append({'trades': cur_trades, 
                                    'wons': wons, 
                                    'losses': losses, 
                                    'gainp': gain_p, 
                                    'avgbuydays': int(np.mean(np.array(buy_intervals))),
                                    'lastbuyts': [last_buy_ts, last_sell_ts]})
            

            if not filter_mode:
                prt(f"Results - {S} (${dat['chart']['result'][0]['meta']['regularMarketPrice']}) From {ts2date(dat['chart']['result'][0]['timestamp'][0])} to {ts2date(dat['chart']['result'][0]['timestamp'][-1])}:\n")
            
            res = [] # summary table
            winr_ma5 = 0
            winr_ma10 = 0
            
            for i in range(len(emas_trades)):
                wr = emas_trades[i]['wons']/(emas_trades[i]['wons']+emas_trades[i]['losses'])*100
                if emas_days[i] == 5:
                    winr_ma5 = wr
                elif emas_days[i] == 10:
                    winr_ma10 = wr
                
                data_tup = (
                    S,
                    emas_days[i],
                    f"{emas_trades[i]['wons']}/{emas_trades[i]['losses']} [{round(wr, 2)}%]",
                    round(emas_trades[i]['gainp'], 2),
                    round(emas_line[i][-1], 2),
                    str(emas_trades[i]['avgbuydays']) + ' days',
                    ts2date(emas_trades[i]['lastbuyts'][0]) + ('-' + ts2date(emas_trades[i]['lastbuyts'][1]) if emas_trades[i]['lastbuyts'][1] > 0 else '')
                )
                output_table.insert("", "end", values=data_tup)
                res.append(list(data_tup))

            output_table.insert("", "end", values=('_' * 5,) * 8)

            if filter_mode:
                use_idx = 0 if winr_ma5 >= winr_ma10 else 1
                reg_p = dat['chart']['result'][0]['meta']['regularMarketPrice']
                month_now = m_gains[date_now[1]]
                month_nxt = m_gains[nxt_mth[date_now[1]]]
                res[use_idx][0] = S
                res[use_idx][5] = f'{reg_p} [{round(pchange(reg_p, res[use_idx][4]), 2)}%]'
                res[use_idx].append(f'{round(np.mean(month_now), 1)}({m_gain_confd(month_now)})->{round(np.mean([month_nxt]), 1)}({m_gain_confd(month_nxt)})')
                res[use_idx].append(emas_trades[use_idx]['lastbuyts'][0])
                filter_list.append(res[use_idx])
                prt(f"Analyzed: {S} [{cnt}/{len(stocks[stock_c])}]\n")
            
            # detail mode
            res.append([len(emas_trades)+1, 'Quit', '-', '-', '-', '-', '-'])
            # print(tabulate(res, headers=['Choice', 'EMA D.', 'Win/Lose', 'Gain %', 'Last EMA $', 'Avg Buy Intv.', 'Last Trade'], tablefmt='mixed_grid'))
            mo_analysis(m_gains, S)

            for k in range(5):
                for T in emas_trades[k]['trades']:
                    tmp_date = ts2date(T["date"])
                    tmp_mth_gain = m_gains[tmp_date.split()[1]]
                    trade_details.append([
                        S,
                        emas_days[k],
                        tmp_date,
                        "buy" if T["buy"] else "sell",
                        round(T["ema"], 2),
                        f'{round(T["price"], 2)} [{round(pchange(T["price"], T["ema"]), 2)}%]',
                        '↓' if T['buy'] else T['gain'],
                        f'{round(np.mean(tmp_mth_gain), 1)} ({m_gain_confd(tmp_mth_gain)})'
                    ])

            # progress
            pb['value'] += 1/len(stocks[stock_c]) * 100
        except:
            prt("Error processing " + S)
            pb['value'] += 1/len(stocks[stock_c]) * 100
    
    # do filter mode stuff
    if filter_mode:
        filter_list.sort(key=lambda wr: wr[-1], reverse=True)
        for F in filter_list:
            F.pop() # remove buy timestamp
            output_table_f.insert("", "end", values=tuple(F))
        print(tabulate(filter_list, headers=['Code', 'EMA D.', 'Win/Lose', 'Gain %', 'Last EMA $', '$ Now', 'Last Trade', f'Near Mth Gain %'], tablefmt='mixed_grid'))
    
    if len(stocks[stock_c]) == 1:
        input_stock.delete(0, tk.END)
        input_stock.insert(0, stocks[stock_c][0])

def clear_tmp():
    global trade_details, month_gain_details
    trade_details = []
    month_gain_details = {}
    combo_mth['values'] = []
    combo_mth.set('Select one')
    pb['value'] = 0
    input_stock.delete(0, tk.END)

# ------------------------------------------------------------
def prt(text):
    output_text.insert(tk.END, text)
    output_text.see(tk.END)

def custom_messagebox(title, message, font_size):
    # Create a new top-level window
    top = tk.Toplevel()
    top.title(title)
    
    # Set the font
    custom_font = font.Font(size=font_size)
    
    # Create a label with the custom font
    label = tk.Label(top, text=message, font=custom_font, anchor='w', justify='left')
    label.pack(padx=20, pady=20)
    
    # Create an OK button to close the message box
    ok_button = tk.Button(top, text="OK", command=top.destroy)
    ok_button.pack(pady=10)

# Function to handle button click in the first row
def handle_first_row_button_click(index):
    clear_tmp()
    output_text.delete('1.0', 'end')
    for item in output_table.get_children():
        output_table.delete(item)
    for item in output_table_f.get_children():
        output_table_f.delete(item)
    base_stock_anal(index)

# Function to handle text input button click
def handle_single_search():
    clear_tmp()
    output_text.delete('1.0', 'end')
    for item in output_table.get_children():
        output_table.delete(item)
    for item in output_table_f.get_children():
        output_table_f.delete(item)
    input_text = text_input.get()
    base_stock_anal(input_text)

def handle_4th_row_button_click(index):
    prt(f"4th row button {index} clicked\n")

# Function to handle button click in the 4th and 5th rows
def handle_5th_6th_row_button_click(index):
    prt(f"5th/6th row button {index} clicked\n")

def handle_trades():
    search_stock = input_stock.get()
    search_ema = combo_ema.get()
    if not output_table.get_children():
        prt("[Err] Search from overview first.")
        return
    if not search_stock or not search_ema:
        prt("[Err] Fill in all the blanks first.")
        return
    
    for item in output_table_t.get_children():
        output_table_t.delete(item)

    for T in trade_details:
        if T[0].lower() == search_stock.lower() and T[1] == int(search_ema):
            output_table_t.insert("", "end", values=(T[2], T[3], T[4], T[5], T[6], T[7]))

def handle_month_analysis(event):
    if not combo_mth.get(): return
    selected_value = combo_mth.get().split(',')
    
    custom_messagebox(f"Monthly Gain Summary ({selected_value[0]}): By month - Average WR: {selected_value[1].split('=')[1]}, Max WR: {selected_value[2].split('=')[1]}%", month_gain_details[selected_value[0]], 12)


# Create the main window
root = tk.Tk()
root.title("Sdock - Your Trading Tenga💦")
root.geometry("800x650")

# First row: dynamically generated buttons based on file contents
pb = ttk.Progressbar(root, orient='horizontal', mode='determinate', length=560)
pb.pack()

nav_rows = (len(s_button_names) + 4) // 5

for r in range(nav_rows):
    nav_frame = ttk.Frame(root)
    nav_frame.pack()

    for i in range(5):
        idx = r * 5 + i
        if idx == len(s_button_names):
            break 
        button = tk.Button(nav_frame, text=s_button_names[idx], command=lambda i=idx: handle_first_row_button_click(i))
        button.pack(side=tk.LEFT)

# Second row: text input box and a button to handle the input text
second_row_frame = tk.Frame(root)
second_row_frame.pack()

text_widget_trade = tk.Label(second_row_frame, text="Search by code")
text_widget_trade.pack(side=tk.LEFT)

text_input = tk.Entry(second_row_frame)
text_input.pack(side=tk.LEFT)

input_button = tk.Button(second_row_frame, text="GO",command=handle_single_search)
input_button.pack(side=tk.LEFT, padx=10)

# Third row: text area for program output
output_text = scrolledtext.ScrolledText(root, width=80, height=5)
output_text.pack()

# Table - overviews
text_widget_trade = tk.Label(root, text="Overview")
text_widget_trade.pack()
tf = ttk.Frame(root)
tf.pack()
output_table = ttk.Treeview(tf, columns=("stock", "emad", "winrate", "gainp", "lastema", "avgbuyintv", "lasttrade"), show='headings', height=6)
output_table.pack(side=tk.LEFT)

output_table.heading("stock", text="Stock")
output_table.heading("emad", text="EMA Days")
output_table.heading("winrate", text="Win Rate")
output_table.heading("gainp", text="Gain %")
output_table.heading("lastema", text="Last EMA $")
output_table.heading("avgbuyintv", text="Avg Buy Intv")
output_table.heading("lasttrade", text="Last Trade")
output_table.column("stock", width=50)
output_table.column("emad", width=80)
output_table.column("winrate", width=100)
output_table.column("gainp", width=50)
output_table.column("lastema", width=120)
output_table.column("avgbuyintv", width=120)

scrollbar = ttk.Scrollbar(tf, orient="vertical", command=output_table.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

output_table.configure(yscrollcommand=scrollbar.set)
# f
output_table_f = ttk.Treeview(tf, columns=("stock", "emad", "winrate", "gainp", "lastema", "pricenow", "lasttrade", "avggainnext"), show='headings', height=6)
output_table_f.pack(side=tk.LEFT)

output_table_f.heading("stock", text="Stock")
output_table_f.heading("emad", text="EMA Days")
output_table_f.heading("winrate", text="Win Rate")
output_table_f.heading("gainp", text="Gain %")
output_table_f.heading("lastema", text="Last EMA $")
output_table_f.heading("pricenow", text="Price Now")
output_table_f.heading("lasttrade", text="Last Trade")
output_table_f.heading("avggainnext", text="Avg Gain Next%")
output_table_f.column("stock", width=50)
output_table_f.column("emad", width=80)
output_table_f.column("winrate", width=100)
output_table_f.column("gainp", width=50)
output_table_f.column("lastema", width=120)
output_table_f.column("pricenow", width=120)
output_table_f.column("lasttrade", width=120)
output_table_f.column("avggainnext", width=150)

scrollbar_f = ttk.Scrollbar(tf, orient="vertical", command=output_table_f.yview)
scrollbar_f.pack(side=tk.RIGHT, fill=tk.Y)

output_table_f.configure(yscrollcommand=scrollbar_f.set)
#
output_table.pack_forget()
scrollbar.pack_forget()
output_table_f.pack_forget()
scrollbar_f.pack_forget()

# Table - trades
trade_row_frame = tk.Frame(root)
trade_row_frame.pack()
txt_trade = tk.Label(trade_row_frame, text="Trades: ")
txt_trade.pack(side=tk.LEFT)
txt_stock = tk.Label(trade_row_frame, text="Stock")
txt_stock.pack(side=tk.LEFT)
input_stock = tk.Entry(trade_row_frame)
input_stock.pack(side=tk.LEFT)
txt_ema = tk.Label(trade_row_frame, text="Ema")
txt_ema.pack(side=tk.LEFT)
combo_ema = ttk.Combobox(trade_row_frame, state="readonly", values=["5", "10", "20", "30", "50"])
combo_ema.pack(side=tk.LEFT)
input_button = tk.Button(trade_row_frame, text="GO",command=handle_trades)
input_button.pack(side=tk.LEFT, padx=10)

tf2 = ttk.Frame(root)
tf2.pack()
output_table_t = ttk.Treeview(tf2, columns=("date", "action", "emap", "atp", "gainp", "monthavg"), show='headings', height=9)
output_table_t.pack(side=tk.LEFT)

output_table_t.heading("date", text="Date")
output_table_t.heading("action", text="Action")
output_table_t.heading("emap", text="EMA $")
output_table_t.heading("atp", text="At Price")
output_table_t.heading("gainp", text="Gain %")
output_table_t.heading("monthavg", text="Monthly Avg")
output_table_t.column("date", width=100)
output_table_t.column("action", width=50)
output_table_t.column("emap", width=100)
output_table_t.column("atp", width=100)
output_table_t.column("gainp", width=50)
output_table_t.column("monthavg", width=120)

scrollbar_t = ttk.Scrollbar(tf2, orient="vertical", command=output_table_t.yview)
scrollbar_t.pack(side=tk.RIGHT, fill=tk.Y)

output_table_t.configure(yscrollcommand=scrollbar_t.set)

# row: monthly analysis
month_frame = tk.Frame(root)
month_frame.pack()

txt_mth = tk.Label(month_frame, text="Monthly analysis: ")
txt_mth.pack(side=tk.LEFT)

combo_mth = ttk.Combobox(month_frame, state="readonly", values=[], width=40)
combo_mth.pack(side=tk.LEFT)
combo_mth.bind("<<ComboboxSelected>>", handle_month_analysis)
combo_mth.set('Select one')

# Run the main loop
root.mainloop()