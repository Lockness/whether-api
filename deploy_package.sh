#!/bin/bash

lambda_function=whether_api

# Remove old deployment package data
rm -r ./deploy
mkdir ./deploy ./deploy/tmp

cd deploy/
path=$(pwd)
cd ../

# Copy all custom .py files to directory
cp -r ./router.py src ./deploy/tmp/

# Install all library requirements
pip install -r ./requirements.txt -t ./deploy/tmp/

# Create deployment package
cd ./deploy/tmp
zip -r -9 ../${lambda_function}-deployment.zip *

# Deploy package to lambda function
aws lambda update-function-code \
--function-name arn:aws:lambda:us-east-1:237093315022:function:${lambda_function} \
--region us-east-1 \
--zip-file fileb://${path}/${lambda_function}-deployment.zip

cd ../../
