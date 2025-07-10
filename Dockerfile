FROM python:3.11.9-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "app.main_portal_app:app"] 