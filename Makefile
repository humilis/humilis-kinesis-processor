HUMILIS := .env/bin/humilis
PIP := .env/bin/pip
PYTHON := .env/bin/python
TOX := .env/bin/tox
STAGE := DEV
HUMILIS_ENV := tests/integration/humilis-kinesis-processor

# create virtual environment
.env:
	virtualenv .env -p python3

# install AWS Lambda like virtualenv
.lambda:
	virtualenv .lambda -p python2.7
	.lambda/bin/pip install -r requirements-lambda.txt

# install dev dependencies, create layers directory
develop: .env .lambda
	$(PIP) install -r requirements-test.txt -r requirements-dev.txt

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
	rm -rf .env .tox .lambda tests/*.pyc tests/__pycache__ \
		humilis_kinesis_processor/*.pyc humilis_kinesis_processor/__pycache__

# deploy secrets to the environment secrets vault
secrets:
	$(PYTHON) scripts/deploy-secrets.py $(HUMILIS_ENV).yaml.j2 $(STAGE)

# create CF stacks
create-cf: develop
	$(HUMILIS) create \
	  --stage $(STAGE) \
	  --output $(HUMILIS_ENV)-$(STAGE).outputs.yaml $(HUMILIS_ENV).yaml.j2

# deploy the test environment
create: create-cf secrets

# update CF stacks
update-cf: develop
	$(HUMILIS) update \
	  --stage $(STAGE) \
	  --output $(HUMILIS_ENV)-$(STAGE).outputs.yaml $(HUMILIS_ENV).yaml.j2

# update the test deployment
update: update-cf secrets

# delete the test deployment
delete: develop
	./scripts/empty-bucket.py $(HUMILIS_ENV)-$(STAGE).outputs.yaml
	$(HUMILIS) delete --stage $(STAGE) $(HUMILIS_ENV).yaml.j2

# upload to Pypi
pypi: develop
	$(PYTHON) setup.py sdist upload
