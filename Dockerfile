FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY doge-scrape.py doge-scrape.py

CMD ["python", "doge-scrape.py"]