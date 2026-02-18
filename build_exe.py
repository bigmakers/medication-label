#!/usr/bin/env python3
"""
medication_label.py を exe / app にビルドするスクリプト
使い方: python build_exe.py
"""
import PyInstaller.__main__
import sys
import os

def build():
    script = os.path.join(os.path.dirname(__file__), "medication_label.py")
    args = [
        script,
        "--windowed",
        "--name=MedicationLabel",
        "--clean",
        "--noconfirm",
    ]

    if sys.platform == "darwin":
        # macOS: onedir + .app バンドル
        args.append("--osx-bundle-identifier=com.medication.label")
    else:
        # Windows/Linux: onefile
        args.append("--onefile")

    PyInstaller.__main__.run(args)
    print("\nビルド完了！ dist/ フォルダを確認してください。")

if __name__ == "__main__":
    build()
