FROM mongo:4.4.6
LABEL maintainer="texnoman@itmo.ru"

COPY . .

CMD mongorestore --host mongodb --db hwc-db db/hwc-db
