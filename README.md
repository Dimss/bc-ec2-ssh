# BV EC2 

Python3 script for creating EC2 instance and SSH into it.

## Prerequisite 
1. Make sure you've python3 installed 
2. Install [pipenv](https://pipenv.kennethreitz.org/en/latest/#install-pipenv-today)
3. cd into code directory and run `pipenv install` to install all Python3 dependencies

## Run the script
To run the script you've to provide your AWS access key and secret key. 
1. Use env vars to export your AWS creds
  ```bash
  export ACCESS_KEY=YOUR-ACCESS-KEY 
  export SECRET_KEY=YOUR-SECRET-KEY
  ```
2. Run the script 
```bash
pipenv run app deploy-ec2-instance
```
