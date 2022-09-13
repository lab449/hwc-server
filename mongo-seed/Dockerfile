FROM mongo:latest
LABEL maintainer="texnoman@itmo.ru"

COPY . .

CMD mongorestore --host mongodb --db hwc-db db/hwc-db
