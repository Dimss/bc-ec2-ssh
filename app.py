import boto3
import logging
import sys
import os
import click
import time

WAIT_FOR_EC2_READY = 500
KEY_NAME = 'candidate_test'
DUMP_KEY_LOCATION = "/tmp/aws_key"
SSM_PARAMETER_KEY_PATH = "/keypairs/candidate_test"
EC2_INSTANCE = {
    'InstanceType': 't2.micro',
    'ImageId': 'ami-0089b31e09ac3fffc',
    'MinCount': 1,
    'MaxCount': 1,
    'KeyName': KEY_NAME
}


class EC2Client(object):
    def __init__(self, access_key, secret_key):
        self._ec2_client = None
        self._ssm_client = None
        self.access_key = access_key
        self.secret_key = secret_key

        self._init_aws_ec2_client()
        self._init_aws_ssm_client()

    def _init_aws_ec2_client(self):
        self._ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="eu-west-2"
        )

    def _init_aws_ssm_client(self):
        self._ssm_client = boto3.client(
            'ssm',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="eu-west-2"
        )

    def create_ec2_instance(self):
        """
        Create EC2 instance and execute ssh login
        :return: none
        """
        res = self._ec2_client.run_instances(**EC2_INSTANCE)
        try:
            logging.info("Trying create an instance")
            instance_id = res['Instances'][0]['InstanceId']
            logging.info(f"EC2 instance successfully created, Instance ID: {instance_id}")
            # Wait for EC2 instance is ready, e.g state: running and checks status are OK
            instance_public_ip = self.watch_for_instance_running_state(instance_id)
            # Connect to SSH instance
            self.connect_to_ec2_instance(instance_public_ip)
        except Exception as ex:
            logging.error("Can't read response body from run_instance api call")
            raise ex

    def watch_for_instance_running_state(self, instance_id):

        for i in range(0, WAIT_FOR_EC2_READY):
            try:
                time.sleep(1)
                logging.info(f"Waiting instance {instance_id} to be ready")
                # Get instance statuses
                ec_instance_status = self._ec2_client.describe_instance_status(InstanceIds=[instance_id])
                if len(ec_instance_status['InstanceStatuses']) == 0:
                    continue
                # Get state
                instance_state = ec_instance_status['InstanceStatuses'][0]['InstanceState']['Name']
                # Get status check
                instance_status = ec_instance_status['InstanceStatuses'][0]['InstanceStatus']['Status']
                logging.info(f"Instance {instance_id} state: {instance_state},  status check: {instance_status}")
                # Is instance is ready, get instance IP and proceed with key dump and SSH connection
                if instance_state == 'running' and instance_status == 'ok':
                    instance = self._ec2_client.describe_instances(InstanceIds=[instance_id])
                    instance_public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
                    logging.info(f"Instance {instance_id} is in running state, continue to SSH key dump")
                    logging.info(f"Instance {instance_id} public IP is: {instance_public_ip}")
                    return instance_public_ip

            except Exception as ex:
                logging.error(f"Error during watch instance: {instance_id} state")
                raise ex
        logging.error(f"The instance {instance_id}, did not reached running state")
        exit(1)

    def dump_key(self):
        try:
            # Get the key from store
            key = self._ssm_client.get_parameter(Name=SSM_PARAMETER_KEY_PATH)
            logging.info(key['Parameter']['Value'])
            with open(DUMP_KEY_LOCATION, "w") as f:
                # Write the key to disk
                f.write(key['Parameter']['Value'])
            f.close()
            # Set correct key permissions
            os.chmod(DUMP_KEY_LOCATION, 0o400)
            logging.info(f"Key was saved into {DUMP_KEY_LOCATION}")
        except Exception as ex:
            logging.error("Error during fetching or saving ssh private key")
            raise ex

    def connect_to_ec2_instance(self, instance_public_ip):
        # If key not exists, create it
        if os.path.exists(DUMP_KEY_LOCATION) is False:
            self.dump_key()
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i /tmp/aws_key ec2-user@{instance_public_ip}"
        logging.info(f"gonna execute: {ssh_cmd}")
        # Exec ssh
        os.system(ssh_cmd)


@click.group()
def cli():
    pass


@click.command()
@click.option('--access-key', default=None, help='AWS Access Key')
@click.option('--secret-key', default=None, help='AWS Secret Key')
def deploy_ec2_instance(access_key, secret_key):
    # If option not set by user, try read env var
    if access_key is None:
        access_key = os.environ['ACCESS_KEY']
    # If option not set by user, try read env var
    if secret_key is None:
        secret_key = os.environ['SECRET_KEY']
    logging.info(access_key)
    logging.info(secret_key)
    ec2_client = EC2Client(access_key, secret_key)
    # Create instance and exec ssh
    ec2_client.create_ec2_instance()


cli.add_command(deploy_ec2_instance)


def main():
    log_format = '[%(asctime)s %(levelname)s] %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        stream=sys.stdout
    )
    cli()


if __name__ == "__main__":
    main()
