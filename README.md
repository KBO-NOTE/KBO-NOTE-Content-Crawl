README는 추후 다시 정리할 예정입니다.(임시)

리눅스 환경에서 아래 명령어 실행해야 chrome driver 정상 작동함.
필자는 Ubuntu 24.04.1LTS 환경임.

세팅법
===
```bash
sudo apt-get update
sudo apt-get install -y \
  libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libasound2t64 libpango-1.0-0 libpangocairo-1.0-0 \
  libgtk-3-0 fonts-liberation xdg-utils chromium-browser
```

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

env 파일
===
```env
#Postgres
PG_HOST=
PG_PORT=
PG_USER=
PG_PASSWORD=
PG_DBNAME=
```

cronjob
====
crontab -e
> 59 3-23/4 * * * /home/user/kbonote/venv/bin/python /home/user/kbonote/main.py >> /home/user/kbonote/cron.log 2>&1