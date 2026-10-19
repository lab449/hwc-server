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

## Проверки API

После пересборки приложения:

```sh
docker compose -f compose.local.yaml exec -T hwc python3 -m unittest discover -s tests -p 'test_*.py' -v
docker compose -f compose.local.yaml exec -T hwc python3 - < tests/api_e2e.py
```

E2E запускает отдельный HTTP-процесс с базой `hwc_e2e_<случайный идентификатор>` и удаляет только эту базу после завершения. Рабочая база локального приложения не используется. Для проверки всех шести работ они должны быть включены в локальном `tasks_info.json`. Проверяются выдача и оценка нулевого варианта, регистрация и вход, ошибочные запросы, конкурентная выдача варианта и лимит попыток.

ID студента — положительное целое число в пределах BSON int64 (до 9223372036854775807); ограничения по году поступления нет. Новые пароли сохраняются как хеши, вход в существующие учётные записи поддерживается без изменения их записей.
