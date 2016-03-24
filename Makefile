HUMILIS := .env/bin/humilis
PIP := .env/bin/pip
PYTHON := .env/bin/python
TOX := .env/bin/tox
STAGE := DEV
HUMILIS_ENV := tests/integration/humilis-kinesis-mapper

# create virtual environment
.env:
	virtualenv .env -p python3

# install dev dependencies, create layers directory
develop: .env
	$(PIP) install -r requirements-dev.txt

# run unit tests
test: .env
	$(PIP) install tox
	$(TOX) -e unit

# run integration tests (require deployment)
testi: .env
	$(PIP) install tox
	$(TOX) -e integration

# remove .tox and .env dirs
clean:
	rm -rf .env .tox

# deploy the test environment
create: develop
	$(HUMILIS) create --stage $(STAGE) $(HUMILIS_ENV).yaml.j2
	$(PYTHON) scripts/deploy-secrets.py $(HUMILIS_ENV).yaml.j2 $(STAGE)

# update the test deployment
update: develop
	$(HUMILIS) update --stage $(STAGE) $(HUMILIS_ENV).yaml.j2
	$(PYTHON) scripts/deploy-secrets.py $(HUMILIS_ENV).yaml.j2 $(STAGE)

# delete the test deployment
delete: develop
	$(HUMILIS) delete --stage $(STAGE) $(HUMILIS_ENV).yaml.j2

# upload to Pypi
pypi: develop
	$(PYTHON) setup.py sdist upload
