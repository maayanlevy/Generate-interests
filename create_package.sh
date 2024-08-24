#!/bin/bash

# Variables
PACKAGE_NAME="lambda_function_package.zip"
PYTHON_VERSION="python3.9"  # Change this to the Python version used by your Lambda function
REQUIREMENTS_FILE="requirements.txt"

# Clean up previous builds
echo "Cleaning up old build..."
rm -rf package
rm -f $PACKAGE_NAME

# Install dependencies
echo "Installing dependencies..."
mkdir package
pip install --target ./package -r $REQUIREMENTS_FILE

# Create the zip package
echo "Creating zip package..."
cd package
zip -r9 ../$PACKAGE_NAME .
cd ..

# Add the Lambda function code to the zip file
echo "Adding Lambda function code to zip package..."
zip -g $PACKAGE_NAME *.py

# Clean up
echo "Cleaning up temporary files..."
rm -rf package

echo "Package creation complete: $PACKAGE_NAME"
