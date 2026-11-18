FROM maven:3.9.11-eclipse-temurin-8

RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
COPY upstream.tar.gz /opt/upstream.tar.gz
COPY FROZEN_MANIFEST.json collision.java HashProbe.java run_frozen.py /opt/input/
RUN mkdir /opt/upstream && tar -xzf /opt/upstream.tar.gz -C /opt/upstream

# Provision Maven's original dependency closure with network access, without running tests.
RUN mkdir /opt/provision && cp -a /opt/upstream/. /opt/provision/ && cd /opt/provision && mvn -B -ntp -Dcheckstyle.skip -Drat.skip=true -DskipTests -Pekstazi-study test && mvn -B -ntp dependency:get -Dartifact=org.apache.maven.surefire:surefire-junit4:3.2.5 -Dtransitive=true && rm -rf /opt/provision
RUN groupadd -g 10001 lab && useradd -u 10001 -g 10001 -m lab && cp -a /root/.m2 /home/lab/.m2 && chown -R lab:lab /home/lab

USER 10001:10001
WORKDIR /work
ENTRYPOINT ["/bin/sh", "-c", "python3 /opt/input/run_frozen.py; code=$?; printf '%s\n' \"$code\" > /work/out/runner-exit; touch /work/out/READY; sleep 180; exit \"$code\""]
