# CDK Lambda Layer Factory

Steps:

```
cdk init app --language python
rm -rf .venv
virtualenv --python=python3.9 ./.venv
source .venv/bin/activate
pip install -r requirements.txt
cdk synth
cdk deploy
```
