FROM python:3.7

COPY onliapa /app/
COPY server.py /app/
COPY requirements.txt /

RUN pip install -r /requirements.txt

WORKDIR /app
