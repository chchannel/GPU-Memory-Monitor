# GPU-Memory-Monitor

A lightweight, modern GPU memory monitoring tool for Windows.  
Windows向けの軽量でモダンなGPUメモリ監視ツールです。

![Main UI](docs/gpu_monitor/screenshot_main.png) 

## Features (主な機能)

- **Accurate Monitoring**: Tracks GPU memory usage per process using Windows Performance Counters.
  - パフォーマンスカウンターを使用し、ブラウザや描画アプリのメモリ使用量も正確に追跡します。
- **Modern UI**: Clean design built with PySide6.
  - PySide6による、モダンで洗練されたグレーベースのデザイン。
- **Interactive Windows**: Resizable, Always-on-Top, and Compact modes.
  - 自由なリサイズ、最前面表示（ピン留め）、コンパクトモードに対応。
- **Stealth Execution**: No console windows pop up during background updates.
  - バックグラウンドでのデータ取得時にコンソールが表示されず、作業を妨げません。
- **Standalone EXE**: Ready to use without Python installation.
  - Python環境不要で、単体で動作するEXE形式。

## Usage (使い方)

1. Download `GPUMonitor.exe` from the `apps/gpu_monitor` folder (or Releases).
2. Run the executable.
3. Use the control buttons:
   - 📌: Toggle Always-on-Top (最前面表示)
   - 🔳: Toggle Compact Mode (コンパクトモード)
   - 🎨: Cyclical Theme Switching (Light -> Gray -> Dark) (テーマ切り替え)
   - Sort buttons (使用量 / 名前): Sort the process list.

## Tech Stack (技術スタック)

- **Language**: Python 3.x
- **GUI Framework**: PySide6
- **Monitoring**: Windows Performance Counters (PowerShell), `nvidia-smi`, `psutil`
- **Packaging**: PyInstaller

## License (ライセンス)

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
MITライセンスの下で公開されています。
