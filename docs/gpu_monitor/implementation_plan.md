GPUメモリの使用状況をリアルタイムで監視し、プロセスごとに使用量を表示するモダンなデスクトップアプリケーションを開発します。
※終了機能は環境によって不安定なため、監視機能に特化した軽量ツールとして構築します。

## Proposed Changes

### [GPU Monitor App]

`nvidia-smi` がプロセスごとのメモリ使用量を `N/A`（利用不可）と報告する場合があるため、Windows標準の「GPU Process Memory」パフォーマンスカウンターを詳細に解析して正確な使用量（MiB単位）を取得する方式に切り替えます。

#### [MODIFY] [gpu_monitor_app.py](file:///e:/Obsidian/2025/作成したプログラム/GpuFree/apps/gpu_monitor/gpu_monitor_app.py)
- `get_gpu_processes` 関数を刷新。
- PowerShell経由で `\GPU Process Memory(*)\Local Usage` を取得・集計。
- 各PIDごとに使用量を加算し、プロセス名と実行パスを `psutil` で補完。
- 更新間隔を最適化し、リアルタイム性を維持。

#### [NEW] [tests/verify_gpu_data.py](file:///e:/Obsidian/2025/作成したプログラム/GpuFree/tests/verify_gpu_data.py)
- GPUプロセス情報の取得とプロセス終了機能の技術検証スクリプト。

#### [NEW] [tests/gpu_monitor_app.py](file:///e:/Obsidian/2025/作成したプログラム/GpuFree/tests/gpu_monitor_app.py)
- メインアプリケーションの実装（開発用）。

## 検証プラン

### 自動テスト / 技術検証
- `tests/verify_gpu_data.py` を実行し、以下の点を確認します。
    - `nvidia-smi` からプロセスIDと使用メモリ量が正しく取得できること。
    - `psutil` を用いてプロセス名が取得できること。

### 手動検証
- アプリケーションを起動し、以下の操作を確認します。
    - GPUを使用しているアプリがリストに表示されること。
    - リストが定期的に更新されること。
    - 「終了」ボタンを押した際に、対象のプロセスが終了し、GPUメモリが解放されること。
    - デザインがモダンで美しく構成されていること。

> [!IMPORTANT]
> `apps` フォルダへの最終配置は、全ての動作確認が完了した後に行います。それまでは `tests` フォルダ内で開発を進めます。
