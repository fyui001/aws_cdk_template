FROM python:3.8.5-alpine

WORKDIR /code

ADD . .

RUN apk add --update-cache --no-cache npm

RUN npm install -g aws-cdk && \
    pip install pipenv && \
    pipenv install

CMD ["/bin/ash"]