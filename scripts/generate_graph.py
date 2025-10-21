import subprocess
import json
import matplotlib.pyplot as plt
from datetime import datetime
import os

# --- 設定 ---
# 追跡したいファイルをリストで指定します。
TARGET_FILES = [
    "@IPSJ_SIGSE202511_Hashimoto/IPSJ_SIGSE202511_Hashimoto.tex",  
    "@IPSJ_SIGSE202511_Horio/IPSJ_SIGSE202511_Horio.tex",  
    "@IPSJ_SIGSE202511_Noguchi/IPSJ_SIGSE202511_Noguchi.tex",
    "@IPSJ_SIGSE202511_Toyoshima/IPSJ_SIGSE202511_Toyoshima.tex"
] 
FILE_LABELS = {
    "@IPSJ_SIGSE202511_Hashimoto/IPSJ_SIGSE202511_Hashimoto.tex": "橋本",
    "@IPSJ_SIGSE202511_Horio/IPSJ_SIGSE202511_Horio.tex": "堀尾",
    "@IPSJ_SIGSE202511_Noguchi/IPSJ_SIGSE202511_Noguchi.tex": "野口",
    "@IPSJ_SIGSE202511_Toyoshima/IPSJ_SIGSE202511_Toyoshima.tex": "豊嶋"
}
DATA_FILE = "data/line_count_history.json"
GRAPH_FILE = "docs/line_count_graph.svg"
# -------------

# (get_file_line_count 関数は変更なし)
def get_file_line_count(file_path):
    """wc -lコマンドを使ってファイルの行数を計測する。"""
    try:
        output = subprocess.check_output(['wc', '-l', file_path], encoding='utf-8').strip()
        return int(output.split()[0])
    except:
        return 0

def collect_line_count_history(file_paths):
    """複数のファイルパスを受け取り、それぞれの履歴を収集する。"""
    print("--- 複数ファイルの行数履歴を収集中 ---")
    current_branch = subprocess.check_output(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
        encoding='utf-8',
        stderr=subprocess.DEVNULL
    ).strip()
    full_history = {} 
    cutoff_timestamp = 1760665250  # 2025年10月17日 00:00:00 (UTC)

    for file_path in file_paths:
        file_history = []
        try:
            log_output = subprocess.check_output(
                ['git', 'log', '--pretty=format:%H %ct', '--', file_path],
                encoding='utf-8',
                stderr=subprocess.DEVNULL
            ).strip()
        except subprocess.CalledProcessError:
            print(f"警告: ファイル '{file_path}' の履歴が見つかりません。スキップします。")
            continue
        commits = [line.split() for line in log_output.split('\n') if line]
        for commit_hash, timestamp in commits:
            if int(timestamp) < cutoff_timestamp:
                continue  # 2025年10月17日より前はスキップ
            subprocess.check_call(
                ['git', 'checkout', commit_hash, '--', file_path],
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            line_count = get_file_line_count(file_path)
            file_history.append({'date': int(timestamp), 'lines': line_count, 'hash': commit_hash})
        file_history.sort(key=lambda x: x['date'])
        full_history[file_path] = file_history
    subprocess.call(['git', 'checkout', current_branch, '--force'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("収集完了。")
    return full_history

def save_data(data):
    """データをJSONに保存する。"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"データが {DATA_FILE} に保存されました。")

def generate_line_graph(full_history):
    """全ファイルの履歴データから一つのグラフを生成する。"""
    if not full_history: 
        print("グラフを生成するためのデータがありません。")
        return

    # --- グラフの描画 ---
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.figure(figsize=(12, 7))
    
    # Matplotlibのデフォルトのカラーサイクラーを使用
    # これにより、plt.plotを呼び出すたびに異なる色が自動的に割り当てられる
    
    for file_path, history in full_history.items():
        if not history:
            continue
            
        dates = [datetime.fromtimestamp(item['date']) for item in history]
        lines = [item['lines'] for item in history]
        
        label = FILE_LABELS.get(file_path, file_path)  # 対応辞書から表示名を取得
        plt.plot(dates, lines, marker='o', linestyle='-', label=label) 
    
    # グラフのメタ情報を設定
    plt.title('Multi-File Line Count History', fontsize=16)
    plt.xlabel('Date (Commit Time)', fontsize=12)
    plt.ylabel('Lines of Code', fontsize=12)
    
    # 凡例を表示
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=10) # 凡例をグラフの外に配置
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.gcf().autofmt_xdate()
    
    # 凡例がはみ出さないようにレイアウトを調整
    plt.tight_layout(rect=[0, 0, 0.85, 1]) # rectでグラフ描画領域を調整

    # グラフをSVGファイルとして保存
    os.makedirs(os.path.dirname(GRAPH_FILE), exist_ok=True)
    plt.savefig(GRAPH_FILE, format='svg', bbox_inches='tight')
    plt.close()
    
    print(f"グラフが {GRAPH_FILE} に保存されました。")

def main():
    history_data = collect_line_count_history(TARGET_FILES)
    
    if history_data is not None:
        save_data(history_data)
        generate_line_graph(history_data)

if __name__ == "__main__":
    main()