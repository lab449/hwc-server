# Локальный запуск

Нужен работающий Docker Desktop. Каталог `server_task_data/` должен содержать задания и `tasks_info.json`; в Git он не хранится.

```sh
docker compose -f compose.local.yaml up -d --build
```

Страница: http://localhost:8080/ . API проверки доступности: http://localhost:8080/api/ok . MongoDB доступна только локально на порту 27018; данные хранятся в отдельном томе `hwc-local_mongodb-local`. Исходный дамп `mongo-seed/` автоматически не загружается.

Проверка и остановка:

```sh
docker compose -f compose.local.yaml ps
docker compose -f compose.local.yaml logs --tail=50 hwc
docker compose -f compose.local.yaml stop
```

После изменения Python-кода пересоберите приложение командой запуска. Изменения в `server_task_data/` видны через подключённый каталог. Для пересчёта конфигурации заданий перезапустите `hwc`:

```sh
docker compose -f compose.local.yaml restart hwc
```
