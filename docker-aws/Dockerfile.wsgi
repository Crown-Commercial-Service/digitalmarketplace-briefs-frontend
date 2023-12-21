# Base builds are defined in https://github.com/Crown-Commercial-Service/ccs-digitalmarketplace-aws-docker-base
FROM 473251818902.dkr.ecr.eu-west-2.amazonaws.com/dmp-base-http-buildstatic:latest as buildstatic
COPY --chown=uwsgi:uwsgi . ${APP_DIR}
RUN ./scripts/build.sh

FROM 473251818902.dkr.ecr.eu-west-2.amazonaws.com/dmp-base-wsgi:latest
COPY --from=buildstatic ${APP_DIR}/node_modules/digitalmarketplace-govuk-frontend ${APP_DIR}/node_modules/digitalmarketplace-govuk-frontend
COPY --from=buildstatic ${APP_DIR}/node_modules/govuk-frontend ${APP_DIR}/node_modules/govuk-frontend
COPY --from=buildstatic ${APP_DIR}/app/content ${APP_DIR}/app/content
COPY --from=buildstatic ${APP_DIR}/app/static ${APP_DIR}/app/static
