# This is a dummy service that will stay
# active while consuming minimal resources.
FROM alpine:latest
COPY ./migrate.sh /usr/bin/migrate
RUN chmod +x /usr/bin/migrate
CMD ["tail", "-f", "/dev/null"]
