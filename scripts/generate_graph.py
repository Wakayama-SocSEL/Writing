import subprocess
import json
import matplotlib.pyplot as plt
from datetime import datetime
import os

# --- 設定 ---
TARGET_FILE = "test.tex"  # <--- 行数を追跡したいファイル名を指定
DATA_FILE = "data/line_count_history.json"
GRAPH_FILE = "docs/line_count_graph.svg" # <--- 生成するグラフのパス
# -------------

def get_file_line_count(file_path):
    """wc -lコマンドを使ってファイルの行数を計測する。"""
    try:
        # 出力形式は "  123 filename" なので、最初の数値を取得
        output = subprocess.check_output(['wc', '-l', file_path], encoding='utf-8').strip()
        return int(output.split()[0])
    except:
        return 0

def collect_line_count_history(file_path):
    """Git履歴を遡ってデータを収集し、作業ブランチを元に戻す。"""
    print(f"--- {file_path} の行数履歴を収集中 ---")
    
    # 現在のブランチを記録
    current_branch = subprocess.check_output(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
        encoding='utf-8',
        stderr=subprocess.DEVNULL
    ).strip()
    history = []
    
    # 対象ファイルが変更されたコミットハッシュと日付を取得
    try:
        log_output = subprocess.check_output(
            ['git', 'log', '--pretty=format:%H %ct', '--', file_path],
            encoding='utf-8',
            stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        print(f"エラー: ファイル '{file_path}' の履歴が見つかりません。")
        return None
    
    if not log_output:
        print(f"警告: ファイル '{file_path}' の履歴が見つかりませんでした。")
        return []

    commits = [line.split() for line in log_output.split('\n') if line]
    
    # 各コミット時のファイルの行数を計測
    for commit_hash, timestamp in commits:
        # コミット時点のファイルを復元
        subprocess.check_call(
            ['git', 'checkout', commit_hash, '--', file_path],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        line_count = get_file_line_count(file_path)
        history.append({'date': int(timestamp), 'lines': line_count, 'hash': commit_hash})
    
    # Git作業ツリーを元のブランチに戻す (最後に実行される)
    subprocess.call(['git', 'checkout', current_branch, '--force'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    history.sort(key=lambda x: x['date'])
    print(f"収集完了: {len(history)}個のデータポイント。")
    return history

def save_data(data):
    """データをJSONに保存する。"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"データが {DATA_FILE} に保存されました。")

def generate_line_graph(history):
    """データを基に折れ線グラフを生成し、SVGとして保存する。"""
    if not history: 
        print("グラフを生成するためのデータがありません。")
        return

    dates = [datetime.fromtimestamp(item['date']) for item in history]
    lines = [item['lines'] for item in history]

    # --- グラフの描画 ---
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.figure(figsize=(10, 6))
    
    plt.plot(dates, lines, marker='o', linestyle='-', color='#007ACC', label='Lines of Code')
    
    plt.title(f'{TARGET_FILE} Line Count History', fontsize=16)
    plt.xlabel('Date (Commit Time)', fontsize=12)
    plt.ylabel('Lines of Code', fontsize=12)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.gcf().autofmt_xdate()
    
    # グラフをSVGファイルとして保存
    os.makedirs(os.path.dirname(GRAPH_FILE), exist_ok=True)
    plt.savefig(GRAPH_FILE, format='svg', bbox_inches='tight')
    plt.close()
    
    print(f"グラフが {GRAPH_FILE} に保存されました。")

def main():
    # 履歴データの収集
    history_data = collect_line_count_history(TARGET_FILE)
    
    if history_data is not None:
        # データの保存
        save_data(history_data)
        
        # グラフの生成
        generate_line_graph(history_data)

if __name__ == "__main__":
    main()