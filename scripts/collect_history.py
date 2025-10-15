import subprocess
import json
import os
from datetime import datetime

# --- 設定 ---
TARGET_FILE = "test.tex"  # 行数を追跡したいファイル名
DATA_FILE = "data/line_count_history.json"
# -------------

def get_file_line_count(file_path):
    """
    wc -lコマンドを使ってファイルの行数を計測する。
    """
    try:
        # wc -lで計測し、出力から行数（最初の数値）を取得
        output = subprocess.check_output(['wc', '-l', file_path], encoding='utf-8').strip()
        # 出力形式は "  123 filename" なので、最初のスペース以外の部分を取得
        return int(output.split()[0])
    except Exception as e:
        print(f"警告: ファイル {file_path} の行数計測に失敗しました: {e}")
        return 0

def collect_line_count_history(file_path):
    """
    Git履歴を遡って、指定されたファイルの行数と日付の履歴を取得する。
    """
    print(f"--- {file_path} の行数履歴を収集中 ---")
    
    # 既存の作業ブランチを記録
    try:
        current_branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
            encoding='utf-8'
        ).strip()
    except:
        current_branch = None

    history = []
    
    # 1. 対象ファイルが変更されたコミットハッシュと日付（タイムスタンプ）を取得
    # --pretty=format:'%H %ct' は「コミットハッシュ タイムスタンプ」の形式
    try:
        log_output = subprocess.check_output(
            ['git', 'log', '--pretty=format:%H %ct', '--', file_path],
            encoding='utf-8',
            stderr=subprocess.STDOUT
        ).strip()
    except subprocess.CalledProcessError as e:
        if "unknown revision or path not in the working tree" in e.output:
            print(f"エラー: リポジトリにファイル '{file_path}' の履歴が見つかりません。")
            return None
        raise e
    
    if not log_output:
        print(f"警告: ファイル '{file_path}' の履歴が見つかりませんでした。")
        return []

    commits = [line.split() for line in log_output.split('\n') if line]
    
    # 2. 各コミット時のファイルの行数を計測
    for commit_hash, timestamp in commits:
        
        # 3. `git checkout`でコミット時点のファイルを作業ディレクトリに復元
        # --forceを使うことで、作業ディレクトリの状態に関わらずファイルを復元
        subprocess.check_call(
            ['git', 'checkout', commit_hash, '--', file_path],
            stdout=subprocess.DEVNULL, # 標準出力を非表示
            stderr=subprocess.DEVNULL  # エラー出力を非表示
        )
        
        # 4. 行数を計測
        line_count = get_file_line_count(file_path)
        
        history.append({
            'date': int(timestamp),
            'lines': line_count,
            'hash': commit_hash
        })
    
    # 5. Git作業ツリーを元のブランチに戻す
    if current_branch:
        subprocess.call(
            ['git', 'checkout', current_branch, '--force'],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        print(f"Git作業ツリーを元のブランチ（{current_branch}）に戻しました。")
    else:
        # ブランチが特定できない場合は、HEADの最新状態に戻す
        subprocess.call(
            ['git', 'checkout', 'HEAD', '--force'],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        print("Git作業ツリーをHEADの最新状態に戻しました。")

    # 日付順にソート（git logは通常新しい順なので、反転させるか、タイムスタンプでソート）
    history.sort(key=lambda x: x['date'])
    print(f"収集完了: {len(history)}個のデータポイント。")
    return history

def save_data(data):
    """
    収集した履歴データをJSONファイルに保存する。
    """
    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"データが {DATA_FILE} に保存されました。")

def main():
    history_data = collect_line_count_history(TARGET_FILE)
    
    if history_data is not None:
        save_data(history_data)

if __name__ == "__main__":
    main()