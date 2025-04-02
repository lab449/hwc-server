# hwc-server
<p align="center">
  <img src="https://user-images.githubusercontent.com/26273766/190159953-ad5e1969-7da5-43bf-8437-16cec4d9d7c9.svg" width="400"/>
</p>

The Homework Checker Server is the back end of an automatic homework checker application with various types of output.

## Setup hwc-server
Before building and starting homework checking server please configure external ports in .env file.

1. For single server on a single host machine you can use docker-compose up without any parameters in background mode.
```bash
    docker-compose up -d 
```
2. For multiple servers on a single host machine use `-p <PROJECT_NAME>` for configuring namespace and another `.env` file:
```bash 
    docker-compose --env-file <ENV_FILENAME> -p <PROJECT_NAME> up -d
```

3. Install nginx with `nginx.conf`
4. Copy images in: `/var/www/<URL>/images/`

## Dumping database from server
```bash
    docker-compose exec -T mongodb sh -c 'mongodump --db hwc-db --out <DIRECTORY_IN_CONTAINER>'
    docker cp <PROJECT_NAME>_mongodb_1:<DIRECTORY_IN_CONTAINER> <PATH_IN_HOST>
```
