FROM apache/airflow:3.3.1

# Reinstalling the image's Airflow version alongside keeps pip from up- or downgrading it
RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    lexicalrichness==0.5.1 \
    nltk==3.10.3 \
    typesafe-sdk==0.7.4
