# Blank Pygame Starter

این پروژه یک اسکلت تمیز و استاندارد برای شروع توسعه بازی با `pygame` است.

## پیش‌نیاز

- Python 3.11 یا بالاتر (در این سیستم: 3.13)

## راه‌اندازی (Windows PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## اجرا

```powershell
game
```

یا:

```powershell
python -m game.main
```

## تست و کیفیت کد

```powershell
pytest
ruff check .
```

## ساختار پروژه

```text
.
├── pyproject.toml
├── README.md
├── src/
│   └── game/
│       ├── __init__.py
│       ├── main.py
│       └── settings.py
└── tests/
    └── test_smoke.py
```

