FROM sp2027-fixed-historical-replay:20261111-observer2
USER root
COPY diagnose_saved_case.py saved-case.json /opt/diagnosis/
RUN chmod -R a-w /opt/diagnosis
USER 10001:10001
ENTRYPOINT ["python", "-I", "-B", "/opt/diagnosis/diagnose_saved_case.py"]
CMD []
