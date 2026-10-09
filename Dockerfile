FROM python:3.12

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip
RUN apt-get update \
    && apt-get -y install libpq-dev gcc


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x  /app/entrypoint.prod.sh

CMD ["/app/entrypoint.prod.sh"]