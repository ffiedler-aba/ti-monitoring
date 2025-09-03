cloc --md .. \
  --exclude-dir=.git,.venv,data,portable-build,windows-setup-src,build,dist,__pycache__ \
  --exclude-ext=hdf5,zip,log \
  --out=../CLOC_REPORT.md