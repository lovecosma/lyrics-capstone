FROM apache/airflow:3.3.1

# pandas, numpy and pyarrow match dashboard/requirements.txt: the dashboard reads the snapshot this image writes
RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    dynaconf==3.3.5 \
    lexicalrichness==0.5.1 \
    nltk==3.10.3 \
    numpy==2.5.4 \
    pandas==3.0.6 \
    pyarrow==26.0.1 \
    typesafe-sdk==0.7.4
