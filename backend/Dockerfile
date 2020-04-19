FROM python:3.7


COPY requirements.txt /
RUN pip install -r /requirements.txt

WORKDIR /app
COPY server.py /app/
COPY onliapa /app/onliapa

