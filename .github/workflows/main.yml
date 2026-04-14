name: Rakesh's Daily Brief

on:
  schedule:
    # 8am EST = 1pm UTC (13:00)
    - cron: '0 13 * * 1-5'   # Monday–Friday
  workflow_dispatch:           # lets you run it manually too

jobs:
  send-brief:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Send Daily Brief
        env:
          EMAIL_TO: ${{ secrets.EMAIL_TO }}
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
        run: python3 daily_brief_email.py
