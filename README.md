# Nginx log analyzer
На данный момент поддерживаемый формат файла настроек - только JSON

## Конфигурирумые параметры:

"**REPORT_SIZE**": Количество url с наибольшим суммарным временем обработки, которые будут сохранены в отчете

"**REPORT_DIR**": Каталог в который будет сохраняться итоговый отчет

"**LOG_DIR**": Каталог в котором будет выполняться поиск логов nginx

"**TS_F_PATH**": Файл в который будет сохранено время завершения работы (аналогично stat -c %Y log_analyzer.ts)

"**LOGFILE_PATH**": Файл для записи лога выполнения (если не указан - только на stdout)

"**LOGFILE_FORMAT**": Формат записи лога выполнения

"**LOGFILE_DATE_FORMAT**": Формат даты для записи в логе выполнения

"**MAX_MISMATCH_PERC**": % при котором структура обрабатываемого файла считается корректной

## Пример заполненого конфига:
`{
"REPORT_SIZE": 1000,
"REPORT_DIR": "reports",
"LOG_DIR": "log",
"TS_F_PATH": "log_analyzer.ts",
"LOGFILE_PATH": "log_analyzer.log",
"LOGFILE_FORMAT": "[%(asctime)s] %(levelname).1s %(message)s",
"LOGFILE_DATE_FORMAT": "%Y.%m.%d %H:%M:%S",
"MAX_MISMATCH_PERC": 10
}`

## Ожидаемый формат лога nginx:
`log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" 'log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" 'log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
'$status $body_bytes_sent "$http_referer" '
'"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
'$request_time';`

## Что ожидается от окружения:
Шаблон для построения отчета находится в файле reports/report.html

## Версии Python:
Протестировано на версии 3.6.4

## Примеры запуска:
`python3 log_analyzer.py`
`python3 log_analyzer.py --config=/home/user/otus/hw1/config.json`

## Тесты:
`python3 -m unittest discover -v tests/`