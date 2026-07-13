FROM php:8.1-apache

RUN apt-get update && apt-get install -y libsqlite3-dev && docker-php-ext-install pdo pdo_sqlite && a2enmod rewrite && apt-get clean

COPY index.php /var/www/html/
COPY dashboard.php /var/www/html/
COPY flag.txt /var/www/html/

RUN chmod 644 /var/www/html/flag.txt
