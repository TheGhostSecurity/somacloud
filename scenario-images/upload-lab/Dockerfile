FROM php:8.1-apache

RUN a2enmod rewrite
RUN mkdir -p /var/www/html/uploads && chmod 777 /var/www/html/uploads

COPY login.php /var/www/html/
COPY index.php /var/www/html/
COPY flag.txt /var/www/html/

RUN chmod 644 /var/www/html/flag.txt
