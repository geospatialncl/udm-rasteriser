FROM python:3.8
RUN apt-get -y update
RUN apt-get -y install libgdal-dev
COPY requirements.txt /

RUN pip install -r requirements.txt
RUN git clone dafni https://github.com/geospatialncl/udm-rasteriser

COPY run.py /
RUN mkdir /data_

ENTRYPOINT python run.py
