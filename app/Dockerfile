#FROM python:3.7
FROM python:3.7-alpine

EXPOSE 5000

WORKDIR app

COPY ./ /app/

# If building from alpine image
RUN apk update

# apk has named gunicorn as py-gunicorn
# TODO check if all are really necessary and if we prebuild this
RUN apk add bash gcc linux-headers make musl-dev python3-dev py-setuptools

# when running non-alpine images
#RUN apt-get update
# apk has named gunicorn as py-gunicorn
#RUN apt-get install -y python3-dev

RUN pip3 install -r requirements.txt

ENTRYPOINT ["gunicorn", "-b", ":5000", "application"]
#ENTRYPOINT ["gunicorn", "-b", ":5000", "application", "--access-logfile=logs/gunicorn.log", "--error-logfile=logs/error.log"]
# for debug
#ENTRYPOINT ["/bin/bash"]
# only local
#CMD ["python", "application.py"]
