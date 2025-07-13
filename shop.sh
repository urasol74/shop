#!/usr/bin/env bash
cd /home/ubuntu/shop
source venv/bin/activate
exec gunicorn -w 4 -b 0.0.0.0:5000 app:app